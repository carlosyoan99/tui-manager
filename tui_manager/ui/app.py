"""
Aplicación textual de TUI Manager.

`Services` agrupa todos los servicios del núcleo y se inyecta en las
pantallas (facilita los tests con fakes). `TuiManagerApp` registra los
temas internos (dark/light/retro de ThemeManager) como temas de textual.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from textual.app import App
from textual.theme import Theme

from tui_manager import __version__
from tui_manager.i18n import set_language, t
from tui_manager.core.config import Config
from tui_manager.core.distribution import DistributionDetector
from tui_manager.core.environment import EnvironmentDetector
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.process_monitor import ProcessMonitor
from tui_manager.core.system_control import SystemControl
from tui_manager.core.theme_manager import ThemeManager

logger = logging.getLogger(__name__)

VERSION = __version__

# Colores hex de los temas internos (ThemeManager usa nombres CSS2 que
# textual no parsea siempre; hex es portable).
_HEX = {
    'dark': dict(
        background='#000000', foreground='#c8c8c8', primary='#5f87af',
        secondary='#5f8787', accent='#af5f87', success='#5faf5f',
        warning='#d7af5f', error='#af5f5f',
    ),
    'light': dict(
        background='#ffffff', foreground='#101010', primary='#5f5fff',
        secondary='#008787', accent='#af00af', success='#00af00',
        warning='#af8700', error='#af0000',
    ),
    'retro': dict(
        background='#0a0a0a', foreground='#c8c878', primary='#af875f',
        secondary='#87af87', accent='#d7875f', success='#87af5f',
        warning='#d7af5f', error='#af5f5f',
    ),
}


def textui_theme(name: str) -> Theme:
    """Construye un Theme de textual a partir de ThemeManager.THEMES."""
    colors = dict(_HEX.get(name) or _HEX['dark'])
    colors.setdefault('accent', colors['primary'])
    return Theme(
        name=f'tm-{name}',
        primary=colors['primary'],
        secondary=colors['secondary'],
        accent=colors['accent'],
        foreground=colors['foreground'],
        background=colors['background'],
        success=colors['success'],
        warning=colors['warning'],
        error=colors['error'],
        dark=name != 'light',
    )


@dataclass
class Services:
    """Servicios del núcleo compartidos por las pantallas.

    Todos los campos tienen valores por defecto para que los tests puedan
    sustituir cualquier pieza con un fake.
    """
    config: Config = field(default_factory=Config)
    package_manager: PackageManager = None
    process_monitor: ProcessMonitor = field(default_factory=ProcessMonitor)
    theme_manager: ThemeManager = field(default_factory=ThemeManager)
    system_control: SystemControl = field(default_factory=SystemControl)
    environment: object = None
    distribution: str = ''

    @classmethod
    def detect(cls, config: Config = None, distribution: str = None) -> 'Services':
        """Crea los servicios reales detectando distribución y entorno."""
        config = config or Config()
        set_language(config.get('language', 'es'))
        distribution = distribution or DistributionDetector.detect()
        environment = EnvironmentDetector.detect()
        return cls(
            config=config,
            package_manager=PackageManager(distribution=distribution),
            process_monitor=ProcessMonitor(),
            theme_manager=ThemeManager(config.get('theme', 'dark')),
            system_control=SystemControl(environment=environment),
            environment=environment,
            distribution=distribution,
        )


class TuiManagerApp(App):
    """Aplicación principal: empuja el menú principal al arrancar."""

    TITLE = 'TUI Manager'
    CSS_PATH = 'app.tcss'
    ENABLE_COMMAND_PALETTE = True
    BINDINGS = [
        ('q', 'quit', t('common.quit')),
        ('?', 'help', t('common.help')),
    ]

    def __init__(self, services: Services = None):
        super().__init__()
        self.services = services or Services.detect()
        self._inject_elevator()
        self._register_themes()

    def _elevation_tool(self) -> Optional[str]:
        """Herramienta disponible para pedir credenciales en el TTY real."""
        if shutil.which('sudo'):
            return 'sudo'
        if shutil.which('doas'):
            return 'doas'
        return None

    def elevate(self) -> bool:
        """Suspende la TUI y ejecuta ``<tool> -v`` en el TTY real.

        Es el hook que se inyecta en los adapters: cuando no hay credenciales
        cacheadas, ``PackageAdapter.execute_command`` lo invoca para que el
        usuario escriba su contraseña en la terminal, sin que la TUI la
        capture ni la almacene. Devuelve True si se obtuvieron credenciales.
        """
        tool = self._elevation_tool()
        if tool is None:
            self._notify_elevation(
                'Elevación no disponible',
                'Instala sudo o doas para realizar esta acción.',
                severity='warning',
            )
            return False
        try:
            with self.suspend():
                result = subprocess.run([tool, '-v'], check=False)
            ok = result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            logger.debug('elevación cancelada o fallida', exc_info=True)
            ok = False
        except Exception:
            logger.debug('elevación no disponible en este entorno', exc_info=True)
            ok = False

        if ok:
            self._notify_elevation(
                'Sesión elevada', 'Credenciales obtenidas; reintentando…')
        else:
            self._notify_elevation(
                'Elevación cancelada',
                f'Ejecuta {tool} -v en la terminal y vuelve a intentarlo.',
                severity='warning',
            )
        return ok

    def _notify_elevation(self, title: str, message: str,
                          severity: str = 'information') -> None:
        """Notifica al volver de suspender, tolerando entornos sin pantalla."""
        try:
            self.notify(title, message, severity=severity)
        except Exception:
            logger.debug('notify no disponible durante la elevación',
                         exc_info=True)

    def _inject_elevator(self) -> None:
        """Conecta ``elevate`` con el adapter real del PackageManager."""
        manager = getattr(self.services, 'package_manager', None)
        adapter = getattr(manager, 'adapter', None)
        if adapter is None:
            return
        try:
            adapter.elevator = self.elevate
        except Exception:
            logger.debug('no se pudo inyectar el elevador en el adapter',
                         exc_info=True)

    def notify_native(self, title: str, message: str) -> None:
        """Notificación nativa opcional (config `native_notifications`)."""
        try:
            if self.services.config.get('native_notifications', False):
                from tui_manager.ui.notifications import notify as native_notify
                native_notify(title, message)
        except Exception:
            logger.debug('notificación nativa omitida', exc_info=True)

    def _register_themes(self):
        """Registra los temas internos como temas de textual."""
        for name in self.services.theme_manager.THEMES:
            try:
                self.register_theme(textui_theme(name))
            except Exception as exc:  # versión de textual sin register_theme
                logger.warning(f"No se pudo registrar el tema '{name}': {exc}")

    def apply_tui_theme(self, name: str):
        """Cambia el tema textual al tema interno dado."""
        key = f'tm-{name}'
        if key not in self.available_themes:
            self._register_themes()
        if key in self.available_themes:
            self.theme = key

    def on_mount(self):
        self.theme = f'tm-{self.services.config.get("theme", "dark")}'
        from tui_manager.ui.screens import MainMenuScreen
        self.push_screen(MainMenuScreen(self.services))

    def action_help(self):
        from tui_manager.ui.screens import HelpScreen
        self.push_screen(HelpScreen(self.services,
                                    context=type(self.screen).__name__))

    def subtitle(self):  # usado por textual si se define SUBTITLE dinámico
        return t('app.subtitle')
