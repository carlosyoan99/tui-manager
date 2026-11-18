"""
Tests simulados de detección de SO/distribución, selección de adapters,
i18n, config, packs de tema, plano de entorno y control del sistema.
"""

import os
import platform

import pytest

from tui_manager.core.distribution import DistributionDetector, DistributionError
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.debian_adapter import DebianAdapter
from tui_manager.core.arch_adapter import ArchAdapter
from tui_manager.core.void_adapter import VoidAdapter
from tui_manager.core.termux_adapter import TermuxAdapter
from tui_manager.core.freebsd_adapter import FreeBSDAdapter
from tui_manager.core.pkgsrc_adapter import PkgsrcAdapter

from tui_manager.i18n import t, set_language, get_language, available_languages


# ---------------- Detección de distribución ----------------

def test_detect_termux(monkeypatch):
    monkeypatch.setenv('TERMUX_VERSION', '0.118.0')
    assert DistributionDetector.detect() == 'termux'
    assert DistributionDetector.is_termux() is True


def test_detect_debian(monkeypatch):
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setenv('PREFIX', '/usr')
    monkeypatch.setattr(os.path, 'exists',
                        lambda p: p == '/etc/debian_version')
    assert DistributionDetector.detect() == 'debian'


def _no_lsb_release(monkeypatch):
    """Fuerza a que lsb_release no exista, para tests sin depender del host."""
    import subprocess
    def fake_run(*args, **kwargs):
        raise FileNotFoundError('lsb_release')
    monkeypatch.setattr(subprocess, 'run', fake_run)


def test_detect_freebsd_kernel_fallback(monkeypatch):
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setenv('PREFIX', '/usr')
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    monkeypatch.setattr(platform, 'system', lambda: 'FreeBSD')
    _no_lsb_release(monkeypatch)
    assert DistributionDetector.detect() == 'freebsd'


def test_detect_failure(monkeypatch):
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setenv('PREFIX', '/usr')
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    monkeypatch.setattr(platform, 'system', lambda: 'Plan9')
    _no_lsb_release(monkeypatch)
    with pytest.raises(DistributionError):
        DistributionDetector.detect()


def test_supported_includes_user_platforms():
    supported = DistributionDetector.get_supported_distributions()
    for distro in ('debian', 'arch', 'cachyos', 'void', 'termux', 'freebsd'):
        assert distro in supported


# ---------------- Selección de adapter ----------------

@pytest.mark.parametrize('distro,adapter_class', [
    ('debian', DebianAdapter), ('ubuntu', DebianAdapter),
    ('arch', ArchAdapter), ('cachyos', ArchAdapter), ('manjaro', ArchAdapter),
    ('void', VoidAdapter), ('termux', TermuxAdapter),
    ('freebsd', FreeBSDAdapter), ('netbsd', PkgsrcAdapter),
])
def test_package_manager_selection(distro, adapter_class):
    pm = PackageManager(distribution=distro)
    assert type(pm.adapter) is adapter_class


def test_package_manager_unknown_falls_back_to_debian():
    pm = PackageManager(distribution='plan9')
    assert type(pm.adapter) is DebianAdapter


# ---------------- i18n ----------------

def test_i18n_es_default():
    set_language('es')
    assert t('menu.packages') == 'Aplicaciones'
    assert t('menu.packages.desc') == 'Ver, buscar, instalar y desinstalar'


def test_i18n_en():
    set_language('en')
    assert t('menu.packages') == 'Applications'
    set_language('es')


def test_i18n_placeholders():
    set_language('es')
    assert t('packages.install_ok', name='curl') == 'curl instalado'


def test_i18n_unknown_key_returns_key():
    assert t('key.that.does.not.exist') == 'key.that.does.not.exist'


def test_i18n_invalid_language_falls_back():
    assert set_language('xx') == 'es'
    assert get_language() == 'es'
    assert set(available_languages()) == {'es', 'en'}


# ---------------- Config ----------------

def test_config_roundtrip(tmp_path):
    from tui_manager.core.config import Config
    cfg = Config(config_file=str(tmp_path / 'config.yaml'))
    cfg.set('language', 'en')
    cfg.set('refresh_interval', 5)
    cfg2 = Config(config_file=str(tmp_path / 'config.yaml'))
    assert cfg2.get('language') == 'en'
    assert cfg2.get('refresh_interval') == 5
    assert cfg2.get_theme() == 'dark'  # default intacto


