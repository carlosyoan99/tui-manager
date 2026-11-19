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


# ---- Runners simulados para sysinfo (nunca ejecutan subprocess real) -------

def _no_subprocess(cmd, timeout=5):
    """Runner que falla limpiamente: fuerza degrade honesto a '' / []."""
    return 1, '', ''


class _ScriptedRunner:
    """Devuelve (rc, stdout, stderr) por comando; el resto falla limpio."""

    def __init__(self, script=None):
        self.script = {tuple(k): v for k, v in (script or {}).items()}
        self.calls = []

    def __call__(self, cmd, timeout=5):
        self.calls.append(tuple(cmd))
        return self.script.get(tuple(cmd), (1, '', ''))


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
                      os_release='FreeBSD 14.2 (amd64)',
                      runner=_no_subprocess, pm_name='pkg')
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
    info = si.collect(system_control=Sc(),
                      runner=_no_subprocess, pm_name='apt')
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


def test_sysinfo_extended_fields(monkeypatch):
    """Acerca de expone campos amplios de hardware y software."""
    import tui_manager.core.sysinfo as si
    info = si.collect(distribution='arch',
                      environment=type('E', (), {'name': 'sway'})(),
                      runner=_no_subprocess, pm_name='pacman')
    expected = ('hostname', 'user', 'platform', 'arch', 'python', 'shell',
                'term', 'uptime', 'cpu_model', 'cpu_logical', 'cpu_physical',
                'ram_total', 'ram_available', 'swap', 'disk_total',
                'disk_used', 'disk_free', 'disk_percent')
    for key in expected:
        assert key in info, f'falta campo {key}'
    assert info['cpu_logical'] >= 1
    assert isinstance(info['disk_percent'], int)


# ---------------- 1.1-F: campos estilo fastfetch en sysinfo ----------------

def test_sysinfo_fastfetch_fields_present():
    import tui_manager.core.sysinfo as si
    info = si.collect(runner=_no_subprocess, pm_name='pkg')
    for key in ('os_version', 'device_name', 'device_type', 'gpu',
                'package_manager', 'displays', 'session', 'shell', 'uptime'):
        assert key in info, f'falta campo {key}'
    assert info['displays'] == []
    assert isinstance(info['session'], str)


def test_sysinfo_os_version_sources():
    import tui_manager.core.sysinfo as si
    text = 'ID=arch\nVERSION_ID="rolling"\nPRETTY_NAME="Arch Linux"\n'
    assert si.collect(runner=_no_subprocess, pm_name='x',
                      os_release_text=text)['os_version'] == 'rolling'
    assert si.collect(runner=_no_subprocess, pm_name='x',
                      os_release_text='VERSION=7\n')['os_version'] == '7'
    assert si.collect(runner=_no_subprocess, pm_name='x',
                      os_release_text='PRETTY_NAME="Foo Linux"\n')['os_version'] == 'Foo Linux'
    assert si.collect(runner=_no_subprocess, pm_name='x',
                      os_release_text='')['os_version'] == ''


def test_sysinfo_device_name_termux(monkeypatch):
    import tui_manager.core.sysinfo as si
    monkeypatch.setenv('TERMUX_VERSION', '0.118.0')
    runner = _ScriptedRunner({
        ('getprop', 'ro.product.model'): (0, 'Pixel 7\n', ''),
    })
    info = si.collect(runner=runner, pm_name='pkg')
    assert info['device_name'] == 'Pixel 7'
    assert ('getprop', 'ro.product.model') in runner.calls
    # sin dato de getprop → hostname (degrada, sin falsedades)
    assert si.collect(runner=_no_subprocess, pm_name='pkg')['device_name']


def _not_termux(monkeypatch):
    """Neutraliza la detección de Termux (vars y PREFIX) para tests multi-SO."""
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setenv('PREFIX', '/usr')


