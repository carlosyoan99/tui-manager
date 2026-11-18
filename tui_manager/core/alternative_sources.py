"""
Gestor de fuentes de instalación alternativas.

Maneja aplicaciones que NO están en los repositorios oficiales o que tienen
múltiples variantes (repo, flatpak, snap, appimage, github).

Reglas importantes:
  1. Siempre notificar al usuario qué fuente se usará.
  2. Pedir confirmación explícita antes de cualquier instalación alternativa.
  3. Si hay varias variantes, pregificar la preferida o usar la configurada.
"""

import os
import shutil
import subprocess
import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict

from .app_catalog import AppEntry

logger = logging.getLogger(__name__)


@dataclass
class InstallSource:
    """Representa una fuente de instalación disponible"""
    type: str                 # 'repo', 'github', 'flatpak', 'snap', 'appimage'
    identifier: str           # id de la fuente
    label: str                # etiqueta legible
    command: List[str]        # comando base a ejecutar
    is_official: bool = False # si viene del repositorio oficial
    requires_sudo: bool = False

    @property
    def Requires_sudo(self) -> bool:
        """Alias legado (deprecado): usar `requires_sudo`."""
        return self.requires_sudo

    def describe(self) -> str:
        return f"[{self.type.upper()}] {self.label}"


class SourceError(Exception):
    """Error al instalar desde una fuente alternativa"""
    pass


class InstallationCancelled(Exception):
    """El usuario canceló la instalación"""
    pass


