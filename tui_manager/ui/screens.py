"""
Pantallas de TUI Manager (Alfa 3).

- MainMenuScreen: menú principal con atajos 1–9 y todas las entradas activas.
- PackagesScreen: DataTable de paquetes, instalar/remover/info/caché/buscar.
- ProcessesScreen: monitor con refresco por intervalo, kill/renice/pausa/orden.
- ThemesScreen: packs de tema, wallpaper, claro/oscuro, instalar desde URL.
- UpdatesScreen: actualizaciones, upgrade, caché, huérfanos, firmware.
- SettingsScreen: tema interno, idioma, intervalo de refresco.
- HelpScreen: atajos contextuales y sugerencia de --doctor; `?` abre la
  ayuda correspondiente a la pantalla activa (B2-2).
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
from tui_manager.core.distribution import DistributionDetector
from tui_manager.core.sources_adapter import SourcesAdapter

logger = logging.getLogger(__name__)


# --------------------------------------------------------------- Iconos ----

# Iconos Unicode del menú. Cuando TERM=dumb (o la terminal no garantiza la
# fuente) se degradan a letras ASCII: siguen siendo legibles y no rompen el
# ancho de las filas ni los atajos numéricos que las prefijan.
_MENU_ICONS = {
    'packages': ('▤', 'P'),
    'processes': ('⚙', 'S'),
    'system': ('▣', 'Y'),
    'themes': ('◐', 'T'),
    'updates': ('⇧', 'U'),
    'settings': ('⚒', 'G'),
    'help': ('?', '?'),
    'about': ('ⓘ', 'I'),
    'logs': ('☰', 'L'),
    'apps': ('◈', 'C'),
}
_TITLE_ICON = ('◆', '*')
_SCREEN_ICON_KEYS = {
    'MainMenuScreen': '',
    'PackagesScreen': 'packages',
    'ProcessesScreen': 'processes',
    'SystemScreen': 'system',
    'ThemesScreen': 'themes',
    'UpdatesScreen': 'updates',
    'SettingsScreen': 'settings',
    'HelpScreen': 'help',
    'AboutScreen': 'about',
    'LogsScreen': 'logs',
    'AppsScreen': 'apps',
}


def _ascii_only() -> bool:
    """Terminal sin garantías de fuente: solo ASCII seguro."""
    return os.environ.get('TERM', '').lower() == 'dumb'


def menu_icon(entry_id: str) -> str:
    """Icono de una entrada del menú, con fallback ASCII para TERM=dumb."""
    glyph, ascii_glyph = _MENU_ICONS.get(entry_id, ('·', '-'))
    return ascii_glyph if _ascii_only() else glyph


def title_icon() -> str:
    """Icono del título; en TERM=dumb se usa un marcador ASCII."""
    glyph, ascii_glyph = _TITLE_ICON
    return ascii_glyph if _ascii_only() else glyph


def screen_icon(screen_name: str) -> str:
    """Icono acorde a la pantalla activa (o el genérico si no hay entrada)."""
    key = _SCREEN_ICON_KEYS.get(screen_name)
    if key is None:
        return title_icon()
    return menu_icon(key) if key else title_icon()


def _status(message: str, keys: str = '', empty: bool = False) -> str:
    """Compone el texto del widget de status con jerarquía uniforme.

    Todas las tablas/listas usan un ``Static`` con la clase CSS ``status``.
    Cuando no hay datos se añade la clave i18n existente ``common.empty``
    para que la lista vacía nunca quede muda (B1-2).
    """
    if empty:
        empty_text = t('common.empty')
        message = f'{message} · {empty_text}' if message else empty_text
    return f'{message} — {keys}' if keys else message


def _open_context_help(screen: Screen) -> None:
    """Abre ``HelpScreen`` con el contexto de la pantalla que pulsó «?».

    Compartido por las 10 pantallas del menú (y por el propio HelpScreen)
    para que la ayuda mostrada siempre corresponda a la pantalla activa.
    """
    screen.app.push_screen(
        HelpScreen(screen.services, context=type(screen).__name__))


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
        ('?', 'help', t('common.help')),
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
        yield Label(f'[b]{title_icon()} {t("app.title")}[/] — {t("menu.title")}',
                    classes='title')
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
                Static(f'[{key}] {menu_icon(entry_id)} {label} — {desc}',
                       markup=False), id=entry_id))
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

    def action_help(self) -> None:
        """?: ayuda contextual del menú principal."""
        _open_context_help(self)

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


def quickstart_text() -> str:
    """Texto del recorrido guiado por el menú para la CLI (``--quickstart``).

    Reutiliza ``MainMenuScreen.ENTRIES`` y ``MainMenuScreen.shortcut`` como
    única fuente de verdad: si cambian las entradas o los atajos del menú,
    este recorrido se actualiza solo. Usa las claves i18n ``menu.*`` ya
    existentes para nombre y descripción. No inicia la TUI ni ejecuta
    subprocesos: solo compone texto plano.
    """
    lines = [
        f'{t("app.title")} — {t("quickstart.title")}',
        '',
        t('quickstart.intro'),
        '',
    ]
    for index, (entry_id, _screen) in enumerate(MainMenuScreen.ENTRIES):
        key = MainMenuScreen.shortcut(index)
        name = t(f'menu.{entry_id}')
        desc = t(f'menu.{entry_id}.desc')
        lines.append(f'  [{key}] {name} — {desc}')
    lines.append('')
    lines.append(t('quickstart.doctor_hint'))
    return '\n'.join(lines)


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
        ('space', 'toggle_mark', t('packages.toggle_mark')),
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._packages = []
        # 1.1-C: índices (en `_packages`) de las filas marcadas con Espacio.
        self._marked: set[int] = set()
        self._origin = t('packages.installed_list')
        self._pending: list = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{screen_icon("PackagesScreen")} {t("packages.title")}[/] '
                    f'({self.services.distribution})', classes='title')
        yield Input(placeholder=t('common.search'), id='search')
        yield LoadingIndicator(id='packages-loading')
        yield DataTable(id='packages-table')
        yield Static(t('packages.keys'), id='packages-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#packages-table', DataTable)
        table.cursor_type = 'row'
        table.add_columns(t('common.selected'), t('common.name'),
                          t('common.version'), t('common.installed'),
                          t('common.description'))
        table.focus()
        self.query_one('#packages-loading', LoadingIndicator).display = True
        self.load_installed()

    def _fetch_installed(self) -> None:
        """Obtiene los paquetes y vuelca la tabla en el hilo de la UI.

        Se llama desde un worker (carga inicial o acción de instalar/remover)
        para no crear workers anidados al recargar tras una acción.
        """
        packages = self.services.package_manager.get_installed_packages()
        self.app.call_from_thread(self._fill, packages, t('packages.installed_list'))

    @work(thread=True, exclusive=True)
    def load_installed(self) -> None:
        self._fetch_installed()

    @work(thread=True, exclusive=True)
    def load_search(self, query: str) -> None:
        self.query_one('#packages-loading', LoadingIndicator).display = True
        packages = self.services.package_manager.search_package(query)
        self.app.call_from_thread(self._fill, packages, t('packages.search_results'))

    def _fill(self, packages, origin: str, *, keep_marks: bool = False) -> None:
        """Vuelca la tabla. `keep_marks` se usa solo al marcar/desmarcar.

        Una recarga normal (búsqueda o tras instalar/remover) descarta las
        marcas: los índices ya no apuntarían a los mismos paquetes.
        """
        self._packages = list(packages)
        self._origin = origin
        if not keep_marks:
            self._marked.clear()
        table = self.query_one('#packages-table', DataTable)
        table.clear()
        for index, pkg in enumerate(self._packages):
            table.add_row('✓' if index in self._marked else '',
                          pkg.name, pkg.version,
                          '✓' if pkg.installed else '',
                          pkg.description or '')
        try:
            self.query_one('#packages-loading', LoadingIndicator).display = False
        except Exception:
            pass
        self.query_one('#packages-status', Static).update(_status(
            f'{origin}: {len(self._packages)}', t('packages.keys'),
            empty=not self._packages))

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

    def _selected_packages(self) -> list:
        """Marcadas (si las hay) o, en su defecto, la fila del cursor.

        Sin marcas el flujo de una sola fila queda exactamente como estaba.
        """
        if self._marked:
            return [self._packages[index] for index in sorted(self._marked)
                    if 0 <= index < len(self._packages)]
        pkg = self._selected_package()
        return [pkg] if pkg is not None else []

    def action_toggle_mark(self) -> None:
        """Espacio: marca/desmarca la fila actual conservando el cursor."""
        table = self.query_one('#packages-table', DataTable)
        index = table.cursor_row
        if not (0 <= index < len(self._packages)):
            return
        if index in self._marked:
            self._marked.discard(index)
        else:
            self._marked.add(index)
        self._fill(self._packages, self._origin, keep_marks=True)
        self.query_one('#packages-table', DataTable).move_cursor(row=index)

    def _take_pending(self, confirmed) -> list:
        """Devuelve el lote confirmado; cancelar no ejecuta ni deja pendiente."""
        if not confirmed:
            self._pending = []
            return []
        pkgs = self._pending or self._selected_packages()
        self._pending = []
        return pkgs

    def action_install(self) -> None:
        pkgs = self._selected_packages()
        if not pkgs:
            return
        self._pending = pkgs
        message = (t('packages.install_many_confirm', n=len(pkgs))
                   if len(pkgs) > 1
                   else f'{t("packages.install_confirm")} {pkgs[0].name}?')
        self.app.push_screen(ConfirmScreen(message), self._do_install)

    def _do_install(self, confirmed) -> None:
        pkgs = self._take_pending(confirmed)
        if pkgs:
            self._run_action(pkgs, 'install')

    def action_remove(self) -> None:
        pkgs = self._selected_packages()
        if not pkgs:
            return
        self._pending = pkgs
        message = (t('packages.remove_many_confirm', n=len(pkgs))
                   if len(pkgs) > 1
                   else f'{t("packages.remove_confirm")} {pkgs[0].name}?')
        self.app.push_screen(ConfirmScreen(message), self._do_remove)

    def _do_remove(self, confirmed) -> None:
        pkgs = self._take_pending(confirmed)
        if pkgs:
            self._run_action(pkgs, 'remove')

    @work(thread=True, exclusive=False)
    def _run_action(self, packages, action: str) -> None:
        """Instala/remueve todo el lote y recarga la tabla una sola vez."""
        pkgs = (list(packages) if isinstance(packages, (list, tuple))
                else [packages])
        self.app.call_from_thread(
            lambda: setattr(self.query_one('#packages-loading', LoadingIndicator),
                            'display', True))
        ok_all = True
        try:
            for pkg in pkgs:
                if action == 'install':
                    ok = self.services.package_manager.install_package(
                        pkg.name, confirm=False)
                else:
                    ok = self.services.package_manager.remove_package(
                        pkg.name, confirm=False)
                ok_all = ok_all and bool(ok)
            if len(pkgs) == 1:
                key = ('packages.install_ok' if action == 'install'
                       else 'packages.remove_ok')
                message = (t(key, name=pkgs[0].name) if ok_all
                           else t('packages.action_failed'))
            else:
                key = ('packages.install_many_ok' if action == 'install'
                       else 'packages.remove_many_ok')
                message = (t(key, n=len(pkgs)) if ok_all
                           else t('packages.action_failed'))
            self.app.call_from_thread(self.notify, message,
                                      severity='information' if ok_all else 'error')
        except Exception as exc:
            logger.exception('acción de paquete falló')
            self.app.call_from_thread(self.notify, f'{t("common.error")}: {exc}',
                                      severity='error')
        finally:
            # Un solo aviso y una sola recarga para todo el lote: las marcas
            # ya no aplican después de la acción.
            self.app.call_from_thread(self._marked.clear)
            self._fetch_installed()

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

    def action_help(self) -> None:
        """?: ayuda contextual de aplicaciones."""
        _open_context_help(self)

    def action_back(self) -> None:
        """Esc: si el buscador tiene el foco, vuelve a la tabla; si no, atrás."""
        if isinstance(self.focused, Input):
            self.query_one('#packages-table', DataTable).focus()
            return
        self.app.pop_screen()


# ------------------------------------------------------------ Procesos ----

class ProcessesScreen(Screen):
    """Monitor de procesos con refresco por intervalo configurable."""

    # 1.1-D: 's' cicla en este orden. cpu/mem siguen siendo los dos primeros
    # para no cambiar el comportamiento ya conocido de la versión 1.0.
    SORT_CRITERIA = ('cpu', 'mem', 'user', 'name', 'pid')
    SORT_KEYS = {
        # El PID desempata para que el orden sea estable entre ciclos de 's'.
        'cpu': lambda p: (p.cpu, p.pid),
        'mem': lambda p: (p.mem, p.pid),
        'user': lambda p: (p.user, p.pid),
        'name': lambda p: (p.command, p.pid),
        'pid': lambda p: p.pid,
    }
    SORT_ASCENDING = frozenset({'user', 'name'})

    BINDINGS = [
        ('k', 'kill', t('processes.kill')),
        ('K', 'kill9', t('processes.kill9')),
        ('n', 'renice', t('processes.renice')),
        ('p', 'pause', t('processes.paused')),
        ('s', 'sort', t('processes.sort')),
        ('f', 'filter', t('common.filter')),
        Binding('/', 'filter', show=False),
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._processes = []
        self._raw_processes = []   # fuente sin ordenar, para recalcular 's'
        self._paused = False
        self._filter = ''
        self._sort = 'cpu'

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{screen_icon("ProcessesScreen")} {t("processes.title")}[/]',
                    classes='title')
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
        # B3-2: el intervalo se lee de la configuración (validada por
        # Config.set_refresh_interval, mínimo 1 s) y se guarda para poder
        # inspeccionarlo/verificarlo en tests sin esperar tiempo real.
        self._poll_interval = max(
            1, int(self.services.config.get_refresh_interval()))
        self._interval = self.set_interval(
            self._poll_interval, self._tick, name='processes-poll')
        self._tick()

    def _tick(self) -> None:
        """Sondeo periódico: solo programa el worker si no está pausado."""
        if not self._paused:
            self.refresh_table()

    @work(thread=True, exclusive=True)
    def refresh_table(self) -> None:
        filters = {'name': self._filter} if self._filter else None
        processes = self.services.process_monitor.get_processes(filters)
        self.app.call_from_thread(self._fill, processes)

    def _fill(self, processes) -> None:
        # Un worker puede terminar justo cuando la pantalla se desmonta:
        # descartar el resultado en vez de fallar con NoMatches.
        if not self.is_mounted:
            return
        self._raw_processes = list(processes)
        criterion = (self._sort if self._sort in self.SORT_CRITERIA else 'cpu')
        ordered = sorted(
            processes,
            key=self.SORT_KEYS[criterion],
            reverse=criterion not in self.SORT_ASCENDING,
        )
        self._processes = list(ordered)
        table = self.query_one('#process-table', DataTable)
        table.clear()
        for proc in ordered:
            table.add_row(str(proc.pid), proc.user, f'{proc.cpu:.1f}',
                          f'{proc.mem:.1f}', str(proc.nice), proc.time,
                          proc.command[:60])
        sort_label = t(f'processes.sort_{self._sort}')
        self.query_one('#process-status', Static).update(_status(
            f'{len(self._processes)} · {sort_label}', t('processes.keys'),
            empty=not self._processes))

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
        """s: cicla cpu → mem → user → name → pid → cpu."""
        criterion = (self._sort if self._sort in self.SORT_CRITERIA else 'cpu')
        index = self.SORT_CRITERIA.index(criterion)
        self._sort = self.SORT_CRITERIA[(index + 1) % len(self.SORT_CRITERIA)]
        self._fill(self._raw_processes)

    def pause_polling(self) -> None:
        """Pausa el sondeo: se detiene el timer y `_tick` no hace nada."""
        if self._paused:
            return
        self._paused = True
        self._interval.pause()
        self.notify(t('processes.paused'))

    def resume_polling(self) -> None:
        """Reanuda el sondeo del timer y refresca la tabla de inmediato."""
        if not self._paused:
            return
        self._paused = False
        # `reset` reactiva el timer y reinicia su cuenta: evita un tick de
        # "atrapo" inmediato con el tiempo transcurrido durante la pausa.
        self._interval.reset()
        self.notify(t('common.refresh_done'))
        self._tick()

    def action_pause(self) -> None:
        """p: alterna pausa / reanudación del sondeo de procesos."""
        if self._paused:
            self.resume_polling()
        else:
            self.pause_polling()

    def _selected_process(self):
        table = self.query_one('#process-table', DataTable)
        if 0 <= table.cursor_row < len(self._processes):
            return self._processes[table.cursor_row]
        return None

    def _send_signal(self, confirmed, signal: int) -> None:
        """Callback del modal: solo valida y delega el I/O a un worker."""
        if not confirmed:
            return
        proc = self._selected_process()
        if not proc:
            return
        self._signal_worker(proc.pid, signal)

    @work(thread=True, exclusive=False)
    def _signal_worker(self, pid: int, signal: int) -> None:
        """Envía la señal en segundo plano (`kill_process` usa subprocess)."""
        try:
            ok = self.services.process_monitor.kill_process(pid, signal=signal)
            self.app.call_from_thread(
                self.notify,
                t('processes.kill_ok', pid=pid) if ok
                else t('processes.kill_failed', pid=pid),
                severity='information' if ok else 'error')
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f'{t("common.error")}: {exc}', severity='error')
        self.app.call_from_thread(self.refresh_table)

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
        """Callback del modal: valida en la UI y delega el I/O al worker."""
        if value is None:
            return
        proc = self._selected_process()
        if not proc:
            return
        try:
            nice = int(value)
        except (TypeError, ValueError):
            self.notify(f'{t("common.error")}: {value}', severity='error')
            return
        self._renice_worker(proc.pid, nice)

    @work(thread=True, exclusive=False)
    def _renice_worker(self, pid: int, nice: int) -> None:
        """Cambia el nice en segundo plano (`renice_process` usa subprocess)."""
        try:
            ok = self.services.process_monitor.renice_process(pid, nice)
            self.app.call_from_thread(
                self.notify,
                t('processes.kill_ok', pid=pid) if ok
                else t('processes.kill_failed', pid=pid),
                severity='information' if ok else 'error')
        except Exception as exc:
            self.app.call_from_thread(
                self.notify, f'{t("common.error")}: {exc}', severity='error')
        self.app.call_from_thread(self.refresh_table)

    def action_help(self) -> None:
        """?: ayuda contextual de procesos."""
        _open_context_help(self)

    def action_back(self) -> None:
        if isinstance(self.focused, Input):
            self.query_one('#process-table', DataTable).focus()
            return
        self.app.pop_screen()


# -------------------------------------------------------------- Ajustes ----

class SettingsScreen(Screen):
    """Ajustes: tema interno, idioma, intervalo de refresco."""

    BINDINGS = [
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    @staticmethod
    def _note_text() -> str:
        """Nota de Ajustes: específica de Termux solo cuando procede."""
        if DistributionDetector.is_termux():
            return t('settings.termux_note')
        return t('settings.generic_note')

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{screen_icon("SettingsScreen")} {t("settings.title")}[/]',
                    classes='title')
        yield VerticalScroll(
            Label(f'[b]{t("settings.tui_theme")}[/]'),
            Static(t('settings.theme_help'), classes='hint', markup=False),
            Select(
                [(name, name) for name in self.services.theme_manager.THEMES],
                value=self.services.config.get('theme', 'dark'),
                id='select-theme',
                prompt=t('settings.tui_theme'),
                allow_blank=False,
                classes='select-compact',
            ),
            Label(f'[b]{t("settings.theme_source")}[/]'),
            Static(t('settings.theme_source_help'), classes='hint', markup=False),
            Select(
                [('Manual', 'manual'), ('Matugen (dinámico)', 'mutagen')],
                value=self.services.config.get_theme_source(),
                id='select-theme-source',
                prompt=t('settings.theme_source'),
                allow_blank=False,
                classes='select-compact',
            ),
            Label(f'[b]{t("common.language")}[/]'),
            Static(t('settings.language_help'), classes='hint', markup=False),
            Select(
                [('Español', 'es'), ('English', 'en')],
                value=self.services.config.get('language', 'es'),
                id='select-language',
                prompt=t('common.language'),
                allow_blank=False,
                classes='select-compact',
            ),
            Label(f'[b]{t("settings.refresh_interval")}[/]'),
            Static(t('settings.interval_help'), classes='hint', markup=False),
            Input(value=str(self.services.config.get('refresh_interval', 2)),
                  id='input-interval', placeholder=t('settings.refresh_interval')),
            # 1.1-B: el aviso de Termux solo aparece en Termux/Android; en
            # el resto de sistemas se muestra una nota neutra y legible.
            Static(self._note_text(), id='settings-note', classes='status',
                   markup=False),
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

    @on(Select.Changed, '#select-theme-source')
    def theme_source_changed(self, event: Select.Changed) -> None:
        self.services.config.set_theme_source(str(event.value))
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

    def action_help(self) -> None:
        """?: ayuda contextual de ajustes."""
        _open_context_help(self)

    def action_back(self) -> None:
        self.app.pop_screen()


# ---------------------------------------------------------------- Ayuda ----

class HelpScreen(Screen):
    """Atajos de teclado (contextuales) y diagnóstico."""

    BINDINGS = [
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

    # pantalla → claves i18n con sus atajos propios. B2-2: las 10 pantallas
    # del menú tienen contexto; cuando no existe clave propia se reutiliza
    # `common.help` (i18n.py no se amplía en este paso).
    CONTEXT_KEYS = {
        'MainMenuScreen': ('menu.keys',),
        'PackagesScreen': ('packages.keys',),
        'ProcessesScreen': ('processes.keys',),
        'ThemesScreen': ('themes.keys',),
        'UpdatesScreen': ('updates.keys',),
        'SystemScreen': ('system.keys',),
        'SettingsScreen': ('common.help',),
        'AboutScreen': ('common.help',),
        'LogsScreen': ('common.help',),
        'AppsScreen': ('common.help',),
        'HelpScreen': ('common.help',),
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
        yield Label(f'[b]{screen_icon("HelpScreen")} {t("help.title")}[/]',
                    classes='title')
        with VerticalScroll():
            yield Static('\n'.join(lines), id='help-text', markup=False)
        yield Footer()

    def action_help(self) -> None:
        """?: ayuda contextual de la propia pantalla de ayuda."""
        _open_context_help(self)

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
        ('?', 'help', t('common.help')),
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
        yield Label(f'[b]{screen_icon("ThemesScreen")} {t("themes.title")}[/]',
                    classes='title')
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
        self.query_one('#themes-status', Static).update(_status(
            f'{t("themes.packs")}: {len(self._packs)}', t('themes.keys'),
            empty=not self._packs))

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

    def action_help(self) -> None:
        """?: ayuda contextual de temas."""
        _open_context_help(self)

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
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self._updates = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{screen_icon("UpdatesScreen")} {t("updates.title")}[/]',
                    classes='title')
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
            _status(message, t('updates.keys'), empty=not self._updates))

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

    def action_help(self) -> None:
        """?: ayuda contextual de actualizaciones."""
        _open_context_help(self)

    def action_back(self) -> None:
        self.app.pop_screen()


# -------------------------------------------------------------- Sistema ----

class SystemScreen(Screen):
    """Menú Sistema: acciones con degradación elegante por disponibilidad.

    Cada entrada se deshabilita con el motivo (herramienta/capacidad que
    falta) según `SystemControl.availability()` + capacidades del entorno.
    """

    BINDINGS = [
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

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
        yield Label(f'[b]{screen_icon("SystemScreen")} {t("system.title")}[/] — '
                    f'{type(self.services.environment).__name__}', classes='title')
        yield ListView(id='system-menu')
        yield Static(t('system.keys'), id='system-status', classes='status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        menu = self.query_one('#system-menu', ListView)
        menu.clear()
        self._available = self.services.system_control.availability()
        first_enabled = None
        enabled = 0
        for index, (action_id, avail_key) in enumerate(self.ORDER):
            label = t(f'system.{action_id}')
            reason = self._available.get(avail_key)
            if reason:
                text = f'[dim]{label} ({t("system.not_supported")}: {reason})[/]'
                menu.append(ListItem(Static(text), id=action_id,
                                     classes='disabled'))
            else:
                menu.append(ListItem(Static(label), id=action_id))
                enabled += 1
                if first_enabled is None:
                    first_enabled = index
        if first_enabled is not None:
            menu.index = first_enabled
        menu.focus()
        self.query_one('#system-status', Static).update(_status(
            f'{t("common.actions")}: {enabled}', t('system.keys'),
            empty=enabled == 0))

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

    def action_help(self) -> None:
        """?: ayuda contextual de sistema."""
        _open_context_help(self)

    def action_back(self) -> None:
        self.app.pop_screen()


# ------------------------------------------------------------ Acerca de ----

class AboutScreen(Screen):
    """B · Info detallada del sistema: software y hardware."""

    BINDINGS = [
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{screen_icon("AboutScreen")} {t("about.title")}[/]',
                    classes='title')
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
            self._line(t('about.os_version'), info.get('os_version')),
            self._line(t('about.device_name'), info.get('device_name')),
            self._line(t('about.device_type'), info.get('device_type')),
            self._line(t('about.pm'), info.get('package_manager')),
            self._line(t('about.session'), info.get('session')),
            self._line(t('about.displays'), ', '.join(info.get('displays') or [])),
            '',
            f'{sep} {t("about.section.hardware")} {sep}',
            self._line(t('about.gpu'), info.get('gpu')),
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

    def action_help(self) -> None:
        """?: ayuda contextual de Acerca de."""
        _open_context_help(self)

    def action_back(self) -> None:
        self.app.pop_screen()

# ----------------------------------------------------------------- Logs ----

class LogsScreen(Screen):
    """E · Visor de logs: cola del log de la app con refresco manual."""

    BINDINGS = [('r', 'refresh', t('common.refresh')),
                ('?', 'help', t('common.help')),
                ('escape', 'back', t('common.back'))]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{screen_icon("LogsScreen")} {t("logs.title")}[/]',
                    classes='title')
        with VerticalScroll():
            yield Static('…', id='log-text', markup=False)
        yield Static('', id='logs-status', classes='status', markup=False)
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
        empty = not text or text == t('logs.empty')
        message = '' if empty else f'{t("logs.title")}: {len(text.splitlines())}'
        self.query_one('#logs-status', Static).update(
            _status(message, empty=empty))

    def action_help(self) -> None:
        """?: ayuda contextual de logs."""
        _open_context_help(self)

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
            yield Static('', id='sources-status', classes='status', markup=False)
            yield Footer()

    def on_mount(self) -> None:
        view = self.query_one('#source-options', ListView)
        for i, opt in enumerate(self.options):
            hint = self.hints[i] if i < len(self.hints) else ''
            label = opt if not hint else f'{opt}  [{hint}]'
            view.append(ListItem(Static(label), id=str(i)))
        if self.options:
            view.index = 0
        self.query_one('#sources-status', Static).update(_status(
            f'{len(self.options)} · {t("apps.sources")}',
            empty=not self.options))
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
        ('space', 'toggle_mark', t('apps.mark')),
        ('c', 'category', t('apps.category')),
        ('f', 'filter', t('common.search')),
        Binding('/', 'filter', show=False),
        ('?', 'help', t('common.help')),
        ('escape', 'back', t('common.back')),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.adapter = SourcesAdapter(services.config)
        self._apps = []
        self._category = 'all'
        self._query = ''
        self._marked = set()
        self._installed = set()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(f'[b]{screen_icon("AppsScreen")} {t("apps.title")}[/]',
                    classes='title')
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
        table.add_columns(t('apps.mark'), t('common.name'), t('common.installed'),
                          t('apps.category'), t('apps.sources'), t('common.description'))
        table.focus()
        self.query_one('#apps-loading', LoadingIndicator).display = True
        self._reload()

    def _reload(self) -> None:
        self._apps = self.adapter.list_apps(self._category, self._query)
        table = self.query_one('#apps-table', DataTable)
        table.clear()
        self._load_installed()
        for app in self._apps:
            mark = '✓' if app.name in self._marked else ''
            installed = '✓' if app.name in self._installed else ''
            table.add_row(mark, app.name, installed, app.category,
                          self.adapter.source_summary(app), app.description)
        self._update_status()
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

    def action_help(self) -> None:
        """?: ayuda contextual del catálogo de apps."""
        _open_context_help(self)

    def action_back(self) -> None:
        self.app.pop_screen()

    def _load_installed(self) -> None:
        """Nombres instalados para marcar la columna (solo lectura, best-effort)."""
        try:
            pm = self.services.package_manager
            self._installed = {p.name for p in pm.get_installed_packages(
                use_cache=True, limit=5000)}
        except Exception:
            self._installed = set()

    def action_toggle_mark(self) -> None:
        app = self._selected_app()
        if not app:
            return
        if app.name in self._marked:
            self._marked.discard(app.name)
        else:
            self._marked.add(app.name)
        table = self.query_one('#apps-table', DataTable)
        row = table.cursor_row
        table.update_cell(row, 0, '✓' if app.name in self._marked else '')
        self._update_status()

    def _update_status(self) -> None:
        extra = f' · {len(self._marked)} marcadas' if self._marked else ''
        self.query_one('#apps-status', Static).update(_status(
            f'{len(self._apps)} apps — {t("apps.category")}: '
            f'{self._category}{extra}', empty=not self._apps))

    def _selected_app(self):
        table = self.query_one('#apps-table', DataTable)
        if 0 <= table.cursor_row < len(self._apps):
            return self._apps[table.cursor_row]
        return None

    def _target_apps(self):
        if self._marked:
            return [a for a in self._apps if a.name in self._marked]
        app = self._selected_app()
        return [app] if app else []

    def action_install(self) -> None:
        targets = self._target_apps()
        if not targets:
            return
        if len(targets) > 1:
            self.app.push_screen(
                ConfirmScreen(f'{t("apps.install_batch_confirm")} '
                              f'{len(targets)}?'),
                lambda ok: self._install_batch(targets) if ok else None)
            return
        app = targets[0]
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

    @work(thread=True, exclusive=False)
    def _install_batch(self, targets) -> None:
        self.app.call_from_thread(
            lambda: setattr(self.query_one('#apps-loading', LoadingIndicator),
                            'display', True))
        ok_count = 0
        for app in targets:
            try:
                sources = self.adapter.sources_for(app)
                if not sources:
                    continue
                result = self.adapter.install(app, sources[0])
                ok_count += int(result.ok)
            except Exception:
                logger.exception('instalación por lote falló: %s', app.name)
        self.app.call_from_thread(self.notify,
                                  t('apps.install_batch_ok').format(
                                      ok=ok_count, total=len(targets)))
        self.app.call_from_thread(self._reload)
        self.app.call_from_thread(self._marked.clear)

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
            self.app.call_from_thread(self.app.notify_native, 'TUI Manager', msg)
        except Exception as exc:
            logger.exception('instalación desde fuente falló')
            self.app.call_from_thread(
                self.notify, f'{t("common.error")}: {exc}', severity='error')
        finally:
            # Instalar desde el catálogo siempre recarga la tabla (y oculta
            # el indicador dentro de _reload), también si la acción falló.
            self.app.call_from_thread(self._reload)

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
