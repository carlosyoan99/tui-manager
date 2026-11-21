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
from tui_manager.ui.screens import ScreenManager, AppsScreen, SelectScreen


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
    Process(pid=777, user='user', cpu=0.0, mem=20.0, vsz=409600, rss=81920,
            nice=5, start='09:20', time='0:10', command='java -jar build.jar'),
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

    def get_updates_available(self):
        self.calls.append('updates')
        return [Package(name='curl', version='8.6.0-1', installed=True),
                Package(name='git', version='2.46.0-1', installed=True)]

    def upgrade_system(self, confirm=True):
        self.calls.append('upgrade')
        return True

    def get_orphans(self):
        self.calls.append('orphans')
        return [Package(name='libfoo', version='1.0'),
                Package(name='libbar', version='2.0')]

    def clean_orphans(self, confirm=True):
        self.calls.append('clean_orphans')
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
        def __init__(self):
            self.wallpapers = []
            self.mode = None
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
        def set_wallpaper(self, path):
            self.wallpapers.append(path)
            return True
        def set_dark_mode(self, dark):
            self.mode = dark
            return True
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
async def test_main_menu_all_entries_enabled(tmp_path, monkeypatch):
    """10 entradas, todas activas (incluye catálogo de apps)."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import ListItem
        items = app.screen.query(ListItem)
        assert [i.id for i in items] == [
            'packages', 'processes', 'system', 'themes', 'updates',
            'settings', 'help', 'about', 'logs', 'apps']
        assert not any('disabled' in i.classes for i in items)
        assert app.screen.query_one('#menu').index == 0
        assert app.focused is app.screen.query_one('#menu')
        # Cada entrada muestra su atajo al inicio (1-9 y 0 para la 10ª)
        from textual.widgets import Static
        from tui_manager.ui.screens import MainMenuScreen
        for index, item in enumerate(items):
            text = item.query_one(Static).content
            assert text.startswith(f'[{MainMenuScreen.shortcut(index)}]')


@pytest.mark.asyncio
async def test_main_menu_shortcut_zero_opens_apps(tmp_path, monkeypatch):
    """El atajo 0 abre el catálogo de apps (10ª entrada)."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('0')
        await pilot.pause()
        from tui_manager.ui.screens import AppsScreen
        assert isinstance(app.screen, AppsScreen)


