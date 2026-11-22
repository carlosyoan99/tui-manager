"""
Pantalla de webapps ligeras (función G del roadmap post-1.0).

Lista el catálogo de ``core.webapps``, permite buscar y crear accesos
directos con confirmación. Toda la E/S (escritura del acceso y, opcionalmente,
el lanzamiento en el navegador del entorno) corre en workers en hilo y se
señaliza con ``LoadingIndicator`` + notificación, sin bloquear la UI.
"""

from __future__ import annotations

import logging
import platform
import shlex
from functools import partial
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Static,
)
from textual.containers import Horizontal

from tui_manager.core.environment import Capability, launch_or_focus
from tui_manager.core.webapps import (
    WEBAPPS,
    WebApp,
    create_webapp_desktop_entry,
)
from tui_manager.i18n import t
from tui_manager.ui.app import Services
from tui_manager.ui.screens import ConfirmScreen

logger = logging.getLogger(__name__)


class WebAppsScreen(Screen):
    """Catálogo de sitios web ligeros con accesos directos bajo demanda."""

    BINDINGS = [
        ('enter', 'create', t('webapps.create')),
        ('o', 'open_browser', t('webapps.open')),
        ('f', 'filter', t('common.search')),
        Binding('/', 'filter', show=False),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services, base_dir: str | Path | None = None):
        super().__init__()
        self.services = services
        # `base_dir` se inyecta en tests; en producción se usa el directorio
        # por defecto del core (XDG / Start Menu / ~/Applications).
        self.base_dir = base_dir
        self._visible: list[WebApp] = list(WEBAPPS)
        self._query = ''

    # ---------------------------------------------------------- compose ----
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]◈ {t("webapps.title")}[/]', classes='title')
        yield Input(placeholder=t('webapps.search'), id='webapps-search')
        yield LoadingIndicator(id='webapps-loading')
        yield ListView(id='webapps-list')
        with Horizontal(classes='status-bar'):
            yield Static('', id='webapps-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#webapps-loading', LoadingIndicator).display = True
        self._apply_filter()
        self.query_one('#webapps-loading', LoadingIndicator).display = False
        self.query_one('#webapps-list', ListView).focus()

    # ----------------------------------------------------------- listado ----
    def _apply_filter(self) -> None:
        query = self._query.casefold().strip()
        self._visible = [
            app for app in WEBAPPS
            if not query or query in app.name.casefold()
            or query in app.url.casefold()
            or query in app.category.casefold()
        ]
        view = self.query_one('#webapps-list', ListView)
        view.clear()
        for app in self._visible:
            # Sin id en el ListItem: el filtrado recrea la lista y textual
            # mantiene los ids viejos hasta el siguiente refresh (DuplicateIds).
            view.append(ListItem(
                Static(f'{app.icon_hint}  {app.name} — {app.url}', markup=False),
            ))
        if self._visible:
            view.index = 0
        n = len(self._visible)
        status = t('webapps.status', n=n, category=self._query or t('webapps.all'))
        if not n:
            status = f'{status} · {t("common.empty")}'
        self.query_one('#webapps-status', Static).update(status)

    def _selected(self) -> WebApp | None:
        view = self.query_one('#webapps-list', ListView)
        if view.index is None or not (0 <= view.index < len(self._visible)):
            return None
        return self._visible[view.index]

    @on(Input.Changed, '#webapps-search')
    def search_changed(self, event: Input.Changed) -> None:
        self._query = event.value
        self._apply_filter()

    @on(Input.Submitted, '#webapps-search')
    def search_submitted(self, event: Input.Submitted) -> None:
        self.query_one('#webapps-list', ListView).focus()

    @on(ListView.Selected, '#webapps-list')
    def list_selected(self, event: ListView.Selected) -> None:
        """Enter sobre la lista: textual consume Enter en ListView, así que
        usamos el evento (igual que MainMenuScreen) además del binding."""
        self.action_create()

    def action_filter(self) -> None:
        search = self.query_one('#webapps-search', Input)
        search.focus()
        search.cursor_position = len(search.value)

    def action_back(self) -> None:
        self.app.pop_screen()

    # ------------------------------------------------- crear acceso ---------
    def action_create(self) -> None:
        webapp = self._selected()
        if webapp is None:
            return
        from tui_manager.ui.screens import ConfirmScreen

        self.app.push_screen(
            ConfirmScreen(t('webapps.create_confirm', name=webapp.name)),
            partial(self._confirm_create, webapp),
        )

    def _confirm_create(self, webapp: WebApp, confirmed: bool | None) -> None:
        if confirmed:
            self._create_shortcut(webapp)

    @work(thread=True)
    def _create_shortcut(self, webapp: WebApp) -> None:
        """Escribe el acceso en un worker; nunca bloquea el hilo de la UI."""
        self._set_loading(True)
        try:
            create_webapp_desktop_entry(
                webapp.name, webapp.url,
                browser=self._browser(), base_dir=self.base_dir)
            message = t('webapps.created', name=webapp.name)
            severity = 'information'
        except (ValueError, OSError) as exc:
            logger.warning('No se pudo crear acceso webapp %s: %s', webapp.name, exc)
            message = t('webapps.failed', error=exc)
            severity = 'error'
        finally:
            self._set_loading(False)
        self.app.call_from_thread(self.notify, message, severity=severity)

    def _set_loading(self, visible: bool) -> None:
        def update() -> None:
            try:
                self.query_one('#webapps-loading', LoadingIndicator).display = visible
            except Exception:  # pantalla ya desmontada
                pass
        self.app.call_from_thread(update)

    def _browser(self) -> str | None:
        return self.services.config.get('webapp_browser') or None

    # ------------------------------------- abrir en el navegador (opcional) --
    def action_open_browser(self) -> None:
        webapp = self._selected()
        env = getattr(self.services, 'environment', None)
        if webapp is None or env is None or not env.supports(Capability.LAUNCH_APP):
            self.notify(t('webapps.unavailable'), severity='warning')
            return
        self.notify(t('webapps.opening', name=webapp.name), severity='information')
        self._launch(webapp, env)

    @work(thread=True)
    def _launch(self, webapp: WebApp, env) -> None:
        browser = self._browser() or (
            'open' if platform.system() == 'Darwin' else 'xdg-open')
        command = f'{shlex.quote(browser)} {shlex.quote(webapp.url)}'
        try:
            result = launch_or_focus(env, command)
        except Exception as exc:  # degradación elegante: nunca traceback
            logger.warning('launch_or_focus falló para %s: %s', webapp.name, exc)
            self.app.call_from_thread(
                self.notify, t('webapps.failed', error=exc), severity='error')
            return
        if result.get('action') == 'failed':
            self.app.call_from_thread(
                self.notify, t('webapps.failed', error='launch'), severity='error')
