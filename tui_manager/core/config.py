"""
Módulo de configuración
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Excepción para errores de configuración"""

    pass


class Config:
    """Gestor de configuración"""

    DEFAULT_CONFIG = {
        'theme': 'dark',
        'auto_update': True,
        'refresh_interval': 2,
        'show_details': True,
        'sort_by': 'name',
        'sort_order': 'asc',
        'default_category': 'all',
        'show_notifications': True,
        'log_level': 'info',
        'default_package_manager': None
    }

    def __init__(self, config_file: str = None):
        """
        Inicializa el gestor de configuración

        Args:
            config_file: Ruta del archivo de configuración
        """
        self.config_file = config_file or os.path.expanduser('~/.tui-manager/config.yaml')
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """
        Carga la configuración desde archivo

        Returns:
            Diccionario con la configuración
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    if config:
                        # Merge con configuración por defecto
                        return {**self.DEFAULT_CONFIG, **config}
            except yaml.YAMLError as e:
                logger.warning(f"Error al leer archivo de configuración: {e}")
                return self.DEFAULT_CONFIG.copy()
            except Exception as e:
                logger.warning(f"Error al cargar configuración: {e}")
                return self.DEFAULT_CONFIG.copy()

        # Configuración por defecto
        return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Guarda la configuración en archivo"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.debug("Configuración guardada")
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            raise ConfigError(f"No se pudo guardar la configuración: {e}")

    def get(self, key: str, default=None):
        """
        Obtiene un valor de configuración

        Args:
            key: Clave de configuración
            default: Valor por defecto si la clave no existe

        Returns:
            Valor de configuración
        """
        return self.config.get(key, default)

    def set(self, key: str, value):
        """
        Establece un valor de configuración

        Args:
            key: Clave de configuración
            value: Valor a establecer

        Raises:
            ConfigError: Si hay un error al establecer el valor
        """
        self.config[key] = value
        self.save_config()

    def get_all(self) -> dict:
        """
        Obtiene todos los valores de configuración

        Returns:
            Diccionario con toda la configuración
        """
        return self.config.copy()

    def set_all(self, config_dict: dict):
        """
        Establece todos los valores de configuración

        Args:
            config_dict: Diccionario con la nueva configuración

        Raises:
            ConfigError: Si hay un error al establecer la configuración
        """
        self.config = {**self.DEFAULT_CONFIG, **config_dict}
        self.save_config()

    def reset_to_default(self):
        """Restaura la configuración a los valores por defecto"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()

    def remove_key(self, key: str):
        """
        Elimina una clave de configuración

        Args:
            key: Clave a eliminar
        """
        if key in self.config:
            del self.config[key]
            self.save_config()

    def get_log_level(self):
        """
        Obtiene el nivel de logging

        Returns:
            Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level_str = self.get('log_level', 'info')
        level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        return level_map.get(level_str.lower(), logging.INFO)

    def get_theme(self) -> str:
        """Obtiene el tema actual"""
        return self.get('theme', 'dark')

    def set_theme(self, theme_name: str):
        """Establece el tema"""
        self.set('theme', theme_name)

    def get_refresh_interval(self) -> int:
        """Obtiene el intervalo de actualización"""
        return self.get('refresh_interval', 2)

    def set_refresh_interval(self, interval: int):
        """Establece el intervalo de actualización"""
        if interval < 1:
            interval = 1
        self.set('refresh_interval', interval)

    def get_auto_update(self) -> bool:
        """Obtiene si la actualización automática está activa"""
        return self.get('auto_update', True)

    def set_auto_update(self, enabled: bool):
        """Establece si la actualización automática está activa"""
        self.set('auto_update', enabled)

    def get_show_details(self) -> bool:
        """Obtiene si se muestran detalles"""
        return self.get('show_details', True)

    def set_show_details(self, show: bool):
        """Establece si se muestran detalles"""
        self.set('show_details', show)

    def get_sort_by(self) -> str:
        """Obtiene el criterio de ordenamiento"""
        return self.get('sort_by', 'name')

    def set_sort_by(self, sort_by: str):
        """Establece el criterio de ordenamiento"""
        self.set('sort_by', sort_by)

    def get_sort_order(self) -> str:
        """Obtiene el orden de ordenamiento"""
        return self.get('sort_order', 'asc')

    def set_sort_order(self, sort_order: str):
        """Establece el orden de ordenamiento"""
        self.set('sort_order', sort_order)

    def get_default_category(self) -> str:
        """Obtiene la categoría por defecto"""
        return self.get('default_category', 'all')

    def set_default_category(self, category: str):
        """Establece la categoría por defecto"""
        self.set('default_category', category)