def test_config_defaults_include_language():
    from tui_manager.core.config import Config
    cfg = Config(config_file='/nonexistent/path/config.yaml')
    assert cfg.get('language', 'es') == 'es'


# ---------------- Packs de tema ----------------

def test_list_packs_includes_five_builtins():
    from tui_manager.core.theme_packs import list_packs
    packs = list_packs()
    names = {p.name for p in packs}
    assert {'tokyo-night', 'catppuccin-mocha', 'gruvbox-dark',
            'nord', 'everforest'} <= names
    for pack in packs:
        assert pack.palette, f"{pack.name} sin paleta"


def test_get_pack_by_name():
    from tui_manager.core.theme_packs import get_pack
    pack = get_pack('tokyo-night')
    assert pack is not None
    assert pack.dark is True
    assert pack.palette['bg'] == '#1a1b26'


def test_apply_pack_generates_terminal_theme(tmp_path, monkeypatch):
    """apply_pack genera archivo de tema y conecta include con backup .bak-tm."""
    from tui_manager.core.theme_packs import apply_pack, ThemePack, _connect_include

    monkeypatch.setenv('HOME', str(tmp_path))
    cfg_dir = tmp_path / '.config' / 'alacritty'
    cfg_dir.mkdir(parents=True)
    cfg = cfg_dir / 'alacritty.toml'
    cfg.write_text('[font]\nsize = 12\n')

    pack = ThemePack(
        name='test',
        palette={'bg': '#101010', 'fg': '#eeeeee'},
        surfaces={'alacritty': {'palette': {'bg': '#101010', 'fg': '#eeeeee'}}},
    )
    result = apply_pack(pack, environment=None)  # sin entorno: wallpaper no aplica
    assert 'alacritty' in result['applied']
    assert result['skipped'] == []  # sin wallpaper en el pack, nada que saltar

    content = cfg.read_text()
    assert 'import' in content  # línea de include añadida (alacritty usa import)
    backup = cfg_dir / 'alacritty.toml.bak-tm'
    assert backup.exists()     # backup creado antes de tocar


def test_connect_include_is_idempotent(tmp_path):
    from tui_manager.core.theme_packs import _connect_include
    cfg = tmp_path / 'foot.ini'
    cfg.write_text('font=monospace:size=10\n')
    target = '/tmp/generated-theme'
    assert _connect_include(str(cfg), 'include', target) is True
    first = cfg.read_text()
    assert _connect_include(str(cfg), 'include', target) is True
    assert cfg.read_text() == first  # no duplica


# ---------------- Plano de entorno ----------------

def test_env_detect_hyprland(monkeypatch):
    from tui_manager.core.environment import EnvironmentDetector, HyprlandAdapter
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setattr(os, 'environ', {'HYPRLAND_INSTANCE_SIGNATURE': 'sig_123'})
    adapter = EnvironmentDetector.detect()
    assert type(adapter) is HyprlandAdapter
    assert adapter.name == 'hyprland'


def test_env_detect_sway_i3_bspwm(monkeypatch):
    from tui_manager.core.environment import (
        EnvironmentDetector, SwayAdapter, I3Adapter, BspwmAdapter)
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    cases = [
        ({'SWAYSOCK': '/sock'}, SwayAdapter),
        ({'I3SOCK': '/sock'}, I3Adapter),
        ({'BSPWM_SOCKET': '/sock'}, BspwmAdapter),
    ]
    for env, expected in cases:
        monkeypatch.setattr(os, 'environ', env)
        assert type(EnvironmentDetector.detect()) is expected


def test_env_detect_de_and_tty(monkeypatch):
    from tui_manager.core.environment import (
        EnvironmentDetector, GenericDEAdapter, TTYAdapter)
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setattr(os, 'environ', {'XDG_CURRENT_DESKTOP': 'KDE'})
    assert type(EnvironmentDetector.detect()) is GenericDEAdapter

    monkeypatch.setattr(os, 'environ', {})
    assert type(EnvironmentDetector.detect()) is TTYAdapter


def test_env_detect_termux(monkeypatch):
    from tui_manager.core.environment import EnvironmentDetector, TermuxEnvironmentAdapter
    monkeypatch.setenv('TERMUX_VERSION', '0.118.0')
    assert type(EnvironmentDetector.detect()) is TermuxEnvironmentAdapter