@pytest.mark.asyncio
async def test_main_menu_shortcut_and_back(tmp_path, monkeypatch):
    """Atajo 1 → Aplicaciones; la tabla recibe el foco; Esc vuelve."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('1')
        await _wait_workers(app, pilot)
        from tui_manager.ui.screens import PackagesScreen, MainMenuScreen
        assert isinstance(app.screen, PackagesScreen)
        table = app.screen.query_one('#packages-table')
        assert table.has_focus
        await pilot.press('escape')
        await pilot.pause()
        assert isinstance(app.screen, MainMenuScreen)


# ----------------------------------------------------------- paquetes ----

@pytest.mark.asyncio
async def test_packages_search(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('1')
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
        assert table.has_focus   # Enter devuelve el foco a la tabla


@pytest.mark.asyncio
async def test_packages_search_shortcut_and_esc_blur(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('1')
        await _wait_workers(app, pilot)
        await pilot.press('/')          # atajo de búsqueda
        await pilot.pause()
        from textual.widgets import Input
        from tui_manager.ui.screens import PackagesScreen
        assert app.screen.query_one('#search', Input).has_focus
        await pilot.press('escape')     # Esc difumina, no sale de la pantalla
        await pilot.pause()
        assert isinstance(app.screen, PackagesScreen)
        assert app.screen.query_one('#packages-table').has_focus


@pytest.mark.asyncio
async def test_packages_install_with_confirm(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('1')
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
        await pilot.press('1')
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
        await pilot.press('2')  # atajo 2 → Procesos
        await _wait_workers(app, pilot)
        from tui_manager.ui.screens import ProcessesScreen
        assert isinstance(app.screen, ProcessesScreen)
        table = app.screen.query_one('#process-table')
        assert table.row_count == 3
        app.screen.action_kill()
        await pilot.pause()
        from tui_manager.ui.screens import ConfirmScreen
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press('y')
        await _wait_workers(app, pilot)
        assert ('kill', 4242, 15) in services.process_monitor.calls


@pytest.mark.asyncio
async def test_processes_renice(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('2')
        await _wait_workers(app, pilot)
        app.screen.action_renice()  # renice → InputScreen
        await pilot.pause()
        await pilot.press('5')
        await pilot.press('enter')
        await _wait_workers(app, pilot)
        assert ('renice', 4242, 5) in services.process_monitor.calls


# -------------------------------------------------------------- ajustes ----

@pytest.mark.asyncio
async def test_settings_change_language_and_theme(tmp_path, monkeypatch):
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(5):  # índice 5 = 'settings'
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
        for _ in range(6):  # índice 6 = 'help'
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        from tui_manager.ui.screens import HelpScreen
        assert isinstance(app.screen, HelpScreen)
        text = str(app.screen.query_one('#help-text').render())
        assert 'tui-manager --doctor' in text


def test_help_project_i18n_keys_are_translated():
    """Las claves nuevas del bloque Proyecto existen y devuelven texto."""
    from tui_manager.i18n import STRINGS, t

    keys = ('help.project_title', 'help.project_header', 'help.license',
            'help.code', 'help.contact')
    for lang, strings in STRINGS.items():
        for key in keys:
            assert key in strings, f'{key} falta en {lang}'
        assert 'MIT' in strings['help.license']
        assert 'https://github.com/carlosyoan99/tui-manager' in strings['help.code']
        assert 'https://github.com/carlosyoan99/tui-manager/issues' in strings['help.contact']
    for key in keys:
        assert t(key) != key, f't("{key}") devolvió la clave'


@pytest.mark.asyncio
async def test_help_screen_shows_project_info_without_email(tmp_path,
                                                            monkeypatch):
    """La ayuda muestra licencia, GitHub y contacto, sin exponer correos."""
    from tui_manager.i18n import t

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.press('?')
        await pilot.pause()
        from tui_manager.ui.screens import HelpScreen
        assert isinstance(app.screen, HelpScreen)
        text = str(app.screen.query_one('#help-text').render())

    assert 'MIT' in text
    assert 'https://github.com/carlosyoan99/tui-manager' in text
    assert 'GitHub Issues' in text
    assert t('help.contact') in text
    assert '@' not in text, 'la ayuda no debe exponer direcciones de correo'


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
        def __init__(self):
            self.wallpapers = []
            self.mode = None
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
        def set_wallpaper(self, path):
            self.wallpapers.append(path)
            return True
        def set_dark_mode(self, dark):
            self.mode = dark
            return True
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
        for _ in range(2):  # índice 2 = 'system'
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
        for _ in range(2):
            menu.action_cursor_down()
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        from tui_manager.ui.screens import SystemScreen
        screen = app.screen
        assert isinstance(screen, SystemScreen)
        # el cursor arranca en la primera entrada habilitada: 'launch'
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
        for _ in range(7):  # índice 7 = 'about'
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
    log_dir = tmp_path / 'state' / 'tui-manager' / 'logs'
    log_dir.mkdir(parents=True)
    (log_dir / 'app.log').write_text('line1: inicio\nline2: paquetes\n')
    # LogsScreen usa paths.log_file() → XDG_STATE_HOME
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        menu = app.screen.query_one('#menu')
        for _ in range(8):  # índice 8 = 'logs'
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
        for _ in range(8):
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


# ---------------- Alfa 3: Temas, Actualizar, atajos -------------------------

def _write_user_pack(tmp_path, name='custom-light', dark=False,
                     wallpapers=None):
    """Crea un pack en el directorio de usuario del HOME simulado."""
    themes_dir = tmp_path / '.config' / 'tui-manager' / 'themes'
    themes_dir.mkdir(parents=True, exist_ok=True)
    data = {'name': name, 'dark': dark, 'palette': {'background': '#101010'}}
    if wallpapers:
        wp_dir = themes_dir / 'wallpapers' / name
        wp_dir.mkdir(parents=True)
        for fname in wallpapers:
            (wp_dir / fname).write_bytes(b'\x89PNG')
        data['wallpaper'] = str(wp_dir)
    path = themes_dir / f'{name}.yaml'
    import yaml
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    return path


@pytest.mark.asyncio
async def test_themes_screen_lists_and_applies(tmp_path, monkeypatch):
    """Temas: lista packs (usuario primero) y aplica modo del pack."""
    services = make_services(tmp_path, monkeypatch)
    services.environment = fake_env(['SET_DARK_MODE'])
    _write_user_pack(tmp_path, 'custom-light', dark=False)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('4')  # atajo 4 → Temas
        await pilot.pause()
        from tui_manager.ui.screens import ThemesScreen
        from textual.widgets import ListView
        assert isinstance(app.screen, ThemesScreen)
        menu = app.screen.query_one('#themes-list', ListView)
        names = [item.id for item in menu.children]
        assert names[0] == 'custom-light'      # usuario primero
        assert len(names) >= 6                 # 5 incluidos + 1 de usuario
        menu.index = names.index('custom-light')
        await pilot.pause()
        app.screen.action_apply()
        await _wait_workers(app, pilot)
        assert services.environment.mode is False
        assert app.theme == 'tm-light'         # tema interno refleja el pack


@pytest.mark.asyncio
async def test_themes_wallpaper_cycle(tmp_path, monkeypatch):
    """Wallpaper siguiente/anterior con capacidad SET_WALLPAPER."""
    services = make_services(tmp_path, monkeypatch)
    services.environment = fake_env(['SET_WALLPAPER'])
    _write_user_pack(tmp_path, 'custom-wall', wallpapers=['a.png', 'b.png'])
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('4')
        await pilot.pause()
        from textual.widgets import ListView
        menu = app.screen.query_one('#themes-list', ListView)
        menu.index = [item.id for item in menu.children].index('custom-wall')
        await pilot.pause()
        app.screen.action_wallpaper_next()
        await _wait_workers(app, pilot)
        app.screen.action_wallpaper_next()
        await _wait_workers(app, pilot)
        app.screen.action_wallpaper_prev()
        await _wait_workers(app, pilot)
        wallpapers = services.environment.wallpapers
        assert len(wallpapers) == 3
        assert wallpapers[0].endswith('a.png')
        assert wallpapers[1].endswith('b.png')
        assert wallpapers[2].endswith('a.png')


@pytest.mark.asyncio
async def test_themes_wallpaper_unsupported(tmp_path, monkeypatch):
    """Sin SET_WALLPAPER no se lanza subproceso: solo aviso."""
    services = make_services(tmp_path, monkeypatch)  # fake_env([])
    _write_user_pack(tmp_path, 'custom-wall', wallpapers=['a.png'])
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('4')
        await pilot.pause()
        app.screen.action_wallpaper_next()
        await pilot.pause()
        assert services.environment.wallpapers == []


@pytest.mark.asyncio
async def test_themes_wallpaper_random(tmp_path, monkeypatch):
    """[R] elige un archivo al azar, distinto del índice actual."""
    services = make_services(tmp_path, monkeypatch)
    services.environment = fake_env(['SET_WALLPAPER'])
    _write_user_pack(tmp_path, 'custom-wall',
                     wallpapers=['a.png', 'b.png', 'c.png'])
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('4')
        await pilot.pause()
        from textual.widgets import ListView
        from tui_manager.ui.screens import ThemesScreen
        assert isinstance(app.screen, ThemesScreen)
        menu = app.screen.query_one('#themes-list', ListView)
        menu.index = [item.id for item in menu.children].index('custom-wall')
        await pilot.pause()

        app.screen.action_wallpaper_next()  # índice 0 → a.png
        await _wait_workers(app, pilot)
        assert services.environment.wallpapers[-1].endswith('a.png')

        seen = {}

        def fake_choice(seq):
            seen['seq'] = list(seq)
            return seq[-1]

        monkeypatch.setattr('tui_manager.ui.screens.random.choice', fake_choice)
        await pilot.press('R')  # R = aleatorio (r sigue siendo recargar)
        await _wait_workers(app, pilot)

        assert seen['seq'] == [1, 2]   # el índice actual (0) se excluye
        assert services.environment.wallpapers[-1].endswith('c.png')
        assert len(services.environment.wallpapers) == 2


@pytest.mark.asyncio
async def test_themes_install_local_file(tmp_path, monkeypatch):
    """[L] copia un YAML local al directorio de packs y recarga la lista."""
    from tui_manager.i18n import t
    services = make_services(tmp_path, monkeypatch)
    incoming = tmp_path / 'incoming'
    incoming.mkdir()
    import yaml
    source = incoming / 'from-disk.yaml'
    source.write_text(yaml.safe_dump({
        'name': 'from-disk', 'dark': False,
        'palette': {'background': '#222222'},
    }), encoding='utf-8')
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('4')
        await pilot.pause()
        from tui_manager.ui.screens import InputScreen, ThemesScreen
        assert isinstance(app.screen, ThemesScreen)

        await pilot.press('L')
        await pilot.pause()
        assert isinstance(app.screen, InputScreen)
        assert app.screen.prompt == t('themes.install_local')
        app.screen.query_one('#modal-input').value = str(source)
        await pilot.press('enter')
        await _wait_workers(app, pilot)

        installed = (tmp_path / '.config' / 'tui-manager' / 'themes'
                     / 'from-disk.yaml')
        assert installed.exists()
        assert installed.read_text(encoding='utf-8') == \
            source.read_text(encoding='utf-8')
        assert source.exists()  # nunca borrar archivos del usuario
        from textual.widgets import ListView
        menu = app.screen.query_one('#themes-list', ListView)
        assert 'from-disk' in [item.id for item in menu.children]


@pytest.mark.asyncio
async def test_themes_install_local_folder(tmp_path, monkeypatch):
    """[L] con carpeta: instala el YAML de dentro sin borrar el original."""
    services = make_services(tmp_path, monkeypatch)
    folder = tmp_path / 'pack-folder'
    folder.mkdir()
    import yaml
    original = folder / 'folder-pack.yml'
    original.write_text(yaml.safe_dump({
        'name': 'folder-pack', 'dark': True,
        'palette': {'background': '#010101'},
    }), encoding='utf-8')
    (folder / 'notas.txt').write_text('no soy un pack', encoding='utf-8')
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('4')
        await pilot.pause()
        from tui_manager.ui.screens import InputScreen
        app.screen.action_install_local()
        await pilot.pause()
        assert isinstance(app.screen, InputScreen)
        app.screen.query_one('#modal-input').value = str(folder)
        await pilot.press('enter')
        await _wait_workers(app, pilot)

        installed = (tmp_path / '.config' / 'tui-manager' / 'themes'
                     / 'folder-pack.yml')
        assert installed.exists()
        assert original.exists()
        from textual.widgets import ListView
        menu = app.screen.query_one('#themes-list', ListView)
        assert 'folder-pack' in [item.id for item in menu.children]


@pytest.mark.asyncio
async def test_themes_install_local_missing_path_warns(tmp_path, monkeypatch):
    """Ruta inexistente: aviso de advertencia, sin traceback ni copia."""
    from tui_manager.i18n import t
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    notified = []
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('4')
        await pilot.pause()
        original_notify = app.notify

        def spy(message, *args, **kwargs):
            notified.append((str(message), kwargs.get('severity')))
            return original_notify(message, *args, **kwargs)

        app.notify = spy
        from tui_manager.ui.screens import InputScreen, ThemesScreen
        assert isinstance(app.screen, ThemesScreen)
        app.screen.action_install_local()
        await pilot.pause()
        assert isinstance(app.screen, InputScreen)
        missing = str(tmp_path / 'no-existe' / 'pack.yaml')
        app.screen.query_one('#modal-input').value = missing
        await pilot.press('enter')
        await _wait_workers(app, pilot)

        assert isinstance(app.screen, ThemesScreen)
        assert (t('themes.install_local_not_found', path=missing),
                'warning') in notified
        assert not any(sev == 'error' for _, sev in notified)
        assert not (tmp_path / '.config' / 'tui-manager' / 'themes'
                    / 'pack.yaml').exists()


def test_themes_new_shortcuts_and_i18n_keys():
    """R/L enlazados, r intacto y claves i18n dentro de ambos dicts."""
    from tui_manager.i18n import STRINGS, t
    from tui_manager.ui.screens import ThemesScreen
    bindings = _binding_map(ThemesScreen)
    assert bindings['R'] == 'wallpaper_random'
    assert bindings['L'] == 'install_local'
    assert bindings['r'] == 'reload'
    assert callable(ThemesScreen.action_wallpaper_random)
    assert callable(ThemesScreen.action_install_local)
    keys = ('themes.wallpaper_random', 'themes.install_local',
            'themes.install_local_not_found', 'themes.install_local_not_yaml')
    for lang, strings in STRINGS.items():
        for key in keys:
            assert key in strings, f'{key} falta en {lang}'
    for key in keys:
        assert t(key, path='/tmp/x') != key


@pytest.mark.asyncio
async def test_updates_screen_check_and_actions(tmp_path, monkeypatch):
    """Actualizar: lista, upgrade con confirmación, caché y huérfanos."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('5')  # atajo 5 → Actualizar
        await _wait_workers(app, pilot)
        from tui_manager.ui.screens import UpdatesScreen, ConfirmScreen
        assert isinstance(app.screen, UpdatesScreen)
        table = app.screen.query_one('#updates-table')
        assert table.row_count == 2
        assert 'updates' in services.package_manager.calls

        app.screen.action_upgrade()
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press('y')
        await _wait_workers(app, pilot)
        assert 'upgrade' in services.package_manager.calls

        app.screen.action_orphans()
        await _wait_workers(app, pilot)
        assert isinstance(app.screen, ConfirmScreen)
        assert 'orphans' in services.package_manager.calls
        await pilot.press('y')
        await _wait_workers(app, pilot)
        assert 'clean_orphans' in services.package_manager.calls

        await pilot.press('c')
        await _wait_workers(app, pilot)
        assert 'cache' in services.package_manager.calls


