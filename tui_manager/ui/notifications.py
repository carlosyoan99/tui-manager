"""
Notificaciones nativas y animaciones conscientes de ``prefers-reduced-motion`` (B3-3).

Módulo standalone: no depende de textual ni de otros módulos del proyecto, para
que el Arquitecto pueda integrarlo después desde ``screens.py`` sin acoplar la
capa UI a detalles de ``subprocess``. Al importarlo no se ejecuta ningún
comando, no se instala nada y no se hace ninguna llamada de red.

API pública
-----------
``notify(title, message, app=None, *, runner=None, which=None) -> str``
    Intenta ``notify-send`` (Freedesktop / GNOME / KDE / sway, etc.). Devuelve
    ``'native'`` si la herramienta existe y la llamada no lanza excepción;
    ``'unavailable'`` en caso contrario. Nunca lanza excepción, nunca instala
    paquetes. ``app`` se acepta y se ignora: está reservado para la integración
    futura y mantener la firma estable (no hace falta cambiar llamadas después).

``reduced_motion_enabled(environ=None) -> bool``
    Consulta ``PREFERS_REDUCED_MOTION`` (valores truthy), ``NO_COLOR`` (simple
    presencia) y ``TERM=dumb``. Con ``environ=None`` lee ``os.environ``.

``progress_animation(label='', *, style='spinner', environ=None)``
    Devuelve un :class:`AnimationDescriptor` inmutable con los frames, el
    intervalo en segundos y el flag ``reduced_motion``. Sin dependencias nuevas.

Uso típico (integración futura; NO se hace en este módulo)::

    from tui_manager.ui.notifications import notify, progress_animation

    resultado = notify('Instalación lista', 'curl se instaló correctamente')
    # 'native' | 'unavailable' -> si es 'unavailable', loguear internamente

    anim = progress_animation('Instalando paquetes')
    if anim.animated:
        # textual: self.set_timer(anim.interval, ...) y rotar anim.frames
        frame = anim.frames[tick % len(anim.frames)]
    else:
        frame = anim.frames[0]  # único frame estático: cero movimiento
    texto = f'{frame} {anim.label}'

Inyección para tests: ``runner`` y ``which`` en :func:`notify`; ``environ`` en
:func:`progress_animation` y :func:`reduced_motion_enabled`. Así los tests
pueden verificar el comportamiento sin ejecutar ``notify-send`` real.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Mapping

__all__ = [
    'AnimationDescriptor',
    'notify',
    'progress_animation',
    'reduced_motion_enabled',
]

_NATIVE = 'native'
_UNAVAILABLE = 'unavailable'

#: Valores considerados "sí" para ``PREFERS_REDUCED_MOTION``.
_TRUTHY = frozenset({'1', 'true', 'yes', 'on'})

#: Frames por estilo cuando el movimiento está permitido.
_FRAMES: dict[str, tuple[str, ...]] = {
    'spinner': ('|', '/', '-', '\\'),
    'dots': ('.', '..', '...', '....'),
    'bar': ('[    ]', '[=   ]', '[==  ]', '[=== ]', '[====]'),
}

#: Un único frame estático por estilo cuando se pide reducir movimiento.
_STATIC_FRAMES: dict[str, tuple[str, ...]] = {
    'spinner': ('■',),
    'dots': ('…',),
    'bar': ('[====]',),
}

#: Segundos entre frames (solo se usa si ``animated`` es True).
_INTERVALS: dict[str, float] = {
    'spinner': 0.08,
    'dots': 0.25,
    'bar': 0.15,
}


@dataclass(frozen=True)
class AnimationDescriptor:
    """Descripción inmutable de una animación de progreso.

    Atributos:
        label: texto que describe la operación en curso.
        style: estilo solicitado (``spinner``, ``dots`` o ``bar``).
        frames: frames a rotar. Con movimiento reducido contiene uno solo.
        interval: segundos entre frames; ``0.0`` con movimiento reducido.
        reduced_motion: True si el entorno pidió reducir el movimiento.
    """

    label: str
    style: str
    frames: tuple[str, ...]
    interval: float
    reduced_motion: bool

    @property
    def animated(self) -> bool:
        """True cuando la UI puede animar; False si debe quedarse quieta."""
        return not self.reduced_motion


def _is_truthy(value: object) -> bool:
    return str(value).strip().lower() in _TRUTHY


def reduced_motion_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Devuelve True si el entorno pide reducir o suprimir el movimiento.

    Se respetan tres señales habituales (en orden): ``PREFERS_REDUCED_MOTION``
    con valor truthy, presencia de ``NO_COLOR`` y ``TERM=dumb``. Aceptar un
    ``environ`` inyectado permite testear sin tocar ``os.environ``.

    Args:
        environ: mapeo de variables de entorno. Por defecto, ``os.environ``.

    Returns:
        ``True`` cuando corresponde mostrar un frame estático.
    """
    env = os.environ if environ is None else environ
    if _is_truthy(env.get('PREFERS_REDUCED_MOTION', '')):
        return True
    if 'NO_COLOR' in env:  # no-color.org: basta con que esté definida
        return True
    if env.get('TERM', '').strip().lower() == 'dumb':
        return True
    return False