def test_env_capabilities_graceful(monkeypatch):
    """Sin binarios del entorno, las capacidades se reducen — nunca explota."""
    import shutil
    from tui_manager.core.environment import HyprlandAdapter, Capability, TTYAdapter

    monkeypatch.setattr(shutil, 'which', lambda _: None)
    hypr = HyprlandAdapter()
    assert Capability.LAUNCH_APP in hypr.capabilities()
    assert Capability.SET_WALLPAPER not in hypr.capabilities()
    assert not hypr.supports(Capability.SET_WALLPAPER)

    tty = TTYAdapter()
    assert tty.capabilities() == {Capability.LAUNCH_APP}
    assert not tty.supports(Capability.RELOAD_CONFIG)


def test_env_hyprland_actions_with_fake_runner(fake_runner):
    from tui_manager.core.environment import HyprlandAdapter
    adapter = HyprlandAdapter()
    fake_runner.expect(['hyprctl', 'reload'], rc=0)
    assert adapter.reload_config() is True
    fake_runner.expect(['hyprctl', 'dispatch', 'exec', 'foot'], rc=0)
    assert adapter.launch_app('foot') is True


def test_env_hyprland_list_windows(fake_runner):
    import json
    from tui_manager.core.environment import HyprlandAdapter
    fake_runner.expect(['hyprctl', '-j', 'clients'], stdout=json.dumps(
        [{'pid': 123, 'class': 'foot', 'title': 'Term'}]))
    windows = HyprlandAdapter().list_windows()
    assert len(windows) == 1
    assert windows[0]['class'] == 'foot'


# ---------------- Control del sistema ----------------

def test_system_battery_termux(fake_runner):
    import shutil
    from tui_manager.core.system_control import SystemControl

    monkey_paths = {
        'termux-battery-status': '/bin/termux-battery-status',
    }
    import tui_manager.core.system_control as sc
    fake_runner.expect(['termux-battery-status'], stdout=(
        '{"percentage": 87, "plugged": true, "status": "CHARGING"}'))
    # _which usa shutil.which: parcheamos para que encuentre termux-battery-status
    orig_which = shutil.which
    sc_shutil = sc.shutil
    sc_shutil.which = lambda t, *a, **k: '/bin/termux-battery-status' if t == 'termux-battery-status' else None
    try:
        data = SystemControl().battery_status()
        assert data['percent'] == 87 and data['status'] == 'CHARGING'
    finally:
        sc_shutil.which = orig_which


def test_system_actions_fail_gracefully():
    """Sin systemd/gsettings (Termux), las acciones reportan no-soportado."""
    import shutil
    from tui_manager.core.system_control import SystemControl
    orig = shutil.which
    shutil.which = lambda t, *a, **k: None
    try:
        control = SystemControl()
        ok, msg = control.reboot()
        assert ok is False and 'systemctl' in msg
        ok, msg = control.set_dark_mode(True)
        assert ok is False and 'gsettings' in msg
    finally:
        shutil.which = orig


def test_system_battery_sysfs(tmp_path, monkeypatch):
    from tui_manager.core.system_control import SystemControl
    import tui_manager.core.system_control as sc

    bat = tmp_path / 'BAT0'
    bat.mkdir()
    (bat / 'capacity').write_text('77')
    (bat / 'status').write_text('Discharging')
    orig_listdir = os.listdir
    monkeypatch.setattr(os, 'listdir',
                        lambda p: ['BAT0'] if p == '/sys/class/power_supply' else orig_listdir(p))
    # Sin termux-battery-status en el PATH del test
    monkeypatch.setattr(sc.shutil, 'which', lambda t, *a, **k: None)
    # open real capturado antes de parchear (evita recursión infinita)
    real_open = open
    monkeypatch.setattr('builtins.open', lambda path, *a, **k: real_open(
        str(tmp_path / 'BAT0' / os.path.basename(path)), *a, **k))
    data = SystemControl().battery_status()
    assert data['percent'] == '77' and data['status'] == 'Discharging'


# ---------------- Monitor de procesos ----------------

def test_process_monitor_parses_ps_aux(fake_runner):
    from tui_manager.core.process_monitor import ProcessMonitor
    fake_runner.expect(['ps', 'aux'], stdout=(
        "USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND\n"
        "root 1 0.1 0.2 10240 4096 ? Ss 08:00 0:01 /sbin/init\n"
        "user 1234 15.5 3.2 512000 131072 ? Sl 09:00 1:02 firefox\n"
    ))
    procs = ProcessMonitor().get_processes()
    assert len(procs) == 2
    assert procs[0].pid == 1
    assert procs[1].cpu == 15.5
    assert 'firefox' in procs[1].command