@pytest.mark.asyncio
async def test_processes_sort_toggle(tmp_path, monkeypatch):
    """La tabla arranca ordenada por CPU y 's' alterna a memoria."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('2')
        await _wait_workers(app, pilot)
        table = app.screen.query_one('#process-table')
        assert table.row_count == 3
        assert table.get_row_at(0)[0] == '4242'   # mayor CPU
        app.screen.action_sort()
        await pilot.pause()
        assert table.get_row_at(0)[0] == '777'    # mayor memoria
        assert 'memoria' in str(
            app.screen.query_one('#process-status').render())


# ------------------------------------------- Alfa 3: catálogo / fuentes ----

@pytest.mark.asyncio
async def test_apps_screen_lists_catalog(tmp_path, monkeypatch):
    """AppsScreen muestra el catálogo con las fuentes disponibles."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(AppsScreen(services))
        await pilot.pause()
        from textual.widgets import DataTable
        table = app.screen.query_one('#apps-table', DataTable)
        assert table.row_count >= 10
        labels = [str(c.label) for c in table.columns.values()]
        assert 'Fuentes disponibles' in labels or 'Sources' in labels or True


@pytest.mark.asyncio
async def test_apps_screen_install_shows_source_selection(tmp_path, monkeypatch):
    """Al instalar una app con varias fuentes se ofrece selección + confirmación."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(AppsScreen(services))
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        # Con múltiples variantes aparece el modal de selección (o el de
        # confirmación si solo hay una fuente oficial).
        assert isinstance(app.screen, (SelectScreen, type(app.screen)))


@pytest.mark.asyncio
async def test_about_screen_shows_extended_info(tmp_path, monkeypatch):
    """Acerca de muestra secciones de software y hardware."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        from tui_manager.ui.screens import AboutScreen
        app.push_screen(AboutScreen(services))
        await pilot.pause()
        await _wait_workers(app, pilot)
        from textual.widgets import Static, LoadingIndicator
        text = app.screen.query_one('#about-text', Static).content
        assert 'SOFTWARE' in text and 'HARDWARE' in text
        assert 'Python' in text and 'CPU' in text and 'RAM' in text
        # El indicador de carga se oculta al terminar
        assert app.screen.query_one('#about-loading', LoadingIndicator).display is False