class AlternativeSourceManager:
    """
    Gestiona la selección e instalación desde fuentes alternativas.

    Args:
        config: Instancia de Config para leer preferencias
        confirm_callback: Función para pedir confirmación (por defecto input()).
                          Debe aceptar (mensaje: str) -> bool.
        select_callback: Función para elegir entre variantes. Debe aceptar
                         (mensaje: str, opciones: List[str]) -> str.
    """

    SOURCE_LABELS = {
        'repo': 'Repositorio oficial',
        'github': 'GitHub (código fuente / release)',
        'flatpak': 'Flatpak',
        'snap': 'Snap',
        'appimage': 'AppImage',
    }

    def __init__(self, config=None,
                 confirm_callback: Callable = None,
                 select_callback: Callable = None,
                 package_manager: str = None):
        self.config = config
        self.confirm_callback = confirm_callback or self._default_confirm
        self.select_callback = select_callback or self._default_select
        self.preferred_format = self._get_preferred_format()
        # Inyectable para tests: evita detectedores que llaman a subprocess.
        self._package_manager = package_manager

    # ------------------------------------------------------------------
    # Preferencias
    # ------------------------------------------------------------------
    def _get_preferred_format(self) -> str:
        """Lee el formato de instalación preferido desde configuración"""
        if self.config:
            pref = self.config.get('preferred_install_method', 'auto')
        else:
            pref = 'auto'
        return pref or 'auto'

    def set_preferred_format(self, fmt: str):
        """Cambia el formato preferido"""
        self.preferred_format = fmt
        if self.config:
            self.config.set('preferred_install_method', fmt)

    # ------------------------------------------------------------------
    # Callbacks por defecto (consola)
    # ------------------------------------------------------------------
    @staticmethod
    def _default_confirm(message: str) -> bool:
        print(f"\n{message}")
        answer = input("  ¿Continuar? [s/N]: ").strip().lower()
        return answer in ('s', 'si', 'sí', 'y', 'yes')

    @staticmethod
    def _default_select(message: str, options: List[str]) -> str:
        print(f"\n{message}")
        for i, opt in enumerate(options, 1):
            print(f"  [{i}] {opt}")
        while True:
            answer = input("  Elige una opción (número): ").strip()
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1]
            print("  Opción inválida. Intenta de nuevo.")

    # ------------------------------------------------------------------
    # Detección de herramientas disponibles
    # ------------------------------------------------------------------
    @staticmethod
    def tool_available(tool: str) -> bool:
        """Verifica si una herramienta está en el PATH (sin subprocess)."""
        return shutil.which(tool) is not None

    def _manager_available(self) -> bool:
        """True solo si el gestor de paquetes de la distro existe y está en PATH."""
        manager = self._package_manager
        if manager is None:
            try:
                from .distribution import DistributionDetector
                manager = DistributionDetector.get_package_manager()
            except Exception:
                manager = None
        return bool(manager) and manager != 'unknown' and self.tool_available(manager)

    def get_available_tools(self) -> Dict[str, bool]:
        """Obtiene qué herramientas de instalación están realmente disponibles."""
        return {
            'flatpak': self.tool_available('flatpak'),
            'snap': self.tool_available('snap'),
            'github': self.tool_available('git') or self.tool_available('curl'),
            'appimage': self.tool_available('wget') or self.tool_available('curl'),
            'repo': self._manager_available(),
        }

    # ------------------------------------------------------------------
    # Construcción de fuentes
    # ------------------------------------------------------------------
    def build_sources(self, app: AppEntry, package_installed: bool = False) -> List[InstallSource]:
        """
        Construye la lista de fuentes disponibles para una aplicación.

        Args:
            app: Entrada del catálogo
            package_installed: True si ya está instalada desde repo

        Returns:
            Lista de fuentes disponibles en el sistema
        """
        available = self.get_available_tools()
        sources = []

        for src_type in app.sources:
            if not available.get(src_type, False):
                continue

            identifier = app.identifiers.get(src_type, app.name)
            label = self.SOURCE_LABELS.get(src_type, src_type)
            command = self._build_command(src_type, identifier)

            sources.append(InstallSource(
                type=src_type,
                identifier=identifier,
                label=f"{label}: {identifier}",
                command=command,
                is_official=(src_type == 'repo'),
                requires_sudo=(src_type in ('repo', 'snap')),
            ))

        return self.validate_sources(sources)

    def validate_sources(self, sources: List[InstallSource]) -> List[InstallSource]:
        """
        Descarta fuentes que no se pueden ejecutar de forma fiable.

        Reglas:
          - todo comando debe tener al menos un argumento;
          - AppImage requiere una URL http(s) real en el identificador
            (no se inventa una ruta de release).
        """
        valid = []
        for source in sources:
            if not source.command:
                logger.debug("Fuente descartada (sin comando): %s", source.type)
                continue
            if source.type == 'appimage':
                ident = source.identifier
                if not isinstance(ident, str) or not ident.startswith(('http://', 'https://')):
                    logger.debug("AppImage descartado (sin URL): %s", ident)
                    continue
            valid.append(source)
        return valid

    def _build_command(self, src_type: str, identifier: str) -> List[str]:
        """Construye el comando de instalación según la fuente"""
        if src_type == 'repo':
            return [identifier]
        elif src_type == 'github':
            return ['git', 'clone', f'https://github.com/{identifier}.git']
        elif src_type == 'flatpak':
            return ['flatpak', 'install', '-y', 'flathub', identifier]
        elif src_type == 'snap':
            return ['snap', 'install', identifier]
        elif src_type == 'appimage':
            # No inventar URLs: solo se acepta una URL http(s) explícita.
            if isinstance(identifier, str) and identifier.startswith(('http://', 'https://')):
                return ['wget', identifier]
            return []
        return []

    # ------------------------------------------------------------------
    # Selección de fuente
    # ------------------------------------------------------------------
    def select_source(self, app: AppEntry,
                      package_installed: bool = False) -> Optional[InstallSource]:
        """
        Selecciona la fuente de instalación, preguntando al usuario si hay
        múltiples variantes o si la fuente no es oficial.

        Returns:
            InstallSource seleccionada, o None si el usuario cancela.
        """
        sources = self.build_sources(app, package_installed)

        if not sources:
            logger.warning("sin fuentes disponibles para %s en este sistema", app.name)
            return None

        # Si solo hay una fuente y es oficial, usarla directamente
        if len(sources) == 1 and sources[0].is_official:
            return sources[0]

        # Aplicar preferencia de formato si está configurada
        if self.preferred_format != 'auto':
            preferred = [s for s in sources if s.type == self.preferred_format]
            if preferred:
                chosen = preferred[0]
                if self._notify_and_confirm(app, chosen):
                    return chosen
                return None

        # Hay múltiples fuentes: preguntar al usuario
        options = [s.describe() for s in sources]
        chosen_label = self.select_callback(
            f"\n📦 '{app.name}' está disponible en varias fuentes. ¿Cuál prefieres?",
            options
        )
        chosen = next((s for s in sources if s.describe() == chosen_label), None)
        if chosen is None:
            return None

        if self._notify_and_confirm(app, chosen):
            return chosen
        return None

    def _notify_and_confirm(self, app: AppEntry, source: InstallSource) -> bool:
        """
        Notifica al usuario sobre la fuente y pide confirmación.

        Las fuentes no oficiales SIEMPRE requieren confirmación.
        """
        if source.is_official:
            message = (
                f"\n📦 Instalación de '{app.name}'\n"
                f"   Fuente: {source.describe()}\n"
                f"   {app.description}"
            )
        else:
            message = (
                f"\n⚠️  INSTALACIÓN DESDE FUENTE ALTERNATIVA\n"
                f"   Aplicación: {app.name}\n"
                f"   Fuente: {source.describe()}\n"
                f"   Identificador: {source.identifier}\n"
                f"   Descripción: {app.description}\n"
                f"\n   Esta instalación NO proviene de los repositorios oficiales.\n"
                f"   El código será descargado desde una fuente externa."
            )

        confirmed = self.confirm_callback(message)
        if not confirmed:
            logger.info(f"Instalación cancelada por el usuario: {app.name}")
        return confirmed

    # ------------------------------------------------------------------
    # Instalación
    # ------------------------------------------------------------------
    def install(self, app: AppEntry, package_installed: bool = False) -> bool:
        """
        Instala una aplicación desde la fuente seleccionada.

        Returns:
            True si se instaló correctamente, False si falló o se canceló.
        """
        source = self.select_source(app, package_installed)
        if source is None:
            return False

        return self._execute_install(app, source)

    # Timeout de una instalación individual (segundos)
    INSTALL_TIMEOUT = 300

    @staticmethod
    def _tail(text: str, lines: int = 20) -> str:
        """Acota stderr/stdout a las últimas líneas para no llenar el log."""
        if not text:
            return ''
        return ' | '.join(text.strip().splitlines()[-lines:])

    def _log_result(self, app, source, *, ok: bool, returncode: int,
                    started: float, error: str = '') -> None:
        """Log estructurado: app, source, returncode, duracion_ms, exit_code."""
        duracion_ms = int((time.monotonic() - started) * 1000)
        base = ('app=%s source=%s returncode=%s duracion_ms=%s exit_code=%s'
                % (app.name, source.type, returncode, duracion_ms,
                   0 if ok else 1))
        if ok:
            logger.info('instalacion_ok %s', base)
        else:
            logger.error('instalacion_fallo %s error=%s', base, self._tail(error))

    def _execute_install(self, app: AppEntry, source: InstallSource) -> bool:
        """Ejecuta la instalación con captura, timeout y logs auditable."""
        command = source.command.copy()
        if source.requires_sudo:
            command.insert(0, 'sudo')

        started = time.monotonic()
        try:
            result = subprocess.run(
                command, capture_output=True, text=True,
                timeout=self.INSTALL_TIMEOUT,
            )
            ok = result.returncode == 0
            self._log_result(
                app, source, ok=ok, returncode=result.returncode,
                started=started, error=result.stderr if not ok else '',
            )
            return ok
        except subprocess.TimeoutExpired:
            self._log_result(app, source, ok=False, returncode=-1,
                             started=started, error='timeout')
            return False
        except FileNotFoundError:
            self._log_result(app, source, ok=False, returncode=-1, started=started,
                             error=f'herramienta no disponible: {command[0]}')
            return False
        except Exception as exc:
            self._log_result(app, source, ok=False, returncode=-1, started=started,
                             error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Utilidades para la TUI
    # ------------------------------------------------------------------
    def get_source_summary(self, app: AppEntry) -> str:
        """Obtiene un resumen legible de las fuentes de una app (para la TUI)"""
        sources = self.build_sources(app)
        if not sources:
            return "Sin fuentes disponibles"
        types = [s.type for s in sources]
        return ", ".join(types)

    def has_alternative_sources(self, app: AppEntry) -> bool:
        """Indica si la app tiene fuentes alternativas a la oficial"""
        return any(src != 'repo' for src in app.sources)
