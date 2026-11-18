"""
Módulo de eventos personalizados
"""

import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    Emisor de eventos personalizados

    Permite escuchar y emitir eventos personalizados.
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event_name: str, callback: Callable) -> Callable:
        """
        Registra un callback para un evento específico

        Args:
            event_name: Nombre del evento
            callback: Función a llamar cuando ocurra el evento

        Returns:
            El callback registrado para que pueda ser removido
        """
        if event_name not in self._listeners:
            self._listeners[event_name] = []

        self._listeners[event_name].append(callback)
        logger.debug(f"Registrado listener para evento '{event_name}'")

        return callback

    def off(self, event_name: str, callback: Callable) -> bool:
        """
        Elimina un callback de un evento específico

        Args:
            event_name: Nombre del evento
            callback: Función a eliminar

        Returns:
            True si el callback fue eliminado, False si no estaba registrado
        """
        if event_name in self._listeners:
            if callback in self._listeners[event_name]:
                self._listeners[event_name].remove(callback)
                logger.debug(f"Eliminado listener para evento '{event_name}'")
                return True
        return False

    def emit(self, event_name: str, *args, **kwargs) -> List[Any]:
        """
        Emite un evento con argumentos

        Args:
            event_name: Nombre del evento
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave

        Returns:
            Lista de resultados de los callbacks
        """
        results = []

        if event_name in self._listeners:
            for callback in self._listeners[event_name]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error en callback para evento '{event_name}': {e}")

        logger.debug(f"Evento '{event_name}' emitido con {len(results)} listeners")
        return results

    def clear(self, event_name: str = None) -> int:
        """
        Elimina todos los listeners de un evento o todos los eventos

        Args:
            event_name: Nombre del evento. Si es None, elimina todos.

        Returns:
            Número de listeners eliminados
        """
        if event_name:
            count = len(self._listeners.get(event_name, []))
            self._listeners[event_name] = []
            logger.debug(f"Eliminados {count} listeners para evento '{event_name}'")
            return count
        else:
            count = sum(len(listeners) for listeners in self._listeners.values())
            self._listeners = {}
            logger.debug(f"Eliminados {count} listeners de todos los eventos")
            return count

    def listeners_count(self, event_name: str = None) -> int:
        """
        Obtiene el número de listeners para un evento o todos los eventos

        Args:
            event_name: Nombre del evento. Si es None, cuenta todos.

        Returns:
            Número de listeners
        """
        if event_name:
            return len(self._listeners.get(event_name, []))
        else:
            return sum(len(listeners) for listeners in self._listeners.values())

    def has_listeners(self, event_name: str) -> bool:
        """
        Verifica si hay listeners para un evento

        Args:
            event_name: Nombre del evento

        Returns:
            True si hay listeners, False en caso contrario
        """
        return event_name in self._listeners and len(self._listeners[event_name]) > 0

    def get_event_names(self) -> List[str]:
        """
        Obtiene la lista de nombres de eventos

        Returns:
            Lista de nombres de eventos
        """
        return list(self._listeners.keys())


# Eventos disponibles por defecto
EVENTS = {
    # Paquetes
    'package.installed': lambda package_name: None,
    'package.removed': lambda package_name: None,
    'package.updated': lambda package_name: None,
    'package.error': lambda package_name, error: None,

    # Procesos
    'process.killed': lambda pid: None,
    'process.reniced': lambda pid, old_nice, new_nice: None,
    'process.error': lambda pid, error: None,

    # Sistema
    'system.updated': lambda: None,
    'system.error': lambda error: None,

    # Interfaz
    'theme.changed': lambda theme_name: None,
    'config.changed': lambda config_name: None,
}
