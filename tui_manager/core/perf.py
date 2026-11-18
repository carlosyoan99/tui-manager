"""
Utilidades ligeras de rendimiento: medición, formato y caché de listados.

Sin dependencias nuevas (sólo biblioteca estándar).  Se usa tanto en los
benchmarks de ``tests/test_perf.py`` como en el código de producción para
evitar recalcular listados grandes de paquetes.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Hashable, Optional, Sequence, TypeVar

T = TypeVar('T')
K = TypeVar('K', bound=Hashable)


# ---------------- Medición ----------------

@dataclass(frozen=True)
class Measurement:
    """Resultado de medir una llamada con :func:`measure_call`."""

    name: str
    elapsed: float          # segundos (time.perf_counter)
    value: Any = None       # valor devuelto por la llamada
    calls: int = 1          # número de llamadas medidas

    @property
    def elapsed_ms(self) -> float:
        """Duración total en milisegundos."""
        return self.elapsed * 1000.0

    @property
    def average_ms(self) -> float:
        """Duración media por llamada en milisegundos."""
        return (self.elapsed / self.calls) * 1000.0 if self.calls else 0.0

    def format(self, precision: int = 3) -> str:
        """Representación legible del resultado."""
        detail = f" ({self.calls} llamada{'s' if self.calls != 1 else ''})" \
            if self.calls != 1 else ""
        return (f"{self.name}: {self.elapsed_ms:.{precision}f} ms"
                f" [media {self.average_ms:.{precision}f} ms]{detail}")

    def __str__(self) -> str:
        return self.format()


def format_result(name: str, elapsed: float, calls: int = 1,
                  precision: int = 3) -> str:
    """Formatea una medición ya realizada (segundos → milisegundos)."""
    return Measurement(name=name, elapsed=elapsed, calls=calls).format(precision)


def measure_call(fn: Callable[..., T], *args: Any,
                 name: Optional[str] = None, repeat: int = 1,
                 **kwargs: Any) -> Measurement:
    """
    Ejecuta ``fn(*args, **kwargs)`` y mide su duración con ``perf_counter``.

    Args:
        fn: Callable a medir.
        *args: Argumentos posicionales para ``fn``.
        name: Etiqueta del resultado (por defecto, ``fn.__name__``).
        repeat: Número de ejecuciones; ``elapsed`` es el total y
            ``average_ms`` el promedio por ejecución. Debe ser >= 1.
        **kwargs: Argumentos por palabra para ``fn``.

    Returns:
        :class:`Measurement` con el valor de la última ejecución.
    """
    if repeat < 1:
        raise ValueError("repeat debe ser >= 1")
    label = name or getattr(fn, '__name__', repr(fn))
    value: Any = None
    start = time.perf_counter()
    for _ in range(repeat):
        value = fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return Measurement(name=label, elapsed=elapsed, value=value, calls=repeat)


# ---------------- Paginación ----------------

def paginate(items: Sequence[T], offset: int = 0,
             limit: Optional[int] = None) -> Sequence[T]:
    """
    Devuelve una ventana de filas ``[offset:offset + limit]`` de ``items``.

    No muta la secuencia original. Índices negativos se tratan como 0 y un
    ``limit`` <= 0 devuelve una ventana vacía.
    """
    start = max(0, offset)
    if limit is None:
        return items[start:]
    if limit <= 0:
        return items[:0]
    return items[start:start + limit]


# ---------------- Caché de paquetes ----------------

class PackageCache:
    """
    Caché en memoria para listados de paquetes, con invalidación.

    ``get(key, factory)`` calcula el valor sólo en caso de fallo (miss) y
    lo reutiliza en aciertos (hit). ``invalidate()`` limpia una clave o
    toda la caché. Es segura para uso concurrente básico (lock).
    """

    def __init__(self) -> None:
        self._entries: Dict[Hashable, Any] = {}
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        """Número de entradas almacenadas."""
        with self._lock:
            return len(self._entries)

    def get(self, key: K, factory: Callable[[], T]) -> T:
        """Devuelve el valor cacheado o lo calcula con ``factory``."""
        with self._lock:
            if key in self._entries:
                self.hits += 1
                return self._entries[key]

        # Se calcula fuera del lock para no bloquear otras claves.
        value = factory()

        with self._lock:
            self._entries[key] = value
            self.misses += 1
        return value

    def set(self, key: K, value: T) -> None:
        """Almacena explícitamente un valor (sin contabilizar miss)."""
        with self._lock:
            self._entries[key] = value

    def invalidate(self, key: Optional[K] = None) -> None:
        """Invalida una clave, o todas si no se especifica ``key``."""
        with self._lock:
            if key is None:
                self._entries.clear()
            else:
                self._entries.pop(key, None)

    def clear(self) -> None:
        """Alias de ``invalidate()`` sin argumentos."""
        self.invalidate()

    def stats(self) -> dict:
        """Devuelve ``hits``, ``misses`` y ``size``."""
        with self._lock:
            return {'hits': self.hits, 'misses': self.misses,
                    'size': len(self._entries)}
