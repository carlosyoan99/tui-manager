"""
Pantallas de TUI Manager (Alfa 1).

- MainMenuScreen: menú con entradas habilitadas y deshabilitadas
  (degradación elegante: Sistema → Alfa 2; Temas/Actualizar → Beta 1).
- PackagesScreen: DataTable de paquetes, instalar/remover/info/caché/buscar.
- ProcessesScreen: monitor con refresco por intervalo, kill/renice/pausa.
- SettingsScreen: tema interno, idioma, intervalo de refresco.
- HelpScreen: atajos y sugerencia de --doctor.
- ConfirmScreen: modal Sí/No reutilizable.
- ScreenManager: fachada de compatibilidad para main.py y tests.
"""

from __future__ import annotations

import logging
from typing import Callable

from textual import on, work
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
)
from textual.containers import VerticalScroll

from tui_manager.i18n import t
from tui_manager.ui.app import Services

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- Menú ----

class MainMenuScreen(Screen):
    """Menú principal con degradación elegante por fase del roadmap."""

    BINDINGS = [('escape', 'app.quit', t('common.quit'))]

    # id de entrada → (fábrica de pantalla, motivo de deshabilitado)
    ENTRIES = (
        ('packages', 'PackagesScreen', None),
        ('processes', 'ProcessesScreen', None),
        ('settings', 'SettingsScreen', None),
        ('help', 'HelpScreen', None),
        ('system', None, 'Alfa 2'),
        ('themes', None, 'Beta 1'),
        ('updates', None, 'Beta 1'),
    )

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("app.title")}[/] — {t("menu.title")}')
        yield ListView(id='menu')
        yield Footer()

    def on_mount(self) -> None:
        menu = self.query_one('#menu', ListView)
        menu.clear()
        for entry_id, _, disabled in self.ENTRIES:
            label = t(f'menu.{entry_id}')
            desc = t(f'menu.{entry_id}.desc')
            if disabled:
                text = f'[dim]{label} — {desc} ({t("menu.coming_soon", phase=disabled)})[/]'
                item = ListItem(Static(text), id=entry_id, classes='disabled')
            else:
                item = ListItem(Static(f'{label} — {desc}'), id=entry_id)
            menu.append(item)

    @on(ListView.Selected)
    def open_entry(self, event: ListView.Selected) -> None:
        entry_id = event.item.id
        if entry_id in ('system', 'themes', 'updates'):
            self.notify(t('menu.coming_soon', phase=dict(
                system='Alfa 2', themes='Beta 1', updates='Beta 1')[entry_id]),
                severity='information')
            return
        from tui_manager.ui import screens
        screen_cls = getattr(screens, dict(
            packages='PackagesScreen', processes='ProcessesScreen',
            settings='SettingsScreen', help='HelpScreen')[entry_id])
        self.app.push_screen(screen_cls(self.services))


# ------------------------------------------------------------ Paquetes ----

