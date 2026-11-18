"""
Tests de la capa UI (textual run_test con fakes inyectados en Services).

Todo es simulado: PackageManager y ProcessMonitor son fakes; nada toca
subprocesos reales ni la configuración del usuario (Config en tmp_path).
"""

import pytest

from tui_manager.core.config import Config
from tui_manager.core.package_adapter import Package
from tui_manager.core.process_monitor import Process
from tui_manager.core.theme_manager import ThemeManager
from tui_manager.ui.app import Services, TuiManagerApp
from tui_manager.ui.screens import ScreenManager


FAKE_PACKAGES = [
    Package(name='curl', version='8.5.0-2', description='[network]', installed=True),
    Package(name='git', version='2.45.1', description='[development]', installed=True),
    Package(name='ripgrep', version='14.1.0', description='', installed=False),
]

FAKE_PROCESSES = [
    Process(pid=1, user='root', cpu=0.1, mem=0.2, vsz=10240, rss=4096,
            nice=0, start='08:00', time='0:01', command='/sbin/init'),
    Process(pid=4242, user='user', cpu=15.5, mem=3.2, vsz=204800, rss=65536,
            nice=0, start='09:12', time='1:23', command='firefox'),
]


class FakePackageManager:
    def __init__(self):
        self.calls = []

    def get_installed_packages(self):
        self.calls.append('installed')
        return FAKE_PACKAGES

    def search_package(self, query):
        self.calls.append(('search', query))
        return [FAKE_PACKAGES[0]]

    def get_package_info(self, name):
        self.calls.append(('info', name))
        info = Package(name=name, version='1.0', installed=True)
        info.dependencies = ['libc']
        return info

    def install_package(self, name, confirm=True):
        self.calls.append(('install', name))
        return True

    def remove_package(self, name, confirm=True):
        self.calls.append(('remove', name))
        return True

    def update_package_cache(self):
        self.calls.append('cache')
        return True


class FakeProcessMonitor:
    def __init__(self):
        self.calls = []

    def get_processes(self, filters=None):
        self.calls.append(('list', filters))
        return FAKE_PROCESSES

    def kill_process(self, pid, signal=15):
        self.calls.append(('kill', pid, signal))
        return True

    def renice_process(self, pid, nice):
        self.calls.append(('renice', pid, nice))
        return True


def fake_env(caps_names):
    from tui_manager.core.environment import Capability
    caps = {getattr(Capability, n) for n in caps_names}
    from tui_manager.core.environment import EnvironmentAdapter

    class FakeEnv(EnvironmentAdapter):
        name = 'fake-env'
        def capabilities(self):
            return caps
        def lock_screen(self):
            return True
        def launch_app(self, command):
            return True
        def focus_window(self, title, cls=None):
            return True
        def list_windows(self):
            return []
    return FakeEnv()