def test_process_monitor_filters(fake_runner):
    from tui_manager.core.process_monitor import ProcessMonitor
    fake_runner.expect(['ps', 'aux'], stdout=(
        "USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND\n"
        "root 1 0.1 0.2 10240 4096 ? Ss 08:00 0:01 /sbin/init\n"
        "user 1234 15.5 3.2 512000 131072 ? Sl 09:00 1:02 firefox\n"
    ))
    monitor = ProcessMonitor()
    procs = monitor.get_processes(filters={'min_cpu': 10})
    assert len(procs) == 1 and procs[0].pid == 1234
    procs = monitor.get_processes(filters={'pid': 1})
    assert len(procs) == 1 and procs[0].pid == 1


# ---------------- Categorías compartidas ----------------

def test_categories_broad_coverage():
    from tui_manager.core.categories import get_category, categories
    expected = {
        'firefox': 'browsers', 'chromium': 'browsers',
        'alacritty': 'terminals', 'foot': 'terminals',
        'vlc': 'multimedia', 'mpv': 'multimedia', 'obs-studio': 'multimedia',
        'gimp': 'graphics', 'krita': 'graphics', 'blender': 'graphics',
        'discord': 'communication', 'telegram-desktop': 'communication',
        'steam': 'games', 'lutris': 'games', 'retroarch': 'games',
        'docker': 'virtualization', 'libvirt': 'virtualization',
        'postgresql': 'databases', 'redis': 'databases',
        'htop': 'system', 'btop': 'system', 'timeshift': 'system',
        'keepassxc': 'security', 'gnupg': 'security',
        'code': 'editors', 'neovim': 'editors', 'helix': 'editors',
        'qbittorrent': 'network', 'syncthing': 'network', 'tailscale': 'network',
    }
    for pkg, cat in expected.items():
        assert get_category(pkg) == cat, f"{pkg} → {get_category(pkg)} != {cat}"


def test_categories_variants_by_prefix():
    from tui_manager.core.categories import get_category
    # variantes de versión del mismo paquete
    assert get_category('firefox-esr') == 'browsers'
    assert get_category('python3.12') == 'development'
    assert get_category('linux-cachyos') == 'system'
    assert get_category('paquete-inexistente-xyz') == 'other'


def test_adapter_categories_shared():
    assert 'firefox' in DebianAdapter.CATEGORIES['browsers']
    assert 'cachyos-packages' in ArchAdapter.CATEGORIES['system']


# ---------------- Alfa 2: availability, sysinfo, doas BSD ------------------

def test_system_availability_degrades(monkeypatch):
    import shutil
    import tui_manager.core.system_control as sc
    from tui_manager.core.system_control import SystemControl
    # entorno sin capacidades (TTY) y sin herramientas → todo deshabilitado salvo nada
    env = type('E', (), {'supports': staticmethod(lambda c: False),
                         'capabilities': lambda self: set()})()
    monkeypatch.setattr(shutil, 'which', lambda t, *a, **k: None)
    avail = SystemControl(environment=env).availability()
    assert avail['lock'] == 'lock_screen (entorno)'
    assert avail['reboot'] == 'systemctl/shutdown'
    assert avail['launch'] == 'launch_app (entorno)'


def test_system_availability_full(monkeypatch):
    import shutil
    from tui_manager.core.system_control import SystemControl
    from tui_manager.core.environment import Capability
    env = type('E', (), {'supports': staticmethod(
        lambda c: c in (Capability.LOCK_SCREEN, Capability.LAUNCH_APP))})()
    monkeypatch.setattr(shutil, 'which', lambda t, *a, **k: f'/usr/bin/{t}')
    avail = SystemControl(environment=env).availability()
    assert avail == {k: None for k in avail}


def test_reboot_bsd_fallback(fake_runner, monkeypatch):
    import shutil
    import tui_manager.core.system_control as sc
    from tui_manager.core.system_control import SystemControl
    # sin systemctl, con shutdown (BSD) → shutdown -r now
    monkeypatch.setattr(sc.shutil, 'which',
                        lambda t, *a, **k: '/sbin/shutdown' if t == 'shutdown' else None)
    fake_runner.expect(['shutdown', '-r', 'now'], rc=0)
    ok, msg = SystemControl().reboot()
    assert ok is True and msg == ''


