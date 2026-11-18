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

# Catálogo y fuentes alternativas (Alfa 3)
from .app_catalog import (
    AppEntry, CATEGORIES as APP_CATEGORIES, APPS,
    get_app_by_name, search_apps, get_apps_by_category, get_all_categories,
)
from .alternative_sources import (
    InstallSource, AlternativeSourceManager, SourceError, InstallationCancelled,
)
from .sources_adapter import SourcesAdapter
