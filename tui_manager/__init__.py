"""
TUI Manager - Panel de control portable para la terminal (Linux, BSD, Termux)
"""

__version__ = '2.0.0'
__author__ = 'Carlos Yoan'
__license__ = 'MIT'
__description__ = 'Panel de control portable: paquetes, procesos, sistema y temas (Linux, BSD, Termux)'

from .core.distribution import DistributionDetector
from .core.package_manager import PackageManager, Package, PackageNotFoundError, PackageAdapter
from .core.process_monitor import ProcessMonitor, Process, ProcessNotFoundError
from .core.theme_manager import ThemeManager, ThemeError
from .core.config import Config
from .core.event import EventEmitter
from .core.sources_adapter import SourcesAdapter
from .core.app_catalog import APPS, get_app_by_name, search_apps
from .core.alternative_sources import AlternativeSourceManager

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
    'EventEmitter', 'SourcesAdapter', 'APPS',
    'get_app_by_name', 'search_apps', 'AlternativeSourceManager',
]
