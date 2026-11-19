"""
Tema dinámico generado por matugen (OpenCode / Noctalia).

La TUI puede tomar los colores del mismo esquema que usa el escritorio:
``~/.config/opencode/themes/matugen.json``.  Este módulo solo *lee* y
*traduce* ese JSON; no aplica ningún cambio fuera de la TUI (el tema del
escritorio lo gestiona Noctalia).

API pública:

* :func:`load_matugen_theme` -- carga el JSON de matugen, nunca falla.
* :func:`to_textual_palette` -- convierte los ``defs`` en nombres de estilo
  de textual (``primary``, ``secondary``, ``surface``, ``background``,
  ``text``, ``error``, ``warning``, ``success``, ...).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Ruta real investigada en las notebooks (OpenCode + Noctalia).
MATUGEN_PATH = os.path.join(
    '~', '.config', 'opencode', 'themes', 'matugen.json'
)

# Colores de respaldo (texto oscuro sobre claro) si el JSON no trae defs.
_FALLBACK = {
    'primary': '#5f87af',
    'secondary': '#5f8787',
    'background': '#ffffff',
    'surface': '#f5f5f5',
    'text': '#101010',
    'error': '#af0000',
}


def _default_path() -> str:
    """Ruta por defecto, reevaluada para respetar cambios de ``HOME``."""
    return os.path.expanduser(MATUGEN_PATH)


def load_matugen_theme(path: Optional[str] = None) -> Optional[dict]:
    """Carga el JSON de matugen.

    Args:
        path: Ruta alternativa al JSON.  Por defecto
            ``~/.config/opencode/themes/matugen.json``.

    Returns:
        El diccionario parseado, o ``None`` si el archivo no existe, no se
        puede leer o no contiene un JSON válido.  Nunca lanza excepciones.
    """
    target = path or _default_path()
    try:
        with open(target, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError) as exc:
        # FileNotFoundError / JSONDecodeError / permisos / ruta inválida.
        logger.debug('No se pudo cargar tema matugen desde %s: %s', target, exc)
        return None

    if not isinstance(data, dict):
        logger.debug('El tema matugen de %s no es un objeto JSON', target)
        return None
    return data


def _hex_to_rgb(value) -> Optional[tuple]:
    """Convierte ``#rrggbb`` (o ``#rgb``) a tupla RGB; ``None`` si es inválido."""
    if not isinstance(value, str):
        return None
    text = value.strip().lstrip('#')
    if len(text) == 3:
        text = ''.join(char * 2 for char in text)
    if len(text) != 6:
        return None
    try:
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _is_dark(background) -> bool:
    """Determina si un color de fondo es oscuro por luminosidad percibida.

    Si el color no es parseable se asume oscuro (comportamiento por defecto).
    """
    rgb = _hex_to_rgb(background)
    if rgb is None:
        return True
    red, green, blue = rgb
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    return luminance < 128


def to_textual_palette(defs) -> dict:
    """Mapea los ``defs`` de matugen a variables de estilo de textual.

    Args:
        defs: Diccionario ``nombre -> hex`` tal como aparece en la clave
            ``defs`` del JSON de matugen.

    Returns:
        Diccionario con claves de estilo de textual.  Incluye además
        ``'dark'`` (bool) para saber si el esquema es claro u oscuro.

    Nota:
        ``warning`` y ``success`` se derivan de ``secondary`` cuando el
        esquema no los define explícitamente, tal como pide la especificación.
    """
    if not isinstance(defs, dict):
        defs = {}

    def pick(*keys, default=None):
        for key in keys:
            value = defs.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return default

    primary = pick('primary', 'accent', default=_FALLBACK['primary'])
    secondary = pick('secondary', default=primary)
    background = pick('background', 'surface', default=_FALLBACK['background'])
    surface = pick('surface', 'background', default=_FALLBACK['surface'])
    text = pick(
        'on_surface', 'on_background', 'text', 'foreground',
        default=_FALLBACK['text'],
    )
    error = pick('error', default=_FALLBACK['error'])
    warning = pick('warning', 'yellow', default=secondary)
    success = pick('success', 'green', default=secondary)

    return {
        'primary': primary,
        'secondary': secondary,
        'accent': pick('accent', default=primary),
        'background': background,
        'surface': surface,
        'panel': surface,
        'text': text,
        'foreground': text,
        'text-muted': pick('on_surface_variant', default=text),
        'error': error,
        'warning': warning,
        'success': success,
        'dark': _is_dark(background),
    }
