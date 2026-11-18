"""
Módulo core de TUI Manager
"""

from .distribution import DistributionDetector
from .package_manager import PackageManager, Package, PackageNotFoundError, PackageAdapter
from .process_monitor import ProcessMonitor, Process, ProcessNotFoundError
from .theme_manager import ThemeManager, ThemeError
from .config import Config
from .event import EventEmitter

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
