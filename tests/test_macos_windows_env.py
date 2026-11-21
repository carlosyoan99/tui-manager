"""
Tests 100% simulados del soporte de entorno macOS / Windows.

Ni un solo comando de macOS o Windows se ejecuta en estos hosts:
``platform.system``, ``shutil.which`` y ``subprocess.run`` se sustituyen por
stubs. Valida los EnvironmentAdapters y SystemControl en cualquier SO.
"""

import os
import platform
import shutil
import subprocess

import pytest

# Mismo objeto de módulo que usan environment.py y system_control.py.
import tui_manager.core.environment as env_mod  # noqa: F401
import tui_manager.core.system_control as sc_mod  # noqa: F401
from tui_manager.core.environment import (
    Capability,
    EnvironmentDetector,
    MacOSEnvironmentAdapter,
    WindowsEnvironmentAdapter,
    launch_or_focus,
)
from tui_manager.core.system_control import SystemControl


def _no_real_run(cmd, *args, **kwargs):
    raise AssertionError(f'Comando real intentado en test: {list(cmd)}')


@pytest.fixture(autouse=True)
def no_real_commands(monkeypatch):
    """Trampa global: ningún test puede ejecutar un binario del host."""
    monkeypatch.setattr(subprocess, 'run', _no_real_run)


@pytest.fixture
def simulated_os(monkeypatch):
    """Fija SO y PATH: '/mock/<tool>' solo para las herramientas dadas."""
    def _set(system, tools=()):
        monkeypatch.setattr(platform, 'system', lambda: system)
        present = set(tools)
        monkeypatch.setattr(
            shutil, 'which',
            lambda cmd, *a, **k: f'/mock/{cmd}' if cmd in present else None)
    return _set


@pytest.fixture
def cmd_recorder(no_real_commands, monkeypatch):
    """Captura subprocess.run sin ejecutar nada: devuelve (calls, state)."""
    calls = []
    state = {'rc': 0, 'out': '', 'err': ''}

    def _run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, state['rc'],
                                           state['out'], state['err'])

    monkeypatch.setattr(subprocess, 'run', _run)
    return calls, state


class _Env:
    """Adapter mínimo para SystemControl, con capacidades explícitas."""

    def __init__(self, *caps):
        self._caps = set(caps)

    def supports(self, cap):
        return cap in self._caps

    def capabilities(self):
        return self._caps

    def lock_screen(self):
        return True

    def launch_app(self, command):
        return True


def _full_env():
    return _Env(Capability.LOCK_SCREEN, Capability.LAUNCH_APP)


def _clear_environment(monkeypatch):
    """Aísla detect() de TERMUX/XDG/WAYLAND del host."""
    monkeypatch.setattr(os, 'environ', {})


# ---------------- Detección por plataforma ----------------

def test_detect_macos(monkeypatch, simulated_os):
    simulated_os('Darwin', ('open',))
    _clear_environment(monkeypatch)
    adapter = EnvironmentDetector.detect()
    assert type(adapter) is MacOSEnvironmentAdapter
    assert adapter.name == 'macos'


def test_detect_windows(monkeypatch, simulated_os):
    simulated_os('Windows', ('cmd',))
    _clear_environment(monkeypatch)
    adapter = EnvironmentDetector.detect()
    assert type(adapter) is WindowsEnvironmentAdapter
    assert adapter.name == 'windows'


def test_detect_so_antes_de_wm_y_fallback(monkeypatch, simulated_os):
    """Darwin manda aunque haya variables de WM/DE de Linux."""
    simulated_os('Darwin', ())
    monkeypatch.setattr(os, 'environ', {
        'HYPRLAND_INSTANCE_SIGNATURE': 'sig',
        'XDG_CURRENT_DESKTOP': 'KDE',
    })
    assert type(EnvironmentDetector.detect()) is MacOSEnvironmentAdapter


def test_get_info_en_simulado(monkeypatch, simulated_os, cmd_recorder):
    simulated_os('Windows', ('cmd', 'reg'))
    _clear_environment(monkeypatch)
    info = EnvironmentDetector.get_info()
    assert info['name'] == 'windows'
    assert 'LAUNCH_APP' in info['capabilities']


# ---------------- macOS: capacidades y acciones ----------------

