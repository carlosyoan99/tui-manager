"""
Pantallas de TUI Manager (Alfa 3).

- MainMenuScreen: menú principal con atajos 1–9 y todas las entradas activas.
- PackagesScreen: DataTable de paquetes, instalar/remover/info/caché/buscar.
- ProcessesScreen: monitor con refresco por intervalo, kill/renice/pausa/orden.
- ThemesScreen: packs de tema, wallpaper, claro/oscuro, instalar desde URL.
- UpdatesScreen: actualizaciones, upgrade, caché, huérfanos, firmware.
- SettingsScreen: tema interno, idioma, intervalo de refresco.
- HelpScreen: atajos contextuales y sugerencia de --doctor.
- ConfirmScreen/InputScreen: modales reutilizables.
- ScreenManager: fachada de compatibilidad para main.py y tests.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Callable

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Select,
    Static,
)
from textual.containers import Vertical, VerticalScroll

from tui_manager.i18n import t
from tui_manager.ui.app import Services
from tui_manager.core.sources_adapter import SourcesAdapter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- Menú ----

class MainMenuScreen(Screen):
    """Menú principal: todas las entradas activas + atajos numéricos."""

    ENTRIES = (
        ('packages', 'PackagesScreen'),
        ('processes', 'ProcessesScreen'),
        ('system', 'SystemScreen'),
        ('themes', 'ThemesScreen'),
        ('updates', 'UpdatesScreen'),
        ('settings', 'SettingsScreen'),
        ('help', 'HelpScreen'),
        ('about', 'AboutScreen'),
        ('logs', 'LogsScreen'),
        ('apps', 'AppsScreen'),
    )

    BINDINGS = [
        Binding('escape', 'app.quit', t('common.quit')),
    ] + [
        Binding('0' if index == 9 else str(index + 1),
                f'quick("{entry_id}")', show=False)
        for index, (entry_id, _) in enumerate(ENTRIES)
    ]

    @staticmethod
    def shortcut(index: int) -> str:
        """Tecla de atajo para la entrada `index` (1-9, y 0 para la 10ª)."""
        return '0' if index == 9 else str(index + 1)

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("app.title")}[/] — {t("menu.title")}', classes='title')
        yield ListView(id='menu')
        yield Static(t('menu.keys'), id='menu-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        menu = self.query_one('#menu', ListView)
        menu.clear()
        for index, (entry_id, _) in enumerate(self.ENTRIES):
            label = t(f'menu.{entry_id}')
            desc = t(f'menu.{entry_id}.desc')
            key = self.shortcut(index)
            menu.append(ListItem(
                Static(f'[{key}] {label} — {desc}', markup=False), id=entry_id))
        if self.ENTRIES:
            menu.index = 0
        menu.focus()

    @on(ListView.Selected)
    def open_entry(self, event: ListView.Selected) -> None:
        if event.item.id:
            self._open(event.item.id)

    def action_quick(self, entry_id: str) -> None:
        """Atajo numérico 1–9 → abre la entrada correspondiente."""
        self._open(entry_id)

    def _open(self, entry_id: str) -> None:
        from tui_manager.ui import screens
        screen_cls = getattr(screens, {
            'packages': 'PackagesScreen', 'processes': 'ProcessesScreen',
            'system': 'SystemScreen', 'themes': 'ThemesScreen',
            'updates': 'UpdatesScreen', 'settings': 'SettingsScreen',
            'help': 'HelpScreen', 'about': 'AboutScreen',
            'logs': 'LogsScreen', 'apps': 'AppsScreen',
        }[entry_id])
        if screen_cls is HelpScreen:
            self.app.push_screen(screen_cls(self.services, context='MainMenuScreen'))
        else:
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
        Binding('/', 'filter', show=False),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._packages = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("packages.title")}[/] ({self.services.distribution})',
                    classes='title')
        yield Input(placeholder=t('common.search'), id='search')
        yield LoadingIndicator(id='packages-loading')
        yield DataTable(id='packages-table')
        yield Static(t('packages.keys'), id='packages-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#packages-table', DataTable)
        table.cursor_type = 'row'
        table.add_columns(t('common.name'), t('common.version'),
                          t('common.installed'), t('common.description'))
        table.focus()
        self.query_one('#packages-loading', LoadingIndicator).display = True
        self.load_installed()

    @work(thread=True, exclusive=True)
    def load_installed(self) -> None:
        packages = self.services.package_manager.get_installed_packages()
        self.app.call_from_thread(self._fill, packages, t('packages.installed_list'))

    @work(thread=True, exclusive=True)
    def load_search(self, query: str) -> None:
        self.query_one('#packages-loading', LoadingIndicator).display = True
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
        try:
            self.query_one('#packages-loading', LoadingIndicator).display = False
        except Exception:
            pass
        self.query_one('#packages-status', Static).update(
            f'{origin}: {len(self._packages)} — {t("packages.keys")}')

    @on(Input.Submitted, '#search')
    def search_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.load_search(query)
            self.query_one('#packages-table', DataTable).focus()

    def action_filter(self) -> None:
        search = self.query_one('#search', Input)
        search.focus()
        search.cursor_position = len(search.value)

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
        self.app.call_from_thread(
            lambda: setattr(self.query_one('#packages-loading', LoadingIndicator),
                            'display', True))
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
        """Esc: si el buscador tiene el foco, vuelve a la tabla; si no, atrás."""
        if isinstance(self.focused, Input):
            self.query_one('#packages-table', DataTable).focus()
            return
        self.app.pop_screen()


# ------------------------------------------------------------ Procesos ----

class ProcessesScreen(Screen):
    """Monitor de procesos con refresco por intervalo configurable."""

    BINDINGS = [
        ('k', 'kill', t('processes.kill')),
        ('K', 'kill9', t('processes.kill9')),
        ('n', 'renice', t('processes.renice')),
        ('p', 'pause', t('processes.paused')),
        ('s', 'sort', t('processes.sort')),
        ('f', 'filter', t('common.filter')),
        Binding('/', 'filter', show=False),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._processes = []
        self._paused = False
        self._filter = ''
        self._sort = 'cpu'

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("processes.title")}[/]', classes='title')
        yield Input(placeholder=t('common.filter'), id='proc-filter')
        yield DataTable(id='process-table')
        yield Static(t('processes.keys'), id='process-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#process-table', DataTable)
        table.cursor_type = 'row'
        table.add_columns(t('processes.pid'), t('common.user'),
                          f'{t("common.cpu")} %', f'{t("common.memory")} %',
                          'NI', 'TIME', 'COMMAND')
        table.focus()
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
        if self._sort == 'mem':
            ordered = sorted(processes, key=lambda p: p.mem, reverse=True)
        else:
            ordered = sorted(processes, key=lambda p: p.cpu, reverse=True)
        self._processes = list(ordered)
        table = self.query_one('#process-table', DataTable)
        table.clear()
        for proc in ordered:
            table.add_row(str(proc.pid), proc.user, f'{proc.cpu:.1f}',
                          f'{proc.mem:.1f}', str(proc.nice), proc.time,
                          proc.command[:60])
        sort_label = t(f'processes.sort_{self._sort}')
        self.query_one('#process-status', Static).update(
            f'{len(self._processes)} · {sort_label} — {t("processes.keys")}')

    @on(Input.Submitted, '#proc-filter')
    def filter_submitted(self, event: Input.Submitted) -> None:
        self._filter = event.value.strip()
        self.refresh_table()
        self.query_one('#process-table', DataTable).focus()

    def action_filter(self) -> None:
        inp = self.query_one('#proc-filter', Input)
        inp.focus()
        inp.cursor_position = len(inp.value)

    def action_sort(self) -> None:
        self._sort = 'mem' if self._sort == 'cpu' else 'cpu'
        self._fill(self._processes)

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
        if isinstance(self.focused, Input):
            self.query_one('#process-table', DataTable).focus()
            return
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
        yield Label(f'[b]{t("settings.title")}[/]', classes='title')
        yield VerticalScroll(
            Label(f'[b]{t("settings.tui_theme")}[/]'),
            Static(t('settings.theme_help'), classes='hint', markup=False),
            Select(
                [(name, name) for name in self.services.theme_manager.THEMES],
                value=self.services.config.get('theme', 'dark'),
                id='select-theme',
                prompt=t('settings.tui_theme'),
                allow_blank=False,
            ),
            Label(f'[b]{t("common.language")}[/]'),
            Static(t('settings.language_help'), classes='hint', markup=False),
            Select(
                [('Español', 'es'), ('English', 'en')],
                value=self.services.config.get('language', 'es'),
                id='select-language',
                prompt=t('common.language'),
                allow_blank=False,
            ),
            Label(f'[b]{t("settings.refresh_interval")}[/]'),
            Static(t('settings.interval_help'), classes='hint', markup=False),
            Input(value=str(self.services.config.get('refresh_interval', 2)),
                  id='input-interval', placeholder=t('settings.refresh_interval')),
            Static(t('settings.termux_note'), id='settings-note', classes='status', markup=False),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#select-theme', Select).focus()

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
    """Atajos de teclado (contextuales) y diagnóstico."""

    BINDINGS = [('escape', 'back', t('common.back'))]

    # pantalla → claves i18n con sus atajos propios
    CONTEXT_KEYS = {
        'MainMenuScreen': ('menu.keys',),
        'PackagesScreen': ('packages.keys',),
        'ProcessesScreen': ('processes.keys',),
        'ThemesScreen': ('themes.keys',),
        'UpdatesScreen': ('updates.keys',),
        'SystemScreen': ('system.keys',),
    }

    def __init__(self, services: Services, context: str = ''):
        super().__init__()
        self.services = services
        self.context = context

    def compose(self) -> ComposeResult:
        lines = [t('help.keys_general'), t('help.keys_search')]
        keys = self.CONTEXT_KEYS.get(self.context, ())
        if keys:
            lines.append('')
            lines.append(t('help.context'))
            lines += [t(key) for key in keys]
        lines += ['', t('help.doctor_hint'), t('settings.termux_note')]
        yield Header(show_clock=True)
        yield Label(f'[b]{t("help.title")}[/]', classes='title')
        with VerticalScroll():
            yield Static('\n'.join(lines), id='help-text', markup=False)
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# ---------------------------------------------------------------- Temas ----

class ThemesScreen(Screen):
    """Packs de tema (aplicar, wallpaper, claro/oscuro, instalar URL)."""

    BINDINGS = [
        ('a', 'apply', t('themes.apply')),
        ('w', 'wallpaper_next', t('themes.wallpaper_next')),
        ('W', 'wallpaper_prev', t('themes.wallpaper_prev')),
        ('d', 'dark', t('system.dark_mode')),
        ('l', 'light', t('system.light_mode')),
        ('i', 'install', t('themes.install_url')),
        ('r', 'reload', t('common.refresh')),
        ('escape', 'back', t('common.back')),
    ]

    WALLPAPER_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._packs = []
        self._wall_index = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("themes.title")}[/]', classes='title')
        yield ListView(id='themes-list')
        yield Static(t('themes.keys'), id='themes-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.action_reload()
        self.query_one('#themes-list', ListView).focus()

    def action_reload(self) -> None:
        from tui_manager.core.theme_packs import list_packs
        self._packs = list_packs()
        menu = self.query_one('#themes-list', ListView)
        menu.clear()
        for pack in self._packs:
            mode = 'dark' if pack.dark else 'light'
            wallpaper = os.path.basename(pack.wallpaper) if pack.wallpaper else '—'
            menu.append(ListItem(
                Static(f'{pack.name}  [dim]({mode}, {wallpaper})[/]'),
                id=pack.name))
        if self._packs:
            menu.index = 0
        self.query_one('#themes-status', Static).update(
            f'{t("themes.packs")}: {len(self._packs)} — {t("themes.keys")}')

    def _selected_pack(self):
        menu = self.query_one('#themes-list', ListView)
        if self._packs and 0 <= menu.index < len(self._packs):
            return self._packs[menu.index]
        return None

    # --- aplicar pack ---

    def action_apply(self) -> None:
        pack = self._selected_pack()
        if not pack:
            self.notify(t('themes.no_pack'), severity='warning')
            return
        self._apply_worker(pack)

    @work(thread=True, exclusive=True)
    def _apply_worker(self, pack) -> None:
        from tui_manager.core.theme_packs import apply_pack
        try:
            summary = apply_pack(pack, self.services.environment)
            applied = ', '.join(summary['applied']) or '—'
            message = f'{t("themes.applied", name=pack.name)} · {applied}'
            if summary['skipped']:
                message += (f' · {t("themes.skipped")}: '
                            + ', '.join(summary['skipped']))
            self.app.call_from_thread(self.notify, message, timeout=8)
            self.app.call_from_thread(self._mirror_internal_theme, pack)
        except Exception as exc:
            logger.exception('aplicar pack falló')
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    def _mirror_internal_theme(self, pack) -> None:
        """Refleja el modo del pack en el tema interno (sin persistir)."""
        name = 'dark' if pack.dark else 'light'
        if name in self.services.theme_manager.THEMES:
            self.app.apply_tui_theme(name)

    # --- wallpaper ---

    def _wallpapers(self, pack):
        wallpaper = pack.wallpaper
        if not wallpaper:
            # convención: config/themes/wallpapers/<pack>/ con imágenes
            wallpaper = os.path.join(os.path.dirname(pack.source),
                                     'wallpapers', pack.name)
        if not os.path.isabs(wallpaper):
            wallpaper = os.path.join(os.path.dirname(pack.source), wallpaper)
        if os.path.isdir(wallpaper):
            try:
                names = sorted(os.listdir(wallpaper))
            except OSError:
                return []
            return [os.path.join(wallpaper, n) for n in names
                    if n.lower().endswith(self.WALLPAPER_EXTS)]
        return [wallpaper]

    def action_wallpaper_next(self) -> None:
        self._cycle_wallpaper(1)

    def action_wallpaper_prev(self) -> None:
        self._cycle_wallpaper(-1)

    def _cycle_wallpaper(self, step: int) -> None:
        from tui_manager.core.environment import Capability
        pack = self._selected_pack()
        if not pack:
            self.notify(t('themes.no_pack'), severity='warning')
            return
        env = self.services.environment
        if not env or not env.supports(Capability.SET_WALLPAPER):
            self.notify(t('themes.wallpaper_unsupported'), severity='warning')
            return
        files = self._wallpapers(pack)
        if not files:
            self.notify(t('themes.no_wallpaper'), severity='warning')
            return
        index = (self._wall_index.get(pack.name, -1) + step) % len(files)
        self._wall_index[pack.name] = index
        self._wallpaper_worker(files[index])

    @work(thread=True, exclusive=False)
    def _wallpaper_worker(self, path: str) -> None:
        try:
            ok = self.services.environment.set_wallpaper(path)
            message = (t('themes.wallpaper_ok', name=os.path.basename(path))
                       if ok else t('themes.wallpaper_failed'))
            self.app.call_from_thread(self.notify, message,
                                      severity='information' if ok else 'error')
        except Exception as exc:
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    # --- claro/oscuro ---

    def action_dark(self) -> None:
        self._set_mode(True)

    def action_light(self) -> None:
        self._set_mode(False)

    def _set_mode(self, dark: bool) -> None:
        from tui_manager.core.environment import Capability
        env = self.services.environment
        if env and env.supports(Capability.SET_DARK_MODE):
            self._mode_worker(dark)
            return
        # Sin soporte del entorno: al menos el tema interno de la TUI.
        name = 'dark' if dark else 'light'
        if name in self.services.theme_manager.THEMES:
            self.app.apply_tui_theme(name)
        self.notify(t('themes.mode_tui_only', mode=name), severity='warning')

    @work(thread=True, exclusive=False)
    def _mode_worker(self, dark: bool) -> None:
        try:
            ok = self.services.environment.set_dark_mode(dark)
            message = (t('themes.dark_ok') if dark else t('themes.light_ok')) \
                if ok else t('themes.mode_failed')
            self.app.call_from_thread(self.notify, message,
                                      severity='information' if ok else 'error')
        except Exception as exc:
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    # --- instalar pack desde URL ---

    def action_install(self) -> None:
        self.app.push_screen(InputScreen(t('themes.install_url')), self._do_install)

    def _do_install(self, url) -> None:
        if not url:
            return
        self._install_worker(url)

    @work(thread=True, exclusive=True)
    def _install_worker(self, url: str) -> None:
        from tui_manager.core.theme_packs import install_pack_from_url
        try:
            pack = install_pack_from_url(url)
            if pack:
                self.app.call_from_thread(self.notify,
                                          t('themes.install_ok', name=pack.name))
                self.app.call_from_thread(self.action_reload)
            else:
                self.app.call_from_thread(self.notify, t('themes.install_fail'),
                                          severity='error')
        except Exception as exc:
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    def action_back(self) -> None:
        self.app.pop_screen()


# ---------------------------------------------------------- Actualizar ----

class UpdatesScreen(Screen):
    """Actualizaciones disponibles, upgrade, caché, huérfanos y firmware."""

    BINDINGS = [
        ('u', 'upgrade', t('packages.upgrade_system')),
        ('c', 'cache', t('packages.update_cache')),
        ('o', 'orphans', t('packages.orphans')),
        ('F', 'firmware', t('updates.firmware')),
        ('r', 'refresh', t('common.refresh')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._updates = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("updates.title")}[/]', classes='title')
        yield DataTable(id='updates-table')
        yield Static(t('updates.checking'), id='updates-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#updates-table', DataTable)
        table.cursor_type = 'row'
        table.add_columns(t('common.name'), t('common.version'),
                          t('common.description'))
        table.focus()
        self.check_updates()

    @work(thread=True, exclusive=True)
    def check_updates(self) -> None:
        try:
            updates = self.services.package_manager.get_updates_available()
        except Exception as exc:
            logger.exception('comprobar actualizaciones falló')
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')
            updates = []
        self.app.call_from_thread(self._fill, updates)

    def _fill(self, updates) -> None:
        self._updates = list(updates)
        table = self.query_one('#updates-table', DataTable)
        table.clear()
        for pkg in self._updates:
            table.add_row(pkg.name, pkg.version, pkg.description or '')
        message = (t('updates.available', n=len(self._updates))
                   if self._updates else t('updates.none'))
        if shutil.which('fwupdmgr'):
            message += f' · [F] {t("updates.firmware")}'
        self.query_one('#updates-status', Static).update(
            f'{message} — {t("updates.keys")}')

    # --- upgrade ---

    def action_upgrade(self) -> None:
        self.app.push_screen(ConfirmScreen(t('updates.upgrade_confirm')),
                             self._do_upgrade)

    def _do_upgrade(self, confirmed) -> None:
        if confirmed:
            self._upgrade_worker()

    @work(thread=True, exclusive=True)
    def _upgrade_worker(self) -> None:
        try:
            ok = self.services.package_manager.upgrade_system()
            message = t('updates.upgraded') if ok else t('packages.action_failed')
            self.app.call_from_thread(self.notify, message,
                                      severity='information' if ok else 'error')
            self.app.call_from_thread(self.check_updates)
        except Exception as exc:
            logger.exception('upgrade falló')
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    # --- caché ---

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

    # --- huérfanos ---

    def action_orphans(self) -> None:
        self._orphans_worker()

    @work(thread=True, exclusive=False)
    def _orphans_worker(self) -> None:
        try:
            orphans = self.services.package_manager.get_orphans()
            self.app.call_from_thread(self._confirm_orphans, orphans)
        except Exception as exc:
            logger.exception('listar huérfanos falló')
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    def _confirm_orphans(self, orphans) -> None:
        if not orphans:
            self.notify(t('updates.no_orphans'))
            return
        names = ', '.join(pkg.name for pkg in orphans[:8])
        if len(orphans) > 8:
            names += ', …'
        self.app.push_screen(
            ConfirmScreen(t('updates.orphans_confirm', n=len(orphans), names=names)),
            self._do_clean_orphans)

    def _do_clean_orphans(self, confirmed) -> None:
        if confirmed:
            self._clean_worker()

    @work(thread=True, exclusive=False)
    def _clean_worker(self) -> None:
        try:
            ok = self.services.package_manager.clean_orphans(confirm=False)
            message = t('updates.orphans_ok') if ok else t('packages.action_failed')
            self.app.call_from_thread(self.notify, message,
                                      severity='information' if ok else 'error')
        except Exception as exc:
            logger.exception('limpiar huérfanos falló')
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    # --- firmware (fwupd, opcional) ---

    def action_firmware(self) -> None:
        if not shutil.which('fwupdmgr'):
            self.notify(t('updates.firmware_absent'), severity='warning')
            return
        self.notify(t('updates.firmware_checking'))
        self._firmware_worker()

    @work(thread=True, exclusive=False)
    def _firmware_worker(self) -> None:
        import subprocess
        try:
            proc = subprocess.run(['fwupdmgr', 'get-updates'],
                                  capture_output=True, text=True, timeout=120)
            output = (proc.stdout or proc.stderr or '').strip()
            self.app.call_from_thread(self.notify, output[:600] or t('updates.none'),
                                      timeout=12)
        except Exception as exc:
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    def action_back(self) -> None:
        self.app.pop_screen()


# -------------------------------------------------------------- Sistema ----

class SystemScreen(Screen):
    """Menú Sistema: acciones con degradación elegante por disponibilidad.

    Cada entrada se deshabilita con el motivo (herramienta/capacidad que
    falta) según `SystemControl.availability()` + capacidades del entorno.
    """

    BINDINGS = [('escape', 'back', t('common.back'))]

    # id → clave de disponibilidad (None: acción siempre disponible)
    ORDER = (
        ('launch', 'launch'),
        ('lock', 'lock'),
        ('logout', 'logout'),
        ('reboot', 'reboot'),
        ('shutdown', 'shutdown'),
        ('suspend', 'suspend'),
        ('brightness_up', 'brightness'),
        ('brightness_down', 'brightness'),
        ('power_profiles', 'power_profiles'),
        ('timezone', 'timezone'),
    )

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("system.title")}[/] — {type(self.services.environment).__name__}',
                    classes='title')
        yield ListView(id='system-menu')
        yield Static(t('system.keys'), id='system-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        menu = self.query_one('#system-menu', ListView)
        menu.clear()
        self._available = self.services.system_control.availability()
        first_enabled = None
        for index, (action_id, avail_key) in enumerate(self.ORDER):
            label = t(f'system.{action_id}')
            reason = self._available.get(avail_key)
            if reason:
                text = f'[dim]{label} ({t("system.not_supported")}: {reason})[/]'
                menu.append(ListItem(Static(text), id=action_id,
                                     classes='disabled'))
            else:
                menu.append(ListItem(Static(label), id=action_id))
                if first_enabled is None:
                    first_enabled = index
        if first_enabled is not None:
            menu.index = first_enabled
        menu.focus()

    @on(ListView.Selected)
    def run_action(self, event: ListView.Selected) -> None:
        action = event.item.id
        if event.item.has_class('disabled'):
            return
        if action == 'launch':
            self.app.push_screen(InputScreen(t('system.launch_prompt')),
                                 self._do_launch)
        elif action == 'reboot':
            self.app.push_screen(ConfirmScreen(t('system.reboot_confirm')),
                                 lambda ok: self._run_action('reboot') if ok else None)
        elif action == 'shutdown':
            self.app.push_screen(ConfirmScreen(t('system.shutdown_confirm')),
                                 lambda ok: self._run_action('shutdown') if ok else None)
        else:
            self._run_action(action)

    def _do_launch(self, command) -> None:
        if not command or not command.strip():
            return
        self._launch_worker(command.strip())

    @work(thread=True, exclusive=False)
    def _launch_worker(self, command: str) -> None:
        from tui_manager.core.environment import launch_or_focus
        try:
            result = launch_or_focus(self.services.environment, command)
            key = {'launched': 'system.done', 'focused': 'system.done',
                   'failed': 'system.failed'}[result['action']]
            self.app.call_from_thread(self.notify, t(key),
                                      severity='information' if
                                      result['action'] != 'failed' else 'error')
        except Exception as exc:
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    @work(thread=True, exclusive=False)
    def _run_action(self, action: str, value=None) -> None:
        sc = self.services.system_control
        try:
            if action == 'lock':
                ok, message = sc.lock()
            elif action == 'logout':
                ok, message = sc.logout()
            elif action == 'reboot':
                ok, message = sc.reboot()
            elif action == 'shutdown':
                ok, message = sc.shutdown()
            elif action == 'suspend':
                ok, message = sc.suspend()
            elif action == 'brightness_up':
                ok, message = sc.brightness_step(1)
            elif action == 'brightness_down':
                ok, message = sc.brightness_step(-1)
            elif action == 'power_profiles':
                ok, message = sc.power_profiles()
            elif action == 'timezone':
                ok, message = sc.set_timezone(value)
            else:
                ok, message = False, action
            severity = 'information' if ok else 'error'
            if not ok and not message:
                message = t('system.failed')
            self.app.call_from_thread(self.notify, message or t('system.done'),
                                      severity=severity)
        except Exception as exc:
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')

    def action_back(self) -> None:
        self.app.pop_screen()


# ------------------------------------------------------------ Acerca de ----

class AboutScreen(Screen):
    """B · Info detallada del sistema: software y hardware."""

    BINDINGS = [('escape', 'back', t('common.back'))]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("about.title")}[/]', classes='title')
        with VerticalScroll():
            yield LoadingIndicator(id='about-loading')
            yield Static(t('common.loading'), id='about-text', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#about-loading', LoadingIndicator).display = True
        self.query_one('#about-text', Static).update('')
        self._collect()

    @work(thread=True, exclusive=True)
    def _collect(self) -> None:
        from tui_manager.core.sysinfo import collect
        info = collect(
            distribution=self.services.distribution,
            environment=self.services.environment,
            system_control=self.services.system_control,
            package_manager=self.services.package_manager,
        )
        self.app.call_from_thread(self._fill, info)

    @staticmethod
    def _line(label: str, value) -> str:
        v = value if value not in (None, '', 0) else t('about.na')
        return f'{label}: {v}'

    def _fill(self, info: dict) -> None:
        na = t('about.na')
        battery = info.get('battery')
        battery_text = (f"{battery.get('percent')}% ({battery.get('status')})"
                        if battery else na)
        packages = info.get('packages')
        pkg_text = packages if packages is not None else na

        sep = '═' * 24
        lines = [
            f'{sep} {t("about.section.software")} {sep}',
            self._line(t('about.os'), info.get('os')),
            self._line(t('about.kernel'), info.get('kernel')),
            self._line(t('about.distro'), info.get('distro')),
            self._line(t('about.environment'), info.get('environment')),
            self._line(t('about.platform'), info.get('platform')),
            self._line(t('about.arch'), info.get('arch')),
            self._line(t('about.hostname'), info.get('hostname')),
            self._line(t('about.user'), info.get('user')),
            self._line(t('about.python'), info.get('python')),
            self._line(t('about.uptime'), info.get('uptime')),
            self._line(t('about.shell'), info.get('shell')),
            self._line(t('about.term'), info.get('term')),
            self._line(t('about.packages'), pkg_text),
            '',
            f'{sep} {t("about.section.hardware")} {sep}',
            self._line(t('about.cpu_model'), info.get('cpu_model')),
            self._line(t('about.cpu_logical'), info.get('cpu_logical')),
            self._line(t('about.cpu_physical'), info.get('cpu_physical')),
            self._line(t('about.ram'), info.get('ram')),
            self._line(t('about.ram_detail'), info.get('ram_detail')),
            self._line(t('about.ram_available'), info.get('ram_available')),
            self._line(t('about.swap'), info.get('swap')),
            self._line(t('about.disk'), info.get('disk')),
            self._line(t('about.disk_total'), info.get('disk_total')),
            self._line(t('about.disk_used'), info.get('disk_used')),
            self._line(t('about.disk_free'), info.get('disk_free')),
            self._line(t('about.battery'), battery_text),
        ]

        self.query_one('#about-text', Static).update('\n'.join(lines))
        self.query_one('#about-loading', LoadingIndicator).display = False

    def action_back(self) -> None:
        self.app.pop_screen()

# ----------------------------------------------------------------- Logs ----

class LogsScreen(Screen):
    """E · Visor de logs: cola del log de la app con refresco manual."""

    BINDINGS = [('r', 'refresh', t('common.refresh')),
                ('escape', 'back', t('common.back'))]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("logs.title")}[/]', classes='title')
        with VerticalScroll():
            yield Static('…', id='log-text', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._interval = self.set_interval(2.0, self.action_refresh)
        self.action_refresh()

    @work(thread=True, exclusive=True)
    def action_refresh(self) -> None:
        from pathlib import Path
        path = Path.home() / '.tui-manager' / 'logs' / 'app.log'
        try:
            with open(path, 'r', errors='replace') as f:
                lines = f.readlines()[-200:]
            text = ''.join(lines) or t('logs.empty')
        except FileNotFoundError:
            text = t('logs.empty')
        except OSError as exc:
            text = f'{t("common.error")}: {exc}'
        self.app.call_from_thread(self._fill, text)

    def _fill(self, text: str) -> None:
        self.query_one('#log-text', Static).update(text)

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
        with Vertical(classes='dialog'):
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
        with Vertical(classes='dialog'):
            yield Label(self.prompt)
            yield Input(value=self.value, id='modal-input')
            yield Footer()

    def on_mount(self) -> None:
        self.query_one('#modal-input', Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


# -------------------------------------------------------- Catálogo / fuentes ----

class SelectScreen(ModalScreen):
    """Modal de selección; dismiss(índice) o dismiss(None) si cancela."""

    BINDINGS = [('escape', 'cancel', t('common.cancel'))]

    def __init__(self, title: str, options: list, hints: list = None):
        super().__init__()
        self.title = title
        self.options = list(options)
        self.hints = list(hints or [])

    def compose(self) -> ComposeResult:
        with Vertical(classes='dialog'):
            yield Label(self.title)
            yield ListView(id='source-options')
            yield Footer()

    def on_mount(self) -> None:
        view = self.query_one('#source-options', ListView)
        for i, opt in enumerate(self.options):
            hint = self.hints[i] if i < len(self.hints) else ''
            label = opt if not hint else f'{opt}  [{hint}]'
            view.append(ListItem(Static(label), id=str(i)))
        if self.options:
            view.index = 0
        view.focus()

    @on(ListView.Selected)
    def selected(self, event: ListView.Selected) -> None:
        if event.item.id is not None:
            self.dismiss(int(event.item.id))

    def action_cancel(self) -> None:
        self.dismiss(None)


class AppsScreen(Screen):
    """Catálogo de apps recomendadas con instalación desde fuentes alternativas."""

    BINDINGS = [
        ('enter', 'install', t('common.install')),
        ('c', 'category', t('apps.category')),
        ('f', 'filter', t('common.search')),
        Binding('/', 'filter', show=False),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.adapter = SourcesAdapter(services.config)
        self._apps = []
        self._category = 'all'
        self._query = ''

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{t("apps.title")}[/]', classes='title')
        yield Input(placeholder=t('common.search'), id='apps-search')
        yield Select(
            [(name, key) for key, name in self.adapter.categories().items()],
            value='all', id='apps-category', prompt=t('apps.category'),
        )
        yield LoadingIndicator(id='apps-loading')
        yield DataTable(id='apps-table')
        yield Static(t('apps.category'), id='apps-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#apps-table', DataTable)
        table.cursor_type = 'row'
        table.add_columns(t('common.name'), t('apps.category'),
                          t('apps.sources'), t('common.description'))
        table.focus()
        self.query_one('#apps-loading', LoadingIndicator).display = True
        self._reload()

    def _reload(self) -> None:
        self._apps = self.adapter.list_apps(self._category, self._query)
        table = self.query_one('#apps-table', DataTable)
        table.clear()
        for app in self._apps:
            table.add_row(app.name, app.category,
                          self.adapter.source_summary(app), app.description)
        self.query_one('#apps-status', Static).update(
            f'{len(self._apps)} apps — {t("apps.category")}: {self._category}'
        )
        try:
            self.query_one('#apps-loading', LoadingIndicator).display = False
        except Exception:
            pass

    @on(Input.Submitted, '#apps-search')
    def search_submitted(self, event: Input.Submitted) -> None:
        self._query = event.value.strip()
        self._reload()
        self.query_one('#apps-table', DataTable).focus()

    @on(Select.Changed, '#apps-category')
    def category_changed(self, event: Select.Changed) -> None:
        if event.value is not Select.BLANK:
            self._category = event.value
            self._reload()

    def action_filter(self) -> None:
        search = self.query_one('#apps-search', Input)
        search.focus()
        search.cursor_position = len(search.value)

    def action_category(self) -> None:
        self.query_one('#apps-category', Select).focus()

    def action_back(self) -> None:
        self.app.pop_screen()

    def _selected_app(self):
        table = self.query_one('#apps-table', DataTable)
        if 0 <= table.cursor_row < len(self._apps):
            return self._apps[table.cursor_row]
        return None

    def action_install(self) -> None:
        app = self._selected_app()
        if not app:
            return
        sources = self.adapter.sources_for(app)
        if not sources:
            self.notify(t('apps.no_sources'), severity='warning')
            return

        if len(sources) == 1 and self.adapter.is_official(sources[0]):
            self._confirm_and_install(app, sources[0])
        else:
            options = [self.adapter.describe_source(s) for s in sources]
            hints = [t('apps.preferred') if s.type == self.adapter.preferred_format()
                     else '' for s in sources]
            self.app.push_screen(
                SelectScreen(t('apps.source_choose'), options, hints),
                lambda idx: self._source_chosen(app, sources, idx),
            )

    def _source_chosen(self, app, sources, idx) -> None:
        if idx is None:
            return
        source = sources[idx]
        if self.adapter.is_official(source):
            self._confirm_and_install(app, source)
        else:
            self.app.push_screen(
                ConfirmScreen(
                    f'{t("apps.source_warning")}\n{app.name} → '
                    f'{self.adapter.describe_source(source)}\n'
                    f'{t("apps.source_confirm")}'
                ),
                lambda ok: self._do_install(app, source) if ok else None,
            )

    def _confirm_and_install(self, app, source) -> None:
        self.app.push_screen(
            ConfirmScreen(f'{t("packages.install_confirm")} {app.name}?'),
            lambda ok: self._do_install(app, source) if ok else None,
        )

    @work(thread=True, exclusive=False)
    def _do_install(self, app, source) -> None:
        self.app.call_from_thread(
            lambda: setattr(self.query_one('#apps-loading', LoadingIndicator),
                            'display', True))
        try:
            result = self.adapter.install(app, source)
            if result.ok:
                msg = t('apps.install_ok', name=app.name, source=source.type)
            else:
                msg = f'{t("packages.action_failed")}: {result.error or "—"}'
            self.app.call_from_thread(self.notify, msg,
                                      severity='information' if result.ok else 'error')
            self.app.call_from_thread(self._reload)
        except Exception as exc:
            logger.exception('instalación desde fuente falló')
            self.app.call_from_thread(
                self.notify, f'{t("common.error")}: {exc}', severity='error')

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
