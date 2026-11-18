"""
Adaptador de fuentes para la capa TUI.

Expone una API simple y testeable sobre el catálogo de apps y el gestor de
fuentes alternativas, para que las pantallas no dependan de detalles de
subprocess ni de callbacks de consola.
"""

import logging
from typing import List, Optional

from .app_catalog import (
    AppEntry, get_app_by_name, search_apps, get_apps_by_category,
    get_all_categories, CATEGORIES,
)
from .alternative_sources import (
    AlternativeSourceManager, InstallSource, InstallResult,
)

logger = logging.getLogger(__name__)


class SourcesAdapter:
    """Fachada TUI para el catálogo y las fuentes de instalación."""

    def __init__(self, config=None):
        self.config = config
        self.manager = AlternativeSourceManager(config=config)

    # --- catálogo ---
    def list_apps(self, category: str = 'all', query: str = '') -> List[AppEntry]:
        """Lista apps, opcionalmente filtradas por categoría y búsqueda."""
        apps = get_apps_by_category(category)
        if query:
            query = query.lower()
            apps = [a for a in apps
                    if query in a.name.lower() or query in a.description.lower()]
        return apps

    def get_app(self, name: str) -> Optional[AppEntry]:
        """Obtiene una app por nombre."""
        return get_app_by_name(name)

    def categories(self) -> dict:
        """Devuelve el mapa de categorías (id -> etiqueta)."""
        return get_all_categories()

    # --- fuentes ---
    def sources_for(self, app: AppEntry) -> List[InstallSource]:
        """Obtiene las fuentes disponibles para una app."""
        return self.manager.build_sources(app)

    def source_summary(self, app: AppEntry) -> str:
        """Resumen legible de fuentes para mostrar en la tabla."""
        return self.manager.get_source_summary(app)

    def has_alternatives(self, app: AppEntry) -> bool:
        """Indica si la app tiene fuentes no oficiales."""
        return self.manager.has_alternative_sources(app)

    def preferred_format(self) -> str:
        """Formato de instalación preferido según configuración."""
        return self.manager.preferred_format

    def set_preferred_format(self, fmt: str):
        """Cambia el formato preferido."""
        self.manager.set_preferred_format(fmt)

    # --- instalación ---
    def install(self, app: AppEntry, source: InstallSource) -> InstallResult:
        """
        Instala una app desde una fuente concreta.

        La confirmación de fuentes no oficiales ya fue gestionada por la TUI
        antes de llegar aquí (SelectScreen + ConfirmScreen).
        """
        return self.manager._execute_install(app, source)

    def describe_source(self, source: InstallSource) -> str:
        """Descripción legible de una fuente."""
        return source.describe()

    def is_official(self, source: InstallSource) -> bool:
        """Indica si la fuente es el repositorio oficial."""
        return source.is_official