def test_sysinfo_collect(tmp_path, monkeypatch):
    import platform
    import tui_manager.core.sysinfo as si
    from tui_manager.core.system_control import SystemControl

    class FakePM:
        def get_installed_packages(self):
            return [1, 2, 3]

    sc_bat = SystemControl()
    monkeypatch.setattr(si.platform, 'system', lambda: 'FreeBSD')
    monkeypatch.setattr(si.platform, 'release', lambda: '14.2')
    monkeypatch.setattr(si.platform, 'machine', lambda: 'amd64')
    import collections
    Usage = collections.namedtuple('usage', 'total used free')
    monkeypatch.setattr(si.shutil, 'disk_usage', lambda p: Usage(100, 40, 60))
    monkeypatch.setattr(si._ram_total_mb, '__wrapped__', None, raising=False)
    info = si.collect(distribution='freebsd',
                      environment=type('E', (), {'name': 'tty'})(),
                      system_control=None, package_manager=FakePM(),
                      os_release='FreeBSD 14.2 (amd64)')
    assert info['distro'] == 'freebsd'
    assert info['environment'] == 'tty'
    assert info['packages'] == 3
    assert 'GB' in info['disk']


def test_sysinfo_battery_and_ram(tmp_path, monkeypatch):
    # RAM via /proc/meminfo simulado + batería via SystemControl fake
    import tui_manager.core.sysinfo as si
    (tmp_path / 'meminfo').write_text('MemTotal:        16384000 kB\n')
    class Sc:
        def battery_status(self):
            return {'percent': '55', 'status': 'Charging'}
    real_open = open
    monkeypatch.setattr('builtins.open', lambda path, *a, **k:
                        real_open(tmp_path / 'meminfo', *a, **k)
                        if path == '/proc/meminfo'
                        else real_open(path, *a, **k))
    info = si.collect(system_control=Sc())
    assert info['ram'] == '16000 MB'
    assert info['battery']['percent'] == '55'


def test_freebsd_doas_preferred(monkeypatch):
    import os
    import shutil
    from tui_manager.core.freebsd_adapter import FreeBSDAdapter
    monkeypatch.setattr(os, 'geteuid', lambda: 1000)
    # solo doas disponible → antepone doas
    monkeypatch.setattr(shutil, 'which',
                        lambda t, *a, **k: '/usr/bin/doas' if t == 'doas' else None)
    assert FreeBSDAdapter()._elevator() == 'doas'


def test_freebsd_doas_command_prefix(fake_runner, monkeypatch):
    import os
    import shutil
    from tui_manager.core.freebsd_adapter import FreeBSDAdapter
    monkeypatch.setattr(os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(shutil, 'which',
                        lambda t, *a, **k: '/usr/bin/doas' if t == 'doas' else None)
    fake_runner.expect(['doas', 'pkg', 'install', '-y', 'curl'], rc=0)
    assert FreeBSDAdapter().install_package('curl', confirm=False) is True


def test_pkgsrc_sudo_command_prefix(fake_runner, monkeypatch):
    import os
    import shutil
    from tui_manager.core.pkgsrc_adapter import PkgsrcAdapter
    monkeypatch.setattr(os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(shutil, 'which',
                        lambda t, *a, **k: '/usr/bin/sudo' if t == 'sudo' else None)
    fake_runner.expect(['sudo', 'pkgin', '-y', 'install', 'curl'], rc=0)
    assert PkgsrcAdapter().install_package('curl', confirm=False) is True


def test_package_manager_orphans_passthrough():
    """PackageManager delega huérfanos en el adapter y tolera errores."""
    from tui_manager.core.package_adapter import Package
    from tui_manager.core.package_manager import PackageManager

    class FakeAdapter:
        def get_orphans(self):
            return [Package(name='libfoo', version='1.0')]

        def clean_orphans(self, confirm=True):
            assert confirm is False
            return True

    pm = PackageManager(distribution='arch')
    pm.adapter = FakeAdapter()
    assert [p.name for p in pm.get_orphans()] == ['libfoo']
    assert pm.clean_orphans(confirm=False) is True

    class BrokenAdapter:
        def get_orphans(self):
            raise RuntimeError('boom')

        def clean_orphans(self, confirm=True):
            raise RuntimeError('boom')

    pm.adapter = BrokenAdapter()
    assert pm.get_orphans() == []
    assert pm.clean_orphans(confirm=False) is False