def progress_animation(
    label: str = '',
    *,
    style: str = 'spinner',
    environ: Mapping[str, str] | None = None,
) -> AnimationDescriptor:
    """Construye un descriptor de animación respetando ``prefers-reduced-motion``.

    Args:
        label: texto de la operación (no incluye el frame).
        style: ``spinner`` (por defecto), ``dots`` o ``bar``. Un valor
            desconocido degrada a ``spinner`` en lugar de lanzar.
        environ: mapeo opcional para simular variables de entorno en tests.

    Returns:
        Un :class:`AnimationDescriptor`. Con movimiento reducido, ``frames``
        tiene un solo elemento y ``interval`` es ``0.0``.
    """
    key = style if style in _FRAMES else 'spinner'
    reduced = reduced_motion_enabled(environ)
    frames = _STATIC_FRAMES[key] if reduced else _FRAMES[key]
    return AnimationDescriptor(
        label=label,
        style=key,
        frames=frames,
        interval=0.0 if reduced else _INTERVALS[key],
        reduced_motion=reduced,
    )


def notify(
    title: str,
    message: str,
    app: object = None,
    *,
    runner: Callable[..., object] | None = None,
    which: Callable[[str], str | None] | None = None,
) -> str:
    """Intenta enviar una notificación nativa con ``notify-send``.

    Si ``shutil.which('notify-send')`` encuentra la herramienta, se invoca
    ``subprocess.run(['notify-send', title, message], timeout=2, check=False)``
    y se devuelve ``'native'``. Si la herramienta no está o la llamada lanza
    cualquier excepción (p. ej. ``TimeoutExpired``, ``OSError``), se devuelve
    ``'unavailable'``. Nunca propaga excepciones ni instala nada.

    Nota: se pasa ``check=False`` a propósito, por lo que un código de salida
    distinto de cero no se considera una excepción; ``'native'`` significa
    "la herramienta estaba disponible y la llamada terminó sin lanzar".

    Args:
        title: título de la notificación.
        message: cuerpo de la notificación.
        app: reservado para integración futura (se ignora; firma estable).
        runner: reemplazo inyectable de ``subprocess.run`` (tests).
        which: reemplazo inyectable de ``shutil.which`` (tests).

    Returns:
        ``'native'`` o ``'unavailable'``.
    """
    del app  # parámetro reservado: no se usa todavía
    try:
        finder = shutil.which if which is None else which
        if not finder('notify-send'):
            return _UNAVAILABLE
        call = subprocess.run if runner is None else runner
        call(['notify-send', title, message], timeout=2, check=False)
        return _NATIVE
    except Exception:
        # Incluye TimeoutExpired/OSError y fallos de un runner inyectado:
        # la notificación es best-effort y jamás debe romper la UI.
        return _UNAVAILABLE