def test_macos_capabilities_por_herramienta(simulated_os):
    simulated_os('Darwin', ('open', 'osascript', 'sqlite3',
                            'defaults', 'pmset'))
    adapter = MacOSEnvironmentAdapter()
    assert adapter.capabilities() == {
        Capability.LAUNCH_APP, Capability.LIST_WINDOWS,
        Capability.SET_WALLPAPER, Capability.SET_DARK_MODE,
        Capability.LOCK_SCREEN,
    }
    assert adapter.supports(Capability.SET_DARK_MODE)


def test_macos_capabilities_sin_herramientas(simulated_os):
    simulated_os('Darwin', ())
    assert MacOSEnvironmentAdapter().capabilities() == set()


def test_macos_wallpaper_osascript(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Darwin', ('osascript',))
    assert MacOSEnvironmentAdapter().set_wallpaper('/tmp/fondo.png') is True
    assert calls == [[
        'osascript', '-e',
        'tell application "System Events" to set picture of every desktop '
        'to "/tmp/fondo.png"',
    ]]


def test_macos_wallpaper_sqlite_fallback(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Darwin', ('sqlite3',))
    db = os.path.expanduser('~/Library/Application Support/Dock/desktoppicture.db')
    assert MacOSEnvironmentAdapter().set_wallpaper('/tmp/fondo.png') is True
    assert calls[0] == ['sqlite3', db, "UPDATE data SET value='/tmp/fondo.png';"]
    assert calls[1] == ['killall', 'Dock']


def test_macos_wallpaper_falla_con_codigo(simulated_os, cmd_recorder):
    _, state = cmd_recorder
    state.update(rc=2, err='AppleScript error')
    simulated_os('Darwin', ('osascript',))
    assert MacOSEnvironmentAdapter().set_wallpaper('/tmp/fondo.png') is False


def test_macos_dark_mode(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Darwin', ('defaults',))
    adapter = MacOSEnvironmentAdapter()
    assert adapter.set_dark_mode(True) is True
    assert adapter.set_dark_mode(False) is True
    assert calls == [
        ['defaults', 'write', '-g', 'AppleInterfaceStyle', '-string', 'Dark'],
        ['defaults', 'delete', '-g', 'AppleInterfaceStyle'],
    ]


def test_macos_launch_y_focus(simulated_os, cmd_recorder):
    calls, state = cmd_recorder
    simulated_os('Darwin', ('open', 'osascript'))
    adapter = MacOSEnvironmentAdapter()
    assert adapter.launch_app('Safari') is True
    assert calls[-1] == ['open', '-a', 'Safari']

    state['out'] = 'Finder, Safari\n'
    assert launch_or_focus(adapter, 'Safari')['action'] == 'focused'
    assert calls[-1] == ['open', '-a', 'Safari']


def test_macos_launch_or_focus_lanza_si_no_hay_ventana(simulated_os,
                                                       cmd_recorder):
    calls, state = cmd_recorder
    simulated_os('Darwin', ('open', 'osascript'))
    state['out'] = 'Finder\n'
    assert launch_or_focus(MacOSEnvironmentAdapter(), 'Safari')['action'] == 'launched'
    assert calls[-1] == ['open', '-a', 'Safari']


def test_macos_lock_screen(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Darwin', ('pmset',))
    assert MacOSEnvironmentAdapter().lock_screen() is True
    assert calls == [['pmset', 'displaysleepnow']]


# ---------------- Windows: capacidades y acciones ----------------

def test_windows_capabilities_por_herramienta(simulated_os):
    simulated_os('Windows', ('cmd', 'powershell', 'reg',
                             'tasklist', 'rundll32'))
    adapter = WindowsEnvironmentAdapter()
    assert adapter.capabilities() == {
        Capability.LAUNCH_APP, Capability.SET_WALLPAPER,
        Capability.SET_DARK_MODE, Capability.LIST_WINDOWS,
        Capability.LOCK_SCREEN,
    }
    assert adapter.supports(Capability.SET_WALLPAPER)


def test_windows_wallpaper_powershell(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Windows', ('powershell',))
    assert WindowsEnvironmentAdapter().set_wallpaper(r'C:\wall.png') is True
    cmd = calls[0]
    assert cmd[:2] == ['powershell', '-NoProfile']
    assert 'SystemParametersInfo' in cmd[3]
    assert r'C:\wall.png' in cmd[3]


def test_windows_wallpaper_reg_fallback(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Windows', ('reg',))
    assert WindowsEnvironmentAdapter().set_wallpaper(r'C:\wall.png') is True
    assert calls[0] == [
        'reg', 'add', r'HKCU\Control Panel\Desktop', '/v', 'Wallpaper',
        '/t', 'REG_SZ', '/d', r'C:\wall.png', '/f',
    ]
    assert calls[1] == ['rundll32', 'user32.dll,UpdatePerUserSystemParameters']


def test_windows_dark_mode(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Windows', ('reg',))
    adapter = WindowsEnvironmentAdapter()
    assert adapter.set_dark_mode(True) is True
    assert adapter.set_dark_mode(False) is True
    key = (r'HKCU\Software\Microsoft\Windows\CurrentVersion'
           r'\Themes\Personalize')
    assert calls[0] == [
        'reg', 'add', key, '/v', 'AppsUseLightTheme',
        '/t', 'REG_DWORD', '/d', '0', '/f',
    ]
    assert calls[1][-3:-1] == ['/d', '1']


def test_windows_launch_y_listado(simulated_os, cmd_recorder):
    calls, state = cmd_recorder
    simulated_os('Windows', ('cmd', 'tasklist'))
    adapter = WindowsEnvironmentAdapter()
    assert adapter.launch_app('notepad.exe') is True
    assert calls[-1] == ['cmd', '/c', 'start', '', 'notepad.exe']

    state['out'] = '"firefox.exe","1234","Console","1"\n'
    assert adapter.list_windows() == [
        {'pid': 1234, 'class': 'firefox.exe', 'title': 'firefox.exe'},
    ]


def test_windows_focus_y_launch_or_focus(simulated_os, cmd_recorder):
    calls, state = cmd_recorder
    simulated_os('Windows', ('cmd', 'tasklist', 'powershell'))
    adapter = WindowsEnvironmentAdapter()
    assert adapter.focus_window('firefox.exe') is True
    assert calls[0][0] == 'powershell'
    assert 'AppActivate' in calls[0][3]

    state['out'] = '"firefox.exe","1234","Console","1"\n'
    assert launch_or_focus(adapter, 'firefox.exe')['action'] == 'focused'


def test_windows_lock_screen(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Windows', ('rundll32',))
    assert WindowsEnvironmentAdapter().lock_screen() is True
    assert calls == [['rundll32', 'user32.dll,LockWorkStation']]


# ---------------- SystemControl en macOS ----------------

def test_macos_availability_completa(simulated_os):
    simulated_os('Darwin', ('pmset', 'osascript', 'shutdown',
                            'brightness', 'systemsetup'))
    avail = SystemControl(environment=_full_env()).availability()
    assert avail == {k: None for k in avail}


def test_macos_availability_degrada(simulated_os):
    simulated_os('Darwin', ())
    avail = SystemControl(environment=_Env()).availability()
    assert all(isinstance(v, str) and v for v in avail.values())
    assert avail['lock'] == 'pmset/lock_screen (entorno)'
    assert avail['timezone'] == 'systemsetup'
    assert avail['launch'] == 'launch_app (entorno)'


def test_macos_system_actions(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Darwin', ('shutdown', 'pmset', 'osascript', 'defaults',
                            'brightness', 'systemsetup'))
    control = SystemControl()

    assert control.reboot() == (True, '')
    assert calls[-1] == ['shutdown', '-r', 'now']
    assert control.shutdown() == (True, '')
    assert calls[-1] == ['shutdown', '-h', 'now']
    assert control.suspend() == (True, '')
    assert calls[-1] == ['pmset', 'sleepnow']
    assert control.logout() == (True, '')
    assert calls[-1][:2] == ['osascript', '-e']
    assert control.lock() == (True, '')
    assert calls[-1] == ['pmset', 'displaysleepnow']
    assert control.brightness_step(1) == (True, '')
    assert calls[-1] == ['brightness', '0.1']
    assert control.brightness_step(-1) == (True, '')
    assert calls[-1] == ['brightness', '-0.1']
    assert control.set_dark_mode(True) == (True, '')
    assert calls[-1] == ['defaults', 'write', '-g',
                         'AppleInterfaceStyle', '-string', 'Dark']
    assert control.set_dark_mode(False) == (True, '')
    assert calls[-1] == ['defaults', 'delete', '-g', 'AppleInterfaceStyle']


def test_macos_timezone(simulated_os, cmd_recorder):
    calls, state = cmd_recorder
    simulated_os('Darwin', ('systemsetup',))
    control = SystemControl()
    assert control.set_timezone('Europe/Madrid') == (True, '')
    assert calls[-1] == ['systemsetup', '-settimezone', 'Europe/Madrid']

    state['out'] = 'Europe/Madrid\nUTC\n'
    ok, zones = control.list_timezones()
    assert ok is True and zones == ['Europe/Madrid', 'UTC']


# ---------------- SystemControl en Windows ----------------

def test_windows_availability_completa(simulated_os):
    simulated_os('Windows', ('shutdown', 'rundll32', 'powershell',
                             'powercfg', 'tzutil'))
    avail = SystemControl(environment=_full_env()).availability()
    assert avail == {k: None for k in avail}


def test_windows_availability_degrada(simulated_os):
    simulated_os('Windows', ())
    avail = SystemControl(environment=_Env()).availability()
    assert all(isinstance(v, str) and v for v in avail.values())
    assert avail['lock'] == 'rundll32/lock_screen (entorno)'
    assert avail['timezone'] == 'tzutil'
    assert avail['launch'] == 'launch_app (entorno)'


def test_windows_system_actions(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    simulated_os('Windows', ('shutdown', 'rundll32', 'powershell',
                             'reg', 'powercfg', 'tzutil'))
    control = SystemControl()

    assert control.reboot() == (True, '')
    assert calls[-1] == ['shutdown', '/r', '/t', '0']
    assert control.shutdown() == (True, '')
    assert calls[-1] == ['shutdown', '/s', '/t', '0']
    assert control.suspend() == (True, '')
    assert calls[-1] == ['rundll32', 'powrprof.dll,SetSuspendState', '0,1,0']
    assert control.logout() == (True, '')
    assert calls[-1] == ['shutdown', '/l']
    assert control.lock() == (True, '')
    assert calls[-1] == ['rundll32', 'user32.dll,LockWorkStation']
    assert control.brightness_step(1) == (True, '')
    assert 'WmiSetBrightness' in calls[-1][3] and '+10' in calls[-1][3]
    assert control.set_dark_mode(True) == (True, '')
    assert calls[-1][:3] == ['reg', 'add', (r'HKCU\Software\Microsoft'
                                            r'\Windows\CurrentVersion'
                                            r'\Themes\Personalize')]
    assert calls[-1][-3:-1] == ['/d', '0']
    assert control.set_timezone('Pacific Standard Time') == (True, '')
    assert calls[-1] == ['tzutil', '/s', 'Pacific Standard Time']
    assert control.power_profiles()[0] is True
    assert calls[-1] == ['powercfg', '/list']
    assert control.set_power_profile('scheme-guid') == (True, '')
    assert calls[-1] == ['powercfg', '/setactive', 'scheme-guid']


def test_windows_timezones_y_perfil(simulated_os, cmd_recorder):
    calls, state = cmd_recorder
    simulated_os('Windows', ('tzutil',))
    state['out'] = 'UTC\nPacific Standard Time\n'
    ok, zones = SystemControl().list_timezones()
    assert ok is True and zones == ['UTC', 'Pacific Standard Time']
    assert calls[-1] == ['tzutil', '/l']


# ---------------- Degradación sin herramientas ----------------

def test_acciones_degradan_sin_herramientas(simulated_os, cmd_recorder):
    calls, _ = cmd_recorder
    for system in ('Darwin', 'Windows'):
        simulated_os(system, ())
        control = SystemControl()
        results = (
            control.reboot(), control.shutdown(), control.suspend(),
            control.logout(), control.lock(), control.brightness_step(1),
            control.set_dark_mode(True), control.set_timezone('UTC'),
        )
        for ok, reason in results:
            assert ok is False
            assert isinstance(reason, str) and reason
    assert calls == []  # ningún comando real ni simulado llegó a ejecutarse
