"""
Gestor de temas TUI
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class ThemeError(Exception):
    """Excepción para errores de temas"""

    pass


class ThemeManager:
    """Gestor de temas TUI"""

    DEFAULT_THEME = 'dark'

    THEMES = {
        'dark': {
            'primary': 'dark blue',
            'secondary': 'dark cyan',
            'success': 'dark green',
            'warning': 'dark yellow',
            'error': 'dark red',
            'background': 'black',
            'foreground': 'light gray',
            'highlight': 'dark blue',
            'selected': 'dark blue bold',
            'inactive': 'dark gray',
            'border': 'dark gray'
        },
        'light': {
            'primary': 'blue',
            'secondary': 'cyan',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
            'background': 'white',
            'foreground': 'black',
            'highlight': 'blue',
            'selected': 'blue bold',
            'inactive': 'gray',
            'border': 'gray'
        },
        'retro': {
            'primary': 'brown',
            'secondary': 'dark green',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
            'background': 'black',
            'foreground': 'light gray',
            'highlight': 'brown',
            'selected': 'brown bold',
            'inactive': 'dark gray',
            'border': 'dark gray'
        }
    }

    def __init__(self, theme_name: str = None):
        """
        Inicializa el gestor de temas

        Args:
            theme_name: Nombre del tema a usar
        """
        self.theme_name = theme_name or self.DEFAULT_THEME
        self.colors = self.THEMES.get(self.theme_name, self.THEMES['dark'])
        logger.info(f"ThemeManager inicializado con tema: {self.theme_name}")

    def get_current_theme(self) -> str:
        """
        Obtiene el nombre del tema actual

        Returns:
            Nombre del tema
        """
        return self.theme_name

    def set_theme(self, theme_name: str):
        """
        Cambia el tema actual

        Args:
            theme_name: Nombre del nuevo tema

        Raises:
            ThemeError: Si el tema no existe
        """
        if theme_name not in self.THEMES:
            raise ThemeError(f"Tema '{theme_name}' no encontrado")

        self.theme_name = theme_name
        self.colors = self.THEMES[theme_name]
        logger.info(f"Tema cambiado a: {theme_name}")

    def get_colors(self) -> dict:
        """
        Obtiene los colores del tema actual

        Returns:
            Diccionario con los colores
        """
        return self.colors.copy()

    def get_color(self, name: str):
        """
        Obtiene un color específico del tema

        Args:
            name: Nombre del color

        Returns:
            Tupla (foreground, background)
        """
        return self.colors.get(name, self.colors['foreground'])

    def list_themes(self) -> List[str]:
        """
        Lista todos los temas disponibles

        Returns:
            Lista de nombres de temas
        """
        return list(self.THEMES.keys())

    def is_theme_available(self, theme_name: str) -> bool:
        """
        Verifica si un tema está disponible

        Args:
            theme_name: Nombre del tema

        Returns:
            True si el tema está disponible
        """
        return theme_name in self.THEMES

    def get_palette(self):
        """
        Obtiene la paleta de colores para la TUI.

        Formato legacy (lista de tuplas nombre/fg/bg) pendiente de migrar
        a colores de textual (hex por rol) en la Fase Alfa 1.
        """
        colors = self.colors
        return [
            ('default', colors['foreground'], colors['background']),
            ('primary', colors['primary'], colors['background']),
            ('secondary', colors['secondary'], colors['background']),
            ('success', colors['success'], colors['background']),
            ('warning', colors['warning'], colors['background']),
            ('error', colors['error'], colors['background']),
            ('highlight', colors['highlight'], colors['background']),
            ('selected', colors['selected']),
            ('inactive', colors['inactive'], colors['background']),
            ('border', colors['border'], colors['background']),
        ]