def make_services(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    # sin herramientas reales en el PATH del test (evita subprocesos vivos
    # de termux-battery-status y compañía en Acerca de/Sistema)
    import tui_manager.core.system_control as sc_module
    monkeypatch.setattr(sc_module.shutil, 'which', lambda t, *a, **k: None)
    config = Config(config_file=str(tmp_path / 'config.yaml'))
    config.config['language'] = 'es'
    from tui_manager.i18n import set_language
    set_language('es')  # el estado de i18n es global: resetear por test
    return Services(
        config=config,
        package_manager=FakePackageManager(),
        process_monitor=FakeProcessMonitor(),
        theme_manager=ThemeManager('dark'),
        distribution='arch',
        environment=fake_env([]),
    )


async def _wait_workers(app, pilot, rounds=30):
    """Espera a que los workers en hilos terminen y la UI se refresque."""
    for _ in range(rounds):
        await pilot.pause(0.02)


# ---------------------------------------------------------------- menú ----

@pytest.mark.asyncio
async def test_main_menu_entries_and_degradation(tmp_path, monkeypatch):
    """7 entradas; System/Temas/Actualizar deshabilitadas."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import ListItem
        items = app.screen.query(ListItem)
        assert len(items) == 9
        disabled = {i.id for i in items if 'disabled' in i.classes}
        assert disabled == {'themes', 'updates'}
        enabled = {i.id for i in items if 'disabled' not in i.classes}
        assert enabled == {'packages', 'processes', 'system', 'about',
                           'logs', 'settings', 'help'}


@pytest.mark.asyncio
async def test_main_menu_navigates_to_packages(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('down')   # cursor a la primera entrada
        await pilot.press('enter')  # abrir Aplicaciones
        await _wait_workers(app, pilot)
        from tui_manager.ui.screens import PackagesScreen
        assert isinstance(app.screen, PackagesScreen)
        table = app.screen.query_one('#packages-table')
        assert table.row_count == 3
        await pilot.press('escape')  # volver
        from tui_manager.ui.screens import MainMenuScreen
        assert isinstance(app.screen, MainMenuScreen)


@pytest.mark.asyncio
async def test_disabled_entry_notifies(tmp_path, monkeypatch):
    """System/Temas/Actualizar no navegan: solo notifican la fase."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        # 8 downs desde cursor inicial -1 → índice 7 = 'themes'
        for _ in range(8):
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        # sigue en el menú principal (no navegó)
        from tui_manager.ui.screens import MainMenuScreen
        assert isinstance(app.screen, MainMenuScreen)


# ----------------------------------------------------------- paquetes ----

@pytest.mark.asyncio
async def test_packages_search(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('down', 'enter')
        await _wait_workers(app, pilot)
        from textual.widgets import Input
        inp = app.screen.query_one('#search', Input)
        inp.focus()
        await pilot.pause()
        inp.value = 'curl'
        await pilot.press('enter')
        await _wait_workers(app, pilot)
        pm = services.package_manager
        assert pm.calls and pm.calls[-1] == ('search', 'curl')
        table = app.screen.query_one('#packages-table')
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_packages_install_with_confirm(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('down', 'enter')
        await _wait_workers(app, pilot)
        app.screen.action_install()  # instalar seleccionado (fila 0: curl)
        await pilot.pause()
        from tui_manager.ui.screens import ConfirmScreen
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press('y')  # confirmar
        await _wait_workers(app, pilot)
        pm = services.package_manager
        assert ('install', 'curl') in pm.calls


@pytest.mark.asyncio
async def test_packages_install_cancelled(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('down', 'enter')
        await _wait_workers(app, pilot)
        app.screen.action_install()
        await pilot.pause()
        await pilot.press('n')  # cancelar
        await pilot.pause()
        assert not any(c and c[0] == 'install' for c in services.package_manager.calls)


# ----------------------------------------------------------- procesos ----

@pytest.mark.asyncio
async def test_processes_screen_lists_and_kills(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('down', 'down', 'enter')  # segunda entrada: Procesos
        await _wait_workers(app, pilot)
        from tui_manager.ui.screens import ProcessesScreen
        assert isinstance(app.screen, ProcessesScreen)
        table = app.screen.query_one('#process-table')
        assert table.row_count == 2
        app.screen.action_kill()
        await pilot.pause()
        from tui_manager.ui.screens import ConfirmScreen
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press('y')
        await _wait_workers(app, pilot)
        assert ('kill', 1, 15) in services.process_monitor.calls


@pytest.mark.asyncio
async def test_processes_renice(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('down', 'down', 'enter')
        await _wait_workers(app, pilot)
        app.screen.action_renice()  # renice → InputScreen
        await pilot.pause()
        await pilot.press('5')
        await pilot.press('enter')
        await _wait_workers(app, pilot)
        assert ('renice', 1, 5) in services.process_monitor.calls


# -------------------------------------------------------------- ajustes ----

@pytest.mark.asyncio
async def test_settings_change_language_and_theme(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(6):  # índice 5 = 'settings'
            menu.action_cursor_down()
        await pilot.pause()
        menu.action_select_cursor()
        from tui_manager.ui.screens import SettingsScreen
        for _ in range(30):
            await pilot.pause(0.02)
            if isinstance(app.screen, SettingsScreen):
                break
        assert isinstance(app.screen, SettingsScreen)
        lang_select = app.screen.query_one('#select-language')
        lang_select.value = 'en'
        await pilot.pause()
        assert services.config.get('language') == 'en'
        theme_select = app.screen.query_one('#select-theme')
        theme_select.value = 'light'
        await pilot.pause()
        assert services.config.get('theme') == 'light'
        assert app.theme == 'tm-light'


# ---------------------------------------------------------------- ayuda ----

@pytest.mark.asyncio
async def test_help_screen_content(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(7):  # 7 downs desde -1 → índice 6 = 'help'
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        from tui_manager.ui.screens import HelpScreen
        assert isinstance(app.screen, HelpScreen)
        text = str(app.screen.query_one('#help-text').render())
        assert 'tui-manager --doctor' in text


# ----------------------------------------------------------- fachada ----

def test_screen_manager_requires_services_for_run():
    """ScreenManager.run delega en TuiManagerApp (no se lanza en tests)."""
    sm = ScreenManager()
    assert sm.services is None


# ---------------- Alfa 2: Sistema, Acerca de, Logs --------------------------

def fake_env(caps_names):
    from tui_manager.core.environment import Capability
    caps = {getattr(Capability, n) for n in caps_names}
    from tui_manager.core.environment import EnvironmentAdapter

    class FakeEnv(EnvironmentAdapter):
        name = 'fake-env'
        def capabilities(self):
            return caps
        def lock_screen(self):
            return True
        def launch_app(self, command):
            return True
        def focus_window(self, title, cls=None):
            return True
        def list_windows(self):
            return []
    return FakeEnv()


def fake_sc(monkeypatch, available_tools=()):
    import shutil
    import tui_manager.core.system_control as sc
    monkeypatch.setattr(sc.shutil, 'which',
                        lambda t, *a, **k: f'/usr/bin/{t}' if t in available_tools else None)
    from tui_manager.core.system_control import SystemControl
    return SystemControl()


@pytest.mark.asyncio
async def test_system_screen_gating(tmp_path, monkeypatch):
    """Entradas habilitadas/deshabilitadas según disponibilidad real."""
    services = make_services(tmp_path, monkeypatch)
    services.system_control = fake_sc(monkeypatch, available_tools=())
    services.environment = fake_env(['LOCK_SCREEN'])  # lock disponible, resto no
    services.system_control.environment = services.environment
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(3):  # 3 downs desde -1 → índice 2 = 'system'
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        from tui_manager.ui.screens import SystemScreen
        assert isinstance(app.screen, SystemScreen)
        from textual.widgets import ListItem
        items = app.screen.query(ListItem)
        ids_disabled = {i.id for i in items if 'disabled' in i.classes}
        # sin herramientas y sin LAUNCH_APP: solo lock queda habilitado
        assert 'lock' not in ids_disabled
        assert {'launch', 'logout', 'reboot', 'shutdown', 'suspend',
                'brightness_up', 'power_profiles', 'timezone'} <= ids_disabled


@pytest.mark.asyncio
async def test_system_screen_launch_flow(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    services.system_control = fake_sc(monkeypatch, available_tools=())
    services.environment = fake_env(['LAUNCH_APP'])
    services.system_control.environment = services.environment
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(3):
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        from tui_manager.ui.screens import SystemScreen
        screen = app.screen
        assert isinstance(screen, SystemScreen)
        # primera entrada del menú Sistema: 'launch' (1 down desde -1)
        await pilot.press('down')
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        from tui_manager.ui.screens import InputScreen
        assert isinstance(app.screen, InputScreen)
        inp = app.screen.query_one('#modal-input')
        inp.value = 'foot editor'
        await pilot.press('enter')
        await _wait_workers(app, pilot)
        # el env fake siempre lanza con éxito → toast system.done
        from tui_manager.ui.screens import SystemScreen
        assert isinstance(app.screen, SystemScreen)


@pytest.mark.asyncio
async def test_about_screen_fill(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(4):  # índice 3 = 'about'
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await _wait_workers(app, pilot)
        from tui_manager.ui.screens import AboutScreen
        assert isinstance(app.screen, AboutScreen)
        text = str(app.screen.query_one('#about-text').render())
        assert 'arch' in text          # distribución del fake
        assert 'fake-env' in text      # entorno fake
        assert '3' in text             # N paquetes del FakePackageManager


@pytest.mark.asyncio
async def test_logs_screen_shows_tail(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)  # HOME → tmp_path
    log_dir = tmp_path / '.tui-manager' / 'logs'
    log_dir.mkdir(parents=True)
    (log_dir / 'app.log').write_text('line1: inicio\nline2: paquetes\n')
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(5):  # índice 4 = 'logs'
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        from tui_manager.ui.screens import LogsScreen
        assert isinstance(app.screen, LogsScreen)
        for _ in range(30):
            await pilot.pause(0.02)
            text = str(app.screen.query_one('#log-text').render())
            if 'line2: paquetes' in text:
                break
        text = str(app.screen.query_one('#log-text').render())
        assert 'line2: paquetes' in text


@pytest.mark.asyncio
async def test_logs_screen_empty_message(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)  # sin log creado
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(5):
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        for _ in range(30):
            await pilot.pause(0.02)
            text = str(app.screen.query_one('#log-text').render())
            if 'No hay log todavía' in text:
                break
        text = str(app.screen.query_one('#log-text').render())
        assert 'No hay log todavía' in text
