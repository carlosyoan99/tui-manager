"""
Capa de interfaz TUI (textual) de TUI Manager.

Alfa 1: Menú principal, Aplicaciones (paquetes), Procesos, Ajustes y Ayuda.
Las entradas de Sistema (Alfa 2), Temas y Actualizar (Beta 1) aparecen
deshabilitadas para mostrar la degradación elegante del roadmap.
"""

from tui_manager.ui.app import TuiManagerApp, Services, VERSION

__all__ = ['TuiManagerApp', 'Services', 'VERSION']
