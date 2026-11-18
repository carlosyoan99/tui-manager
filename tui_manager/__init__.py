"""
TUI Manager - Gestor de Paquetes y Procesos TUI para Linux
"""

__version__ = '0.2.0-alpha.2'
__author__ = 'Tu Nombre'
__license__ = 'MIT'
__description__ = 'Gestor de paquetes y monitoreo de procesos TUI para Linux'

from .core.distribution import DistributionDetector
from .core.package_manager import PackageManager, Package, PackageNotFoundError, PackageAdapter
from .core.process_monitor import ProcessMonitor, Process, ProcessNotFoundError
from .core.theme_manager import ThemeManager, ThemeError
from .core.config import Config
from .core.event import EventEmitter

__all__ = [
    'DistributionDetector',
    'PackageManager',
    'Package',
    'PackageNotFoundError',
    'PackageAdapter',
    'ProcessMonitor',
    'Process',
    'ProcessNotFoundError',
    'ThemeManager',
    'ThemeError',
    'Config',
    'EventEmitter',
]