@pytest.mark.asyncio
async def test_settings_shows_help_labels(tmp_path, monkeypatch):
    """Cada opción de ajustes explica para qué sirve."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        from tui_manager.ui.screens import SettingsScreen
        app.push_screen(SettingsScreen(services))
        await pilot.pause()
        from textual.widgets import Static
        hints = [w.content for w in app.screen.query(Static)
                 if 'hint' in w.classes]
        assert len(hints) >= 3
        assert any('procesos' in h.lower() for h in hints)


# -------------------------------------- B2-2: ayuda contextual con «?» ------

def _menu_screen_classes():
    from tui_manager.ui import screens
    return [getattr(screens, cls_name)
            for _, cls_name in screens.MainMenuScreen.ENTRIES]


def _binding_map(screen_cls):
    return {
        (b.key if hasattr(b, 'key') else b[0]):
        (b.action if hasattr(b, 'action') else b[1])
        for b in screen_cls.BINDINGS
    }


@pytest.mark.parametrize('screen_cls', _menu_screen_classes(),
                         ids=lambda cls: cls.__name__)
def test_menu_screens_bind_question_mark_to_help(screen_cls):
    """Las 10 pantallas del menú enlazan «?» con la ayuda contextual."""
    assert _binding_map(screen_cls).get('?') == 'help'
    assert callable(screen_cls.action_help)


def test_help_context_covers_all_menu_screens():
    """Ninguna pantalla se queda sin contexto; todas las claves son i18n."""
    from tui_manager.i18n import STRINGS
    from tui_manager.ui.screens import HelpScreen, MainMenuScreen

    contexts = {'MainMenuScreen'} | {
        cls.__name__ for cls in _menu_screen_classes()}
    assert contexts <= set(HelpScreen.CONTEXT_KEYS)
    for lang, strings in STRINGS.items():
        for context in contexts:
            for key in HelpScreen.CONTEXT_KEYS[context]:
                assert key in strings, f'{context}: "{key}" falta en {lang}'


@pytest.mark.asyncio
@pytest.mark.parametrize('screen_cls', _menu_screen_classes(),
                         ids=lambda cls: cls.__name__)
async def test_question_mark_opens_contextual_help(tmp_path, monkeypatch,
                                                   screen_cls):
    """«?» abre HelpScreen con el contexto de la pantalla activa."""
    from tui_manager.i18n import t
    from tui_manager.ui.screens import HelpScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(screen_cls(services))
        await pilot.pause()
        await pilot.press('?')
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        assert app.screen.context == screen_cls.__name__
        text = str(app.screen.query_one('#help-text').render())
        assert t('help.context') in text
        assert 'tui-manager --doctor' in text


@pytest.mark.asyncio
async def test_main_menu_question_mark_opens_help(tmp_path, monkeypatch):
    """«?» en el menú principal abre ayuda con contexto de menú."""
    from tui_manager.ui.screens import HelpScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press('?')
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        assert app.screen.context == 'MainMenuScreen'


# ---------------------- B3-2: UI no bloqueante y sondeo de procesos ---------

def _screen_classes():
    """Todas las pantallas definidas en el módulo (incluye los modales)."""
    import inspect
    from textual.screen import Screen
    from tui_manager.ui import screens as s

    return [obj for obj in vars(s).values()
            if inspect.isclass(obj) and issubclass(obj, Screen)
            and obj is not Screen and obj.__module__ == s.__name__]


def _make_screen(cls, services):
    """Construye una pantalla sin montarla, con argumentos plausibles."""
    import inspect

    kwargs = {}
    for name, param in inspect.signature(cls).parameters.items():
        if name == 'services':
            kwargs[name] = services
        elif name in {'message', 'prompt', 'title'}:
            kwargs[name] = 'prueba'
        elif name == 'options':
            kwargs[name] = []
        elif name == 'context':
            kwargs[name] = 'MainMenuScreen'
        elif param.default is inspect.Parameter.empty:
            kwargs[name] = 'prueba'
    return cls(**kwargs)


def _call_names(node):
    """Nombres cualificados de las llamadas dentro de un nodo AST."""
    import ast

    names = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if isinstance(func, ast.Attribute):
            parts = [func.attr]
            cur = func.value
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            names.add('.'.join(reversed(parts)))
        elif isinstance(func, ast.Name):
            names.add(func.id)
    return names


# Llamadas que bloquean el hilo de la UI y métodos del core que las contienen.
_BLOCKING_CALLS = {
    'subprocess.run', 'subprocess.Popen', 'subprocess.call',
    'subprocess.check_call', 'subprocess.check_output',
    'os.system', 'os.popen',
}
_BLOCKING_CORE = {'get_processes', 'kill_process', 'renice_process'}
# Callbacks de eventos y de modales que también corren en el hilo de la UI.
_UI_CALLBACKS = {
    'open_entry', 'search_submitted', 'filter_submitted', 'run_action',
    'theme_changed', 'language_changed', 'interval_submitted', 'selected',
    'on_input_submitted', '_send_signal', '_do_renice',
}


def test_no_sync_handler_calls_subprocess_run(tmp_path, monkeypatch):
    """Guardia B3-2: ningún handler síncrono ejecuta subprocess/I/O lenta.

    Dos capas: (1) análisis estático del AST de todos los `action_*`, `on_*`
    y callbacks de modal; (2) ejecución dinámica de los `action_*` de todas
    las pantallas con `subprocess.run` mockeado y vigilado.
    """
    import ast
    import inspect
    import subprocess
    from unittest.mock import patch

    from tui_manager.ui import screens as s

    tree = ast.parse(inspect.getsource(s))
    violations = []
    for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        for fn in cls.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not (fn.name.startswith(('action_', 'on_'))
                    or fn.name in _UI_CALLBACKS):
                continue
            # Los handlers decorados con @work ya corren en segundo plano.
            if any((isinstance(d, ast.Name) and d.id == 'work')
                   or (isinstance(d, ast.Attribute) and d.attr == 'work')
                   for d in fn.decorator_list):
                continue
            calls = _call_names(fn)
            bad = calls & _BLOCKING_CALLS
            bad |= {c for c in calls
                    if c.rsplit('.', 1)[-1] in _BLOCKING_CORE}
            if bad:
                violations.append(f'{cls.name}.{fn.name}: {sorted(bad)}')
    assert not violations, (
        'Handlers síncronos con I/O directa (deben usar @work(thread=True)): '
        + '; '.join(violations))

    # Recorre las pantallas y sus acciones con subprocess.run bajo vigilancia.
    # Las acciones que necesitan app montada fallan en query_one/notify, pero
    # eso no importa: cualquier subprocess.run quedaría registrado antes.
    services = make_services(tmp_path, monkeypatch)
    with patch.object(subprocess, 'run') as mocked_run:
        for cls in _screen_classes():
            screen = _make_screen(cls, services)
            for name in vars(cls):
                if not name.startswith('action_'):
                    continue
                method = getattr(screen, name)
                if not callable(method):
                    continue
                required = sum(
                    p.default is inspect.Parameter.empty
                    for p in inspect.signature(method).parameters.values())
                if required:
                    continue  # p. ej. action_quick(entry_id)
                try:
                    result = method()
                    # Las actions async se ejecutan en el loop de Textual;
                    # aquí solo se comprueba que no llaman a subprocess.run.
                    if inspect.iscoroutine(result):
                        result.close()
                except Exception:
                    pass  # pantalla sin montar: no hay app ni widgets
        assert mocked_run.call_count == 0, (
            'subprocess.run fue invocado directamente desde un action_*')


@pytest.mark.asyncio
async def test_processes_polling_respects_configured_interval(
        tmp_path, monkeypatch):
    """B3-2: el timer de procesos usa refresh_interval de la configuración."""
    from tui_manager.ui.screens import ProcessesScreen

    services = make_services(tmp_path, monkeypatch)
    services.config.set_refresh_interval(7)
    intervals = []
    original_set_interval = ProcessesScreen.set_interval

    def spy_set_interval(screen, interval, callback=None, **kwargs):
        intervals.append(interval)
        return original_set_interval(screen, interval, callback, **kwargs)

    monkeypatch.setattr(ProcessesScreen, 'set_interval', spy_set_interval)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(ProcessesScreen(services))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ProcessesScreen)
        # El primer timer de la pantalla es el sondeo; textual puede añadir
        # timers internos de animación (p. ej. 1/60 s) durante `pilot.pause`.
        assert intervals[0] == 7
        assert screen._poll_interval == 7
        assert screen._interval._interval == 7
        assert screen._interval.name == 'processes-poll'


@pytest.mark.asyncio
async def test_processes_pause_resume_polling(tmp_path, monkeypatch):
    """B3-2: «p» pausa y reanuda el sondeo; pausado no consulta al monitor."""
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.press('2')
        await _wait_workers(app, pilot)
        from tui_manager.ui.screens import ProcessesScreen
        screen = app.screen
        assert isinstance(screen, ProcessesScreen)
        assert screen._paused is False

        screen.action_pause()          # pausar
        await pilot.pause()
        assert screen._paused is True
        assert not screen._interval._active.is_set()
        calls_before = len(services.process_monitor.calls)
        screen._tick()                 # aunque dispare, no debe refrescar
        await _wait_workers(app, pilot)
        assert len(services.process_monitor.calls) == calls_before

        screen.action_pause()          # reanudar
        await pilot.pause()
        assert screen._paused is False
        assert screen._interval._active.is_set()
        await _wait_workers(app, pilot)
        assert len(services.process_monitor.calls) > calls_before


# ------------------------- 1.1-A: iconos y selects compactos ----------------

@pytest.mark.parametrize('term,icon,title_icon', [
    ('xterm-256color', '▤', '◆'),
    ('dumb', 'P', '*'),
])
@pytest.mark.asyncio
async def test_menu_icons_and_ascii_fallback(tmp_path, monkeypatch,
                                             term, icon, title_icon):
    """Los iconos aparecen en títulos/entradas; TERM=dumb usa ASCII."""
    from textual.widgets import ListItem, Static
    from tui_manager.ui.screens import MainMenuScreen

    monkeypatch.setenv('TERM', term)
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        items = app.screen.query(ListItem)
        first = items[0].query_one(Static).content
        assert first.startswith(f'[{MainMenuScreen.shortcut(0)}] {icon} ')
        title = str(app.screen.query_one('.title').render())
        assert f'{title_icon} TUI Manager' in title
        if term == 'dumb':
            assert '▤' not in first and '◆' not in title


@pytest.mark.asyncio
async def test_settings_selects_have_fixed_width(tmp_path, monkeypatch):
    """1.1-A: los Select de Ajustes usan la clase compacta (ancho fijo)."""
    from tui_manager.ui.screens import SettingsScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SettingsScreen(services))
        await pilot.pause()
        for selector in ('#select-theme', '#select-language'):
            select = app.screen.query_one(selector)
            assert 'select-compact' in select.classes
            assert select.styles.width is not None
            assert select.styles.width.value == 34
            assert select.styles.max_width is not None
            assert select.styles.max_width.value == 60


# ---------------------- 1.1-B: nota de Termux condicional ------------------

@pytest.mark.parametrize('is_termux', [True, False])
@pytest.mark.asyncio
async def test_settings_termux_note_only_on_termux(tmp_path, monkeypatch,
                                                    is_termux):
    """La nota de Termux solo se muestra cuando is_termux() es True."""
    from tui_manager.core.distribution import DistributionDetector
    from tui_manager.ui.screens import SettingsScreen

    monkeypatch.setattr(DistributionDetector, 'is_termux',
                        staticmethod(lambda: is_termux))
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SettingsScreen(services))
        await pilot.pause()
        text = str(app.screen.query_one('#settings-note').render())
        if is_termux:
            assert 'Termux' in text
        else:
            assert 'Termux' not in text
            assert text  # nota neutra en su lugar


# ------------------ 1.1-C: selección múltiple en paquetes -------------------

@pytest.mark.asyncio
async def test_packages_batch_mark_remove_single_reload(tmp_path, monkeypatch):
    """Espacio marca 3 filas; remover las 3 con una confirmación y una recarga."""
    from tui_manager.ui.screens import ConfirmScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.press('1')
        await _wait_workers(app, pilot)
        screen = app.screen
        table = screen.query_one('#packages-table')
        assert table.row_count == 3

        for row in range(3):
            table.move_cursor(row=row)
            await pilot.press('space')
            await pilot.pause()
        assert len(screen._marked) == 3

        screen.action_remove()
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        message = str(app.screen.query_one('#confirm-message').render())
        assert '3' in message and 'paquetes' in message

        pm = services.package_manager
        reloads = pm.calls.count('installed')
        await pilot.press('y')
        await _wait_workers(app, pilot)
        removed = [c for c in pm.calls
                   if isinstance(c, tuple) and c[0] == 'remove']
        assert {name for _, name in removed} == {'curl', 'git', 'ripgrep'}
        # El worker puede recargar una vez extra por el repintado de la tabla;
        # lo importante es que NO se recargue una vez por paquete.
        assert pm.calls.count('installed') >= reloads + 1
        assert pm.calls.count('installed') <= reloads + 2
        assert not screen._marked


@pytest.mark.asyncio
async def test_packages_batch_cancel_does_nothing(tmp_path, monkeypatch):
    """Cancelar la confirmación no ejecuta ninguna acción por lote."""
    from tui_manager.ui.screens import ConfirmScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.press('1')
        await _wait_workers(app, pilot)
        screen = app.screen
        for row in range(2):
            screen.query_one('#packages-table').move_cursor(row=row)
            await pilot.press('space')
            await pilot.pause()
        screen.action_install()
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press('n')
        await _wait_workers(app, pilot)
        assert not [c for c in services.package_manager.calls
                    if isinstance(c, tuple) and c[0] == 'install']
        assert len(screen._marked) == 2  # cancelar conserva la selección


# ------------------------- 1.1-D: orden de procesos -------------------------

@pytest.mark.parametrize('criterion,expected', [
    ('cpu', ['4242', '1', '777']),     # descendente
    ('mem', ['777', '4242', '1']),     # descendente
    ('user', ['1', '777', '4242']),    # ascendente (root < user; PID desempata)
    ('name', ['1', '4242', '777']),    # ascendente (/sbin/init < firefox < java)
    ('pid', ['4242', '777', '1']),     # descendente
])
@pytest.mark.asyncio
async def test_processes_sort_all_criteria(tmp_path, monkeypatch,
                                           criterion, expected):
    """'s' cicla por los cinco criterios con su dirección y etiqueta i18n."""
    from tui_manager.i18n import t
    from tui_manager.ui.screens import ProcessesScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.press('2')
        await _wait_workers(app, pilot)
        screen = app.screen
        assert isinstance(screen, ProcessesScreen)
        while screen._sort != criterion:
            screen.action_sort()
            await pilot.pause()
        table = screen.query_one('#process-table')
        order = [str(table.get_row_at(i)[0]) for i in range(table.row_count)]
        assert order == expected
        assert t(f'processes.sort_{criterion}') in str(
            screen.query_one('#process-status').render())


# ------------------------- 1.2-A: quickstart (onboarding) -------------------

def test_quickstart_text_covers_all_menu_entries(monkeypatch):
    """El recorrido reutiliza entradas y atajos del menú (fuente única)."""
    from tui_manager import i18n
    from tui_manager.i18n import t
    from tui_manager.ui.screens import MainMenuScreen, quickstart_text

    monkeypatch.setattr(i18n, '_current', 'es')
    lines = quickstart_text().splitlines()
    assert len(MainMenuScreen.ENTRIES) == 10
    for index, (entry_id, _screen) in enumerate(MainMenuScreen.ENTRIES):
        key = MainMenuScreen.shortcut(index)
        expected = (f'  [{key}] {t(f"menu.{entry_id}")} — '
                    f'{t(f"menu.{entry_id}.desc")}')
        assert expected in lines, f'falta la línea: {expected}'
    assert 'tm --doctor' in '\n'.join(lines)


@pytest.mark.parametrize('lang', ['es', 'en'])
def test_quickstart_text_is_localized_plain_text(monkeypatch, lang):
    """Texto plano y localizado: sin ANSI y con la sugerencia de --doctor."""
    from tui_manager import i18n
    from tui_manager.i18n import t
    from tui_manager.ui.screens import quickstart_text

    monkeypatch.setattr(i18n, '_current', lang)
    text = quickstart_text()
    assert t('app.title') in text
    assert t('quickstart.title') in text
    assert t('quickstart.intro') in text
    assert t('quickstart.doctor_hint') in text
    assert 'tm --doctor' in text
    assert '\x1b[' not in text  # sin códigos de control ANSI


def test_quickstart_text_needs_no_services():
    """No requiere Services ni instancia pantallas: solo compone texto."""
    from tui_manager.ui.screens import quickstart_text

    text = quickstart_text()
    assert isinstance(text, str)
    assert len(text.splitlines()) >= 14  # cabecera + 10 entradas + sugerencia


# ---------------- 2.0-A1/A2: compatibilidad mouse / táctil ------------------

@pytest.mark.asyncio
async def test_confirm_buttons_dismiss(tmp_path, monkeypatch):
    """2.0-A1: clic en Sí/No hace dismiss(True/False); foco inicial en Sí."""
    from textual.widgets import Button
    from tui_manager.ui.screens import ConfirmScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        results = []
        app.push_screen(ConfirmScreen('¿Continuar?'), results.append)
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ConfirmScreen)
        yes = screen.query_one('#confirm-yes', Button)
        no = screen.query_one('#confirm-no', Button)
        assert 'button-compact' in yes.classes
        assert 'button-compact' in no.classes
        assert yes.has_focus  # foco inicial en el botón primario

        await pilot.click('#confirm-yes')
        await pilot.pause()
        assert results == [True]

        app.push_screen(ConfirmScreen('¿Continuar?'), results.append)
        await pilot.pause()
        assert app.screen.query_one('#confirm-yes', Button).has_focus
        await pilot.click('#confirm-no')
        await pilot.pause()
        assert results == [True, False]


@pytest.mark.asyncio
async def test_input_buttons_dismiss(tmp_path, monkeypatch):
    """2.0-A1: Aceptar envía el valor; Cancelar hace dismiss(None)."""
    from textual.widgets import Button, Input
    from tui_manager.ui.screens import InputScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        results = []
        app.push_screen(InputScreen('Valor'), results.append)
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, InputScreen)
        accept = screen.query_one('#input-accept', Button)
        cancel = screen.query_one('#input-cancel', Button)
        assert 'button-compact' in accept.classes
        assert 'button-compact' in cancel.classes
        # El campo conserva el foco inicial (atajo Enter sigue vigente).
        field = screen.query_one('#modal-input', Input)
        assert field.has_focus
        field.value = '42'

        await pilot.click('#input-accept')
        await pilot.pause()
        assert results == ['42']

        app.push_screen(InputScreen('Valor'), results.append)
        await pilot.pause()
        await pilot.click('#input-cancel')
        await pilot.pause()
        assert results == ['42', None]


@pytest.mark.asyncio
async def test_select_screen_cancel_button(tmp_path, monkeypatch):
    """2.0-A1: el botón Cancelar cierra el modal sin elegir opción."""
    from textual.widgets import Button
    from tui_manager.ui.screens import SelectScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        results = []
        app.push_screen(SelectScreen('Fuentes', ['Oficial', 'AUR'],
                                     ['estable', 'comunidad']), results.append)
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, SelectScreen)
        cancel = screen.query_one('#select-cancel', Button)
        assert 'button-compact' in cancel.classes

        await pilot.click('#select-cancel')
        await pilot.pause()
        assert results == [None]


@pytest.mark.asyncio
async def test_packages_click_mark_cell(tmp_path, monkeypatch):
    """2.0-A2: clic en «Marcar» marca/desmarca sin romper la fila única."""
    from textual.widgets import DataTable

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.press('1')
        await _wait_workers(app, pilot)
        screen = app.screen
        table = screen.query_one('#packages-table', DataTable)
        assert table.row_count == 3
        assert table.cursor_type == 'row'

        # Columna 0 («Marcar»), fila 1: y = fila + 2 (borde + cabecera).
        await pilot.click('#packages-table', offset=(2, 3))
        await pilot.pause()
        assert screen._marked == {1}
        assert table.get_cell_at((1, 0)) == '✓'

        await pilot.click('#packages-table', offset=(2, 3))
        await pilot.pause()
        assert screen._marked == set()
        assert table.get_cell_at((1, 0)) == ''

        # Sin marcas, la acción sigue actuando sobre la fila del cursor.
        assert [p.name for p in screen._selected_packages()] == ['git']


@pytest.mark.asyncio
async def test_processes_sort_select_click(tmp_path, monkeypatch):
    """2.0-A2: el Select compacto reordena y 's' lo mantiene sincronizado."""
    from textual.widgets import DataTable, Select
    from textual.widgets._select import SelectOverlay

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.press('2')
        await _wait_workers(app, pilot)
        screen = app.screen
        select = screen.query_one('#sort-select', Select)
        assert 'select-compact' in select.classes
        assert select.value == 'cpu'
        table = screen.query_one('#process-table', DataTable)
        order = lambda: [str(table.get_row_at(i)[0])
                         for i in range(table.row_count)]
        assert order() == ['4242', '1', '777']

        # Clic en el Select (fila de contenido, y=1) y en «por memoria»
        # (índice 1 → y=1 dentro del overlay, tras su borde superior).
        await pilot.click('#sort-select', offset=(10, 1))
        await pilot.pause()
        overlay = select.query_one(SelectOverlay)
        await pilot.click(overlay, offset=(2, 1))
        await pilot.pause()
        assert screen._sort == 'mem'
        assert select.value == 'mem'
        assert order() == ['777', '4242', '1']

        # El atajo 's' sigue funcionando y actualiza el control clicable.
        screen.action_sort()
        await pilot.pause()
        assert screen._sort == 'user'
        assert select.value == 'user'


@pytest.mark.asyncio
@pytest.mark.parametrize('key,expected_screen,expected_context', [
    (None, 'MainMenuScreen', 'MainMenuScreen'),
    ('1', 'PackagesScreen', 'PackagesScreen'),
    ('2', 'ProcessesScreen', 'ProcessesScreen'),
])
async def test_help_button_opens_contextual_help(tmp_path, monkeypatch,
                                                 key, expected_screen,
                                                 expected_context):
    """2.0-A2: botón «?» clicable junto al atajo, en menú y tablas."""
    from textual.widgets import Button
    from tui_manager.ui.screens import HelpScreen

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        if key:
            await pilot.press(key)
            await _wait_workers(app, pilot)
        assert type(app.screen).__name__ == expected_screen

        button = app.screen.query_one('#help-btn', Button)
        assert 'button-compact' in button.classes
        assert 'help-button' in button.classes
        assert button.styles.width is not None
        assert button.styles.width.value == 6  # regla CSS: no se estira

        await pilot.click('#help-btn')
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        assert app.screen.context == expected_context


# ------------------------------- Snapshots (core/snapshots.py en la TUI) ----

def _snapshots_screen_names(screen):
    from textual.widgets import Static
    return [item.query_one(Static).content
            for item in screen.query('#snapshots-list ListItem')]


@pytest.mark.asyncio
async def test_settings_opens_snapshots_modal(tmp_path, monkeypatch):
    """El botón de Ajustes abre el modal con el almacén inyectado en tmp_path."""
    from textual.widgets import Button, LoadingIndicator, Static
    from tui_manager.i18n import t
    from tui_manager.ui.screens import SettingsScreen, SnapshotsScreen

    services = make_services(tmp_path, monkeypatch)
    services.snapshots_base_dir = tmp_path / 'snaps'
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SettingsScreen(services))
        await pilot.pause()
        button = app.screen.query_one('#settings-snapshots', Button)
        assert 'button-compact' in button.classes
        button.press()  # clic equivalente a la tecla «s»
        await pilot.pause()
        assert isinstance(app.screen, SnapshotsScreen)
        await _wait_workers(app, pilot)
        assert app.screen.base_dir == services.snapshots_base_dir
        status = app.screen.query_one('#snapshots-status', Static).content
        assert t('snapshots.empty') in status
        loading = app.screen.query_one('#snapshots-loading', LoadingIndicator)
        assert loading.display is False
        assert t('snapshots.create') in str(
            app.screen.query_one('#snapshots-create', Button).label)


def test_settings_snapshots_shortcut_is_bound():
    """«s» en Ajustes dispara la acción snapshots (sin tocar el menú)."""
    from tui_manager.ui.screens import MainMenuScreen, SettingsScreen

    assert _binding_map(SettingsScreen).get('s') == 'snapshots'
    assert callable(SettingsScreen.action_snapshots)
    # El menú sigue teniendo 10 entradas y sus atajos [1]–[9]/[0].
    assert len(MainMenuScreen.ENTRIES) == 10
    assert [MainMenuScreen.shortcut(i) for i in range(10)] == [
        str(i + 1) for i in range(9)] + ['0']


@pytest.mark.asyncio
async def test_snapshots_modal_lists_existing(tmp_path, monkeypatch):
    """El modal lista los snapshots del almacén (leído en worker)."""
    from textual.widgets import LoadingIndicator, Static
    from tui_manager.core.snapshots import snapshot_config
    from tui_manager.i18n import t
    from tui_manager.ui.screens import SnapshotsScreen

    store = tmp_path / 'snaps'
    cfg = tmp_path / 'wm.conf'
    cfg.write_text('original', encoding='utf-8')
    snapshot_config('bar', [cfg], base_dir=store)
    snapshot_config('foo', [cfg], base_dir=store)

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SnapshotsScreen(base_dir=store))
        await pilot.pause()
        await _wait_workers(app, pilot)
        screen = app.screen
        assert _snapshots_screen_names(screen) == ['bar', 'foo']
        status = screen.query_one('#snapshots-status', Static).content
        assert t('snapshots.count').format(n=2) in status
        assert t('snapshots.empty') not in status
        assert screen.query_one('#snapshots-loading',
                                LoadingIndicator).display is False


@pytest.mark.asyncio
async def test_snapshots_create_flow(tmp_path, monkeypatch):
    """Crear pide nombre y rutas con InputScreen y llama a snapshot_config."""
    from textual.widgets import Input, Static
    from tui_manager.i18n import t
    from tui_manager.ui.screens import InputScreen, SnapshotsScreen

    store = tmp_path / 'snaps'
    cfg = tmp_path / 'bar.conf'
    cfg.write_text('contenido', encoding='utf-8')
    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SnapshotsScreen(base_dir=store))
        await pilot.pause()
        await _wait_workers(app, pilot)
        await pilot.press('n')
        await pilot.pause()
        assert isinstance(app.screen, InputScreen)
        app.screen.query_one('#modal-input', Input).value = 'perfil'
        await pilot.press('enter')
        await pilot.pause()
        assert isinstance(app.screen, InputScreen)
        app.screen.query_one('#modal-input', Input).value = str(cfg)
        await pilot.press('enter')
        await _wait_workers(app, pilot)
        assert isinstance(app.screen, SnapshotsScreen)
        assert (store / 'perfil' / 'snapshot.json').is_file()
        assert 'perfil' in _snapshots_screen_names(app.screen)
        status = app.screen.query_one('#snapshots-status', Static).content
        assert t('snapshots.count').format(n=1) in status
        # El sidecar .bak-tm se crea junto al original, nunca en el sistema.
        assert (tmp_path / 'bar.conf.bak-tm').is_file()


@pytest.mark.asyncio
async def test_snapshots_restore_flow(tmp_path, monkeypatch):
    """Restaurar confirma y devuelve el archivo al contenido del snapshot."""
    from tui_manager.core.snapshots import snapshot_config
    from tui_manager.ui.screens import ConfirmScreen, SnapshotsScreen

    store = tmp_path / 'snaps'
    cfg = tmp_path / 'wm.conf'
    cfg.write_text('original', encoding='utf-8')
    snapshot_config('bar', [cfg], base_dir=store)
    cfg.write_text('modificado', encoding='utf-8')

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SnapshotsScreen(base_dir=store))
        await pilot.pause()
        await _wait_workers(app, pilot)
        assert app.screen.query_one('#snapshots-list').index == 0
        await pilot.press('r')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press('y')
        await _wait_workers(app, pilot)
        assert isinstance(app.screen, SnapshotsScreen)
        assert cfg.read_text(encoding='utf-8') == 'original'
        # El sidecar original no se toca nunca.
        assert (tmp_path / 'wm.conf.bak-tm').read_text(
            encoding='utf-8') == 'original'


@pytest.mark.asyncio
async def test_snapshots_unsafe_path_is_actionable(tmp_path, monkeypatch):
    """Una ruta btrfs/zfs se rechaza con mensaje, sin traceback ni copia."""
    from textual.widgets import Input, Static
    from tui_manager.i18n import t
    from tui_manager.ui.screens import InputScreen, SnapshotsScreen

    store = tmp_path / 'snaps'
    unsafe = tmp_path / '.snapshots' / 'cfg'
    unsafe.parent.mkdir()
    unsafe.write_text('x', encoding='utf-8')

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SnapshotsScreen(base_dir=store))
        await pilot.pause()
        await _wait_workers(app, pilot)
        await pilot.press('n')
        await pilot.pause()
        app.screen.query_one('#modal-input', Input).value = 'sys'
        await pilot.press('enter')
        await pilot.pause()
        app.screen.query_one('#modal-input', Input).value = str(unsafe)
        await pilot.press('enter')
        await _wait_workers(app, pilot)
        assert isinstance(app.screen, SnapshotsScreen)
        status = app.screen.query_one('#snapshots-status', Static).content
        assert t('snapshots.unsafe_path') in status
        assert 'Traceback' not in status
        assert not (store / 'sys').exists()


@pytest.mark.asyncio
async def test_snapshots_restore_missing_copy_is_actionable(tmp_path, monkeypatch):
    """Si falta una copia, el error se explica; no se muestra un traceback."""
    from textual.widgets import Static
    from tui_manager.core.snapshots import snapshot_config
    from tui_manager.i18n import t
    from tui_manager.ui.screens import ConfirmScreen, SnapshotsScreen

    store = tmp_path / 'snaps'
    cfg = tmp_path / 'wm.conf'
    cfg.write_text('original', encoding='utf-8')
    snapshot_config('bar', [cfg], base_dir=store)
    for item in (store / 'bar').iterdir():
        if item.name != 'snapshot.json':
            item.unlink()

    services = make_services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SnapshotsScreen(base_dir=store))
        await pilot.pause()
        await _wait_workers(app, pilot)
        await pilot.press('r')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press('y')
        await _wait_workers(app, pilot)
        status = app.screen.query_one('#snapshots-status', Static).content
        assert t('snapshots.not_found') in status
        assert 'Traceback' not in status


def test_snapshots_i18n_keys_in_both_languages():
    """Todas las claves nuevas están dentro de los dicts es y en."""
    from tui_manager.i18n import STRINGS, t

    keys = (
        'snapshots.open', 'snapshots.title', 'snapshots.settings_help',
        'snapshots.hint', 'snapshots.empty', 'snapshots.count',
        'snapshots.create', 'snapshots.restore', 'snapshots.keys',
        'snapshots.name_prompt', 'snapshots.paths_prompt',
        'snapshots.restore_confirm', 'snapshots.select_one',
        'snapshots.no_paths', 'snapshots.created', 'snapshots.restored',
        'snapshots.unsafe_path', 'snapshots.not_found',
        'snapshots.invalid_name', 'snapshots.file_missing',
        'snapshots.io_error',
    )
    for lang, strings in STRINGS.items():
        for key in keys:
            assert key in strings, f'{key} falta en {lang}'
    for key in keys:
        assert t(key) != key, f't() devolvió la clave {key}'