def test_sysinfo_device_type(monkeypatch, tmp_path):
    import tui_manager.core.sysinfo as si
    _not_termux(monkeypatch)

    vm = _ScriptedRunner({('systemd-detect-virt',): (0, 'kvm\n', '')})
    assert si.collect(runner=vm, pm_name='x')['device_type'] == 'VM'

    chassis = tmp_path / 'chassis'
    chassis.write_text('10\n')
    monkeypatch.setattr(si, 'DMI_CHASSIS_PATH', str(chassis))
    novirt = _ScriptedRunner({('systemd-detect-virt',): (0, 'none\n', '')})
    assert si.collect(runner=novirt, pm_name='x')['device_type'] == 'laptop'
    chassis.write_text('3\n')
    assert si.collect(runner=novirt, pm_name='x')['device_type'] == 'desktop'
    chassis.write_text('99\n')
    assert si.collect(runner=novirt, pm_name='x')['device_type'] == ''

    monkeypatch.setenv('TERMUX_VERSION', '0.1')
    assert si.collect(runner=_no_subprocess, pm_name='pkg')['device_type'] == 'Termux'


def test_sysinfo_gpu_sources(monkeypatch):
    import tui_manager.core.sysinfo as si
    _not_termux(monkeypatch)

    lspci = _ScriptedRunner({('lspci',): (0,
        '00:02.0 VGA compatible controller: Intel Corporation UHD Graphics 620\n'
        '00:1f.6 Network controller: Realtek Semiconductor\n', '')})
    assert 'Intel Corporation UHD Graphics 620' in si.collect(
        runner=lspci, pm_name='x')['gpu']

    monkeypatch.setattr(si.platform, 'system', lambda: 'FreeBSD')
    bsd = _ScriptedRunner({('sysctl', '-n', 'hw.model'): (0, 'AMD Ryzen 9\n', '')})
    assert si.collect(runner=bsd, pm_name='x')['gpu'] == 'AMD Ryzen 9'

    monkeypatch.setattr(si.platform, 'system', lambda: 'Linux')
    monkeypatch.setenv('TERMUX_VERSION', '0.1')
    termux = _ScriptedRunner({('getprop', 'ro.gpu'): (0, 'Adreno 640\n', '')})
    assert si.collect(runner=termux, pm_name='pkg')['gpu'] == 'Adreno 640'

    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    assert si.collect(runner=_no_subprocess, pm_name='x')['gpu'] == ''


def test_sysinfo_displays_sources():
    import json
    import tui_manager.core.sysinfo as si

    hypr = _ScriptedRunner({('hyprctl', 'monitors'): (0,
        'Monitor eDP-1 (ID 1):\n   1920x1080@60.00000Hz\n', '')})
    assert si.collect(runner=hypr, pm_name='x')['displays'] == [
        'eDP-1 1920x1080@60.00000Hz']

    sway_out = json.dumps([{'name': 'HDMI-A-1',
                            'rect': {'width': 2560, 'height': 1440}}])
    sway = _ScriptedRunner({('swaymsg', '-t', 'get_outputs'): (0, sway_out, '')})
    assert si.collect(runner=sway, pm_name='x')['displays'] == [
        'HDMI-A-1 2560x1440']

    xrandr = _ScriptedRunner({('xrandr', '--query'): (0,
        'Screen 0: minimum 8 x 8\n'
        'HDMI-1 connected primary 1920x1080+0+0 344mm x 194mm\n', '')})
    assert si.collect(runner=xrandr, pm_name='x')['displays'] == [
        'HDMI-1 1920x1080']

    assert si.collect(runner=_no_subprocess, pm_name='x')['displays'] == []


def test_sysinfo_session_and_shell_uptime(monkeypatch):
    import tui_manager.core.sysinfo as si
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'sway')
    monkeypatch.setenv('WAYLAND_DISPLAY', 'wayland-1')
    monkeypatch.setenv('SHELL', '/bin/zsh')
    info = si.collect(runner=_no_subprocess, pm_name='x')
    assert info['session'] == 'wayland · sway · wayland-1'
    assert info['shell'] == '/bin/zsh'
    assert isinstance(info['uptime'], str)

    for key in ('XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'WAYLAND_DISPLAY'):
        monkeypatch.delenv(key, raising=False)
    assert si.collect(runner=_no_subprocess, pm_name='x')['session'] == ''


def test_sysinfo_package_manager_from_detector(monkeypatch):
    import tui_manager.core.sysinfo as si
    from tui_manager.core.distribution import DistributionDetector
    monkeypatch.setattr(DistributionDetector, 'get_package_manager',
                        staticmethod(lambda: 'pacman'))
    assert si.collect(runner=_no_subprocess)['package_manager'] == 'pacman'
    assert si.collect(runner=_no_subprocess, pm_name='xbps')['package_manager'] == 'xbps'