class PackagesScreen(Screen):
    """Gestión de aplicaciones: listar, buscar, instalar, remover, caché."""

    BINDINGS = [
        ('i', 'install', t('common.install')),
        ('r', 'remove', t('common.remove')),
        ('u', 'info', t('common.details')),
        ('c', 'cache', t('packages.update_cache')),
        ('f', 'filter', t('common.search')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._packages = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("packages.title")}[/] ({self.services.distribution})')
        yield Input(placeholder=t('common.search'), id='search')
        yield DataTable(id='packages-table')
        yield Static(t('packages.keys'), id='packages-status')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#packages-table', DataTable)
        table.cursor_type = 'row'
        table.add_columns(t('common.name'), t('common.version'),
                          t('common.installed'), t('common.description'))
        self.load_installed()

    @work(thread=True, exclusive=True)
    def load_installed(self) -> None:
        packages = self.services.package_manager.get_installed_packages()
        self.app.call_from_thread(self._fill, packages, t('packages.installed_list'))

    @work(thread=True, exclusive=True)
    def load_search(self, query: str) -> None:
        packages = self.services.package_manager.search_package(query)
        self.app.call_from_thread(self._fill, packages, t('packages.search_results'))

    def _fill(self, packages, origin: str) -> None:
        self._packages = list(packages)
        table = self.query_one('#packages-table', DataTable)
        table.clear()
        for pkg in self._packages:
            table.add_row(pkg.name, pkg.version,
                          '✓' if pkg.installed else '',
                          pkg.description or '')
        self.query_one('#packages-status', Static).update(
            f'{origin}: {len(self._packages)} — {t("packages.keys")}')

    @on(Input.Submitted, '#search')
    def search_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.load_search(query)

    def action_filter(self) -> None:
        self.query_one('#search', Input).focus()

    def _selected_package(self):
        table = self.query_one('#packages-table', DataTable)
        row_key = table.cursor_row
        if 0 <= row_key < len(self._packages):
            return self._packages[row_key]
        return None

    def action_install(self) -> None:
        pkg = self._selected_package()
        if pkg:
            self.app.push_screen(
                ConfirmScreen(f'{t("packages.install_confirm")} {pkg.name}?'),
                self._do_install)

    def _do_install(self, confirmed) -> None:
        if not confirmed:
            return
        pkg = self._selected_package()
        self._run_action(pkg, 'install')

    def action_remove(self) -> None:
        pkg = self._selected_package()
        if pkg:
            self.app.push_screen(
                ConfirmScreen(f'{t("packages.remove_confirm")} {pkg.name}?'),
                self._do_remove)

    def _do_remove(self, confirmed) -> None:
        if not confirmed:
            return
        pkg = self._selected_package()
        self._run_action(pkg, 'remove')

    @work(thread=True, exclusive=False)
    def _run_action(self, pkg, action: str) -> None:
        try:
            if action == 'install':
                ok = self.services.package_manager.install_package(pkg.name, confirm=False)
                key = 'packages.install_ok'
            else:
                ok = self.services.package_manager.remove_package(pkg.name, confirm=False)
                key = 'packages.remove_ok'
            message = t(key, name=pkg.name) if ok else t('packages.action_failed')
            self.app.call_from_thread(self.notify, message,
                                      severity='information' if ok else 'error')
            self.load_installed()
        except Exception as exc:
            logger.exception('acción de paquete falló')
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    def action_info(self) -> None:
        pkg = self._selected_package()
        if pkg:
            self._fetch_info(pkg.name)

    @work(thread=True, exclusive=False)
    def _fetch_info(self, package_name: str) -> None:
        try:
            info = self.services.package_manager.get_package_info(package_name)
            deps = ', '.join(info.dependencies) or '—'
            text = (f'{info.name} {info.version}\n{info.description}\n'
                    f'{t("packages.deps")}: {deps}')
        except Exception as exc:
            text = f'{t("common.error")}: {exc}'
        self.app.call_from_thread(self.notify, text,
                                  title=package_name, timeout=10)

    @work(thread=True, exclusive=False)
    def action_cache(self) -> None:
        try:
            ok = self.services.package_manager.update_package_cache()
            message = t('updates.cache_ok') if ok else t('packages.action_failed')
            self.app.call_from_thread(self.notify, message,
                                      severity='information' if ok else 'error')
        except Exception as exc:
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    def action_back(self) -> None:
        self.app.pop_screen()


# ------------------------------------------------------------ Procesos ----

class ProcessesScreen(Screen):
    """Monitor de procesos con refresco por intervalo configurable."""

    BINDINGS = [
        ('k', 'kill', t('processes.kill')),
        ('K', 'kill9', t('processes.kill9')),
        ('n', 'renice', t('processes.renice')),
        ('p', 'pause', t('processes.paused')),
        ('f', 'filter', t('common.filter')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._processes = []
        self._paused = False
        self._filter = ''

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("processes.title")}[/]')
        yield Input(placeholder=t('common.filter'), id='proc-filter')
        yield DataTable(id='process-table')
        yield Static(t('processes.keys'), id='process-status')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#process-table', DataTable)
        table.cursor_type = 'row'
        table.add_columns(t('processes.pid'), t('common.user'),
                          f'{t("common.cpu")} %', f'{t("common.memory")} %',
                          'NI', 'TIME', 'COMMAND')
        self._interval = self.set_interval(
            max(1, int(self.services.config.get('refresh_interval', 2))),
            self._tick)
        self._tick()

    def _tick(self) -> None:
        if not self._paused:
            self.refresh_table()

    @work(thread=True, exclusive=True)
    def refresh_table(self) -> None:
        filters = {'name': self._filter} if self._filter else None
        processes = self.services.process_monitor.get_processes(filters)
        self.app.call_from_thread(self._fill, processes)

    def _fill(self, processes) -> None:
        self._processes = list(processes)
        table = self.query_one('#process-table', DataTable)
        table.clear()
        for proc in self._processes:
            table.add_row(str(proc.pid), proc.user, f'{proc.cpu:.1f}',
                          f'{proc.mem:.1f}', str(proc.nice), proc.time,
                          proc.command[:60])
        self.query_one('#process-status', Static).update(
            f'{len(self._processes)} — {t("processes.keys")}')

    @on(Input.Submitted, '#proc-filter')
    def filter_submitted(self, event: Input.Submitted) -> None:
        self._filter = event.value.strip()
        self.refresh_table()

    def action_filter(self) -> None:
        self.query_one('#proc-filter', Input).focus()

    def action_pause(self) -> None:
        self._paused = not self._paused
        self.notify(t('processes.paused') if self._paused
                    else t('common.refresh_done'))

    def _selected_process(self):
        table = self.query_one('#process-table', DataTable)
        if 0 <= table.cursor_row < len(self._processes):
            return self._processes[table.cursor_row]
        return None

    def _send_signal(self, confirmed, signal: int) -> None:
        if not confirmed:
            return
        proc = self._selected_process()
        if not proc:
            return
        try:
            ok = self.services.process_monitor.kill_process(proc.pid, signal=signal)
            self.notify(t('processes.kill_ok', pid=proc.pid)
                        if ok else t('processes.kill_failed', pid=proc.pid),
                        severity='information' if ok else 'error')
        except Exception as exc:
            self.notify(f'{t("common.error")}: {exc}', severity='error')
        self.refresh_table()

    def action_kill(self) -> None:
        proc = self._selected_process()
        if proc:
            self.app.push_screen(ConfirmScreen(t('processes.kill_confirm',
                                                  pid=proc.pid,
                                                  name=proc.command[:40])),
                                 lambda ok: self._send_signal(ok, 15))

    def action_kill9(self) -> None:
        proc = self._selected_process()
        if proc:
            self._send_signal(True, 9)  # SIGKILL: sin confirmación (Alfa 1)

    def action_renice(self) -> None:
        proc = self._selected_process()
        if proc:
            self.app.push_screen(InputScreen(t('processes.renice'), '10'),
                                 self._do_renice)

    def _do_renice(self, value) -> None:
        if value is None:
            return
        proc = self._selected_process()
        try:
            nice = int(value)
        except (TypeError, ValueError):
            self.notify(f'{t("common.error")}: {value}', severity='error')
            return
        try:
            ok = self.services.process_monitor.renice_process(proc.pid, nice)
            self.notify(t('processes.kill_ok', pid=proc.pid)
                        if ok else t('processes.kill_failed', pid=proc.pid),
                        severity='information' if ok else 'error')
        except Exception as exc:
            self.notify(f'{t("common.error")}: {exc}', severity='error')
        self.refresh_table()

    def action_back(self) -> None:
        self.app.pop_screen()


# -------------------------------------------------------------- Ajustes ----

class SettingsScreen(Screen):
    """Ajustes: tema interno, idioma, intervalo de refresco."""

    BINDINGS = [('escape', 'back', t('common.back'))]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("settings.title")}[/]')
        yield VerticalScroll(
            Select(
                [(name, name) for name in self.services.theme_manager.THEMES],
                value=self.services.config.get('theme', 'dark'),
                id='select-theme',
                prompt=t('settings.tui_theme'),
                allow_blank=False,
            ),
            Select(
                [('Español', 'es'), ('English', 'en')],
                value=self.services.config.get('language', 'es'),
                id='select-language',
                prompt=t('common.language'),
                allow_blank=False,
            ),
            Input(value=str(self.services.config.get('refresh_interval', 2)),
                  id='input-interval', placeholder=t('settings.refresh_interval')),
            Static(t('settings.termux_note'), id='settings-note'),
        )
        yield Footer()

    @on(Select.Changed, '#select-theme')
    def theme_changed(self, event: Select.Changed) -> None:
        name = str(event.value)
        self.services.config.set_theme(name)
        self.services.theme_manager.set_theme(name)
        self.app.apply_tui_theme(name)
        self.notify(t('settings.saved'))

    @on(Select.Changed, '#select-language')
    def language_changed(self, event: Select.Changed) -> None:
        from tui_manager.i18n import set_language
        lang = set_language(str(event.value))
        self.services.config.set('language', lang)
        self.notify(t('settings.saved'))

    @on(Input.Submitted, '#input-interval')
    def interval_submitted(self, event: Input.Submitted) -> None:
        try:
            self.services.config.set_refresh_interval(int(event.value))
            self.notify(t('settings.saved'))
        except (TypeError, ValueError):
            self.notify(f'{t("common.error")}: {event.value}', severity='error')

    def action_back(self) -> None:
        self.app.pop_screen()


# ---------------------------------------------------------------- Ayuda ----

class HelpScreen(Screen):
    """Atajos de teclado y diagnóstico."""

    BINDINGS = [('escape', 'back', t('common.back'))]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            yield Static(
                f'[b]{t("help.title")}[/]\n\n'
                f'{t("help.keys_general")}\n\n'
                f'{t("packages.keys")}\n'
                f'{t("processes.keys")}\n\n'
                f'{t("help.doctor_hint")}\n'
                f'{t("settings.termux_note")}',
                id='help-text')
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# ---------------------------------------------------------------- Modals ----

class ConfirmScreen(ModalScreen):
    """Modal Sí/No; dismiss(True/False) llega al callback de push_screen."""

    BINDINGS = [('y', 'yes', t('common.yes')), ('n', 'no', t('common.no')),
                ('escape', 'no', t('common.no'))]

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Label(self.message, id='confirm-message')
        yield Footer()

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class InputScreen(ModalScreen):
    """Modal de entrada de texto simple; dismiss(str) o dismiss(None)."""

    BINDINGS = [('escape', 'cancel', t('common.cancel'))]

    def __init__(self, prompt: str, value: str = ''):
        super().__init__()
        self.prompt = prompt
        self.value = value

    def compose(self) -> ComposeResult:
        yield Label(self.prompt)
        yield Input(value=self.value, id='modal-input')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#modal-input', Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


# -------------------------------------------------------- Compatibilidad ----

class ScreenManager:
    """Fachada de compatibilidad: construye servicios y lanza la App.

    main.py y los tests importan `from tui_manager.ui.screens import
    ScreenManager`; `ScreenManager().run()` lanza la aplicación completa.
    """

    def __init__(self, services: Services = None):
        self.services = services

    def run(self) -> None:
        from tui_manager.ui.app import TuiManagerApp
        TuiManagerApp(self.services).run()
