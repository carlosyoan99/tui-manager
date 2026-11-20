"""
Cobertura adicional de ``tui_manager.core`` (R1-1 del PLAN-1.0).

Todas las pruebas son 100% simuladas: no hay subprocess reales, ni red, ni
sudo, ni escritura fuera de ``tmp_path``. Se reutilizan los patrones del
proyecto (FakeRunner, monkeypatch de ``shutil.which``/``subprocess.run`` y
fakes de servicios).
"""
import io
import os
import platform
import subprocess
from collections import namedtuple

import pytest
import yaml


# --------------------------------------------------------------------------
# Helpers compartidos
# --------------------------------------------------------------------------

class _Completed:
    def __init__(self, rc=0, stdout='', stderr=''):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = stderr


def _patch_open(monkeypatch, mapping):
    """Sustituye open() para las rutas de ``mapping``; el resto usa el real.

    Los valores pueden ser texto (se devuelve un StringIO) o una excepción
    (se lanza al abrir).
    """
    real_open = open

    def fake(path, *args, **kwargs):
        key = os.fspath(path)
        if key in mapping:
            value = mapping[key]
            if isinstance(value, Exception):
                raise value
            return io.StringIO(value)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr('builtins.open', fake)


def _fake_commands(monkeypatch, table):
    """Simula subprocess.run usando una tabla tuple(cmd) -> (rc, out, err)."""
    def run(cmd, *args, **kwargs):
        key = tuple(cmd)
        if key not in table:
            raise AssertionError(f'Comando no simulado: {list(cmd)}')
        value = table[key]
        if isinstance(value, Exception):
            raise value
        return _Completed(*value)

    monkeypatch.setattr(subprocess, 'run', run)
    return run


# ==========================================================================
# system_control.py
# ==========================================================================

@pytest.fixture
def sc_tools(monkeypatch):
    import tui_manager.core.system_control as module
    tools = set()
    monkeypatch.setattr(module.shutil, 'which',
                        lambda t, *a, **k: f'/usr/bin/{t}' if t in tools else None)
    return module, tools


def test_sc_run_exception(sc_tools, monkeypatch):
    module, _ = sc_tools

    def boom(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(subprocess, 'run', boom)
    assert module._run(['anything']) == (-1, '', 'boom')
    # ruta normal
    _fake_commands(monkeypatch, {('true',): (0, 'out', 'err')})
    assert module._run(['true']) == (0, 'out', 'err')


def test_sc_lock(sc_tools):
    module, _ = sc_tools
    from tui_manager.core.environment import Capability

    class Env:
        def supports(self, cap):
            return cap == Capability.LOCK_SCREEN

        def lock_screen(self):
            return True

    class NoImpl:
        def supports(self, cap):
            return True

        def lock_screen(self):
            raise NotImplementedError

    assert module.SystemControl(Env()).lock() == (True, '')
    assert module.SystemControl(NoImpl()).lock() == (
        False, 'lock_screen no soportado')
    assert module.SystemControl().lock() == (False, 'lock_screen no soportado')


def test_sc_logout(sc_tools, monkeypatch, fake_runner):
    module, tools = sc_tools
    control = module.SystemControl()
    assert control.logout() == (False, 'loginctl no disponible')
    tools.add('loginctl')
    monkeypatch.setenv('XDG_SESSION_ID', 'sess-7')
    fake_runner.expect(['loginctl', 'terminate-session', 'sess-7'], rc=0)
    assert control.logout() == (True, '')
    fake_runner.expect(['loginctl', 'terminate-session', 'sess-7'], rc=1)
    assert control.logout() == (False, '')


def test_sc_power_actions(sc_tools, fake_runner):
    module, tools = sc_tools
    control = module.SystemControl()

    assert control.shutdown() == (False, 'systemctl/shutdown no disponible')
    assert control.suspend() == (False, 'systemctl/zzz no disponible')

    tools.add('shutdown')
    fake_runner.expect(['shutdown', '-r', 'now'], rc=0)
    assert control.reboot() == (True, '')
    fake_runner.expect(['shutdown', '-p', 'now'], rc=1)
    assert control.shutdown() == (False, '')

    tools.add('systemctl')
    fake_runner.expect(['systemctl', 'reboot'], rc=0)
    assert control.reboot() == (True, '')
    fake_runner.expect(['systemctl', 'poweroff'], rc=0)
    assert control.shutdown() == (True, '')
    fake_runner.expect(['systemctl', 'suspend'], rc=1)
    assert control.suspend() == (False, '')

    tools.clear()
    tools.add('zzz')
    fake_runner.expect(['zzz'], rc=0)
    assert control.suspend() == (True, '')


def test_sc_brightness(sc_tools, fake_runner):
    module, tools = sc_tools
    control = module.SystemControl()
    assert control.brightness_step(1) == (False, 'brightnessctl no disponible')
    tools.add('brightnessctl')
    fake_runner.expect(['brightnessctl', 'set', '+5%'], rc=0)
    assert control.brightness_step(3) == (True, '')
    fake_runner.expect(['brightnessctl', 'set', '-5%'], rc=1)
    assert control.brightness_step(-1) == (False, '')


def test_sc_power_profiles(sc_tools, fake_runner):
    module, tools = sc_tools
    control = module.SystemControl()
    reason = 'powerprofilesctl no disponible'
    assert control.power_profiles() == (False, reason)
    assert control.set_power_profile('balanced') == (False, reason)
    tools.add('powerprofilesctl')
    fake_runner.expect(['powerprofilesctl', 'list'], rc=0,
                       stdout='  balanced \n performance\n')
    ok, profiles = control.power_profiles()
    assert ok is True and profiles == 'balanced \n performance'
    fake_runner.expect(['powerprofilesctl', 'list'], rc=1)
    assert control.power_profiles() == (False, reason)
    fake_runner.expect(['powerprofilesctl', 'set', 'balanced'], rc=0)
    assert control.set_power_profile('balanced') == (True, '')
    fake_runner.expect(['powerprofilesctl', 'set', 'balanced'], rc=1)
    assert control.set_power_profile('balanced') == (False, '')


def test_sc_timezone(sc_tools, fake_runner):
    module, tools = sc_tools
    control = module.SystemControl()
    reason = 'timedatectl no disponible'
    assert control.set_timezone('UTC') == (False, reason)
    assert control.list_timezones() == (False, reason)
    tools.add('timedatectl')
    fake_runner.expect(['timedatectl', 'set-timezone', 'UTC'], rc=0, stderr='')
    assert control.set_timezone('UTC') == (True, '')
    fake_runner.expect(['timedatectl', 'set-timezone', 'UTC'], rc=1,
                       stderr='zona inválida')
    assert control.set_timezone('UTC') == (False, 'zona inválida')
    fake_runner.expect(['timedatectl', 'list-timezones'], rc=0,
                       stdout='UTC\nEtc/UTC\n')
    assert control.list_timezones() == (True, ['UTC', 'Etc/UTC', ''])
    fake_runner.expect(['timedatectl', 'list-timezones'], rc=1)
    assert control.list_timezones() == (False, reason)


def test_sc_dark_mode(sc_tools, fake_runner):
    module, tools = sc_tools
    control = module.SystemControl()
    assert control.set_dark_mode(True) == (False, 'gsettings no disponible')
    tools.add('gsettings')
    expected = ['gsettings', 'set', 'org.gnome.desktop.interface',
                'color-scheme']
    fake_runner.expect(expected + ['prefer-dark'], rc=0)
    assert control.set_dark_mode(True) == (True, '')
    fake_runner.expect(expected + ['prefer-light'], rc=1)
    assert control.set_dark_mode(False) == (False, '')


def test_sc_battery_termux_bad_json_and_sysfs(sc_tools, fake_runner, monkeypatch):
    module, tools = sc_tools
    tools.add('termux-battery-status')
    # JSON inválido → cae al sysfs
    fake_runner.expect(['termux-battery-status'], rc=0, stdout='no-es-json')
    real_listdir = os.listdir

    def no_listdir(path):
        if path == '/sys/class/power_supply':
            raise OSError('sin sysfs')
        return real_listdir(path)

    monkeypatch.setattr(os, 'listdir', no_listdir)
    assert module.SystemControl().battery_status() is None

    # comando con error → también cae al sysfs (sin baterías → None)
    fake_runner.expect(['termux-battery-status'], rc=1, stdout='')
    monkeypatch.setattr(os, 'listdir',
                        lambda path: [] if path == '/sys/class/power_supply'
                        else real_listdir(path))
    assert module.SystemControl().battery_status() is None


def test_sc_availability_env_cap_raises(sc_tools):
    module, _ = sc_tools

    class BrokenEnv:
        def supports(self, cap):
            raise RuntimeError('entorno roto')

    avail = module.SystemControl(BrokenEnv()).availability()
    assert avail['lock'] == 'lock_screen (entorno)'
    assert avail['launch'] == 'launch_app (entorno)'


# ==========================================================================
# theme_manager.py
# ==========================================================================

def test_theme_manager_full_api():
    from tui_manager.core.theme_manager import ThemeManager, ThemeError

    tm = ThemeManager()
    assert tm.get_current_theme() == 'dark'
    assert set(tm.list_themes()) == {'dark', 'light', 'retro'}
    assert tm.is_theme_available('light') is True
    assert tm.is_theme_available('nope') is False

    # nombre desconocido → colors por defecto (sin lanzar)
    assert ThemeManager('desconocido').get_current_theme() == 'desconocido'
    assert ThemeManager('').get_current_theme() == ThemeManager.DEFAULT_THEME

    tm.set_theme('light')
    assert tm.get_color('primary') == 'blue'
    assert tm.get_color('inexistente') == 'black'  # fallback a foreground
    colors = tm.get_colors()
    colors['primary'] = 'modificado'
    assert tm.get_color('primary') == 'blue'  # get_colors devuelve copia

    palette = tm.get_palette()
    assert palette[0] == ('default', 'black', 'white')
    assert palette[-1][0] == 'border'

    with pytest.raises(ThemeError):
        tm.set_theme('inexistente')


# ==========================================================================
# theme_packs.py
# ==========================================================================

@pytest.fixture
def tp_env(tmp_path, monkeypatch):
    import tui_manager.core.theme_packs as module
    monkeypatch.setenv('HOME', str(tmp_path))
    user_dir = tmp_path / '.config' / 'tui-manager' / 'themes'
    user_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module, 'user_themes_dir', lambda: str(user_dir))
    return module, tmp_path, user_dir


def test_tp_pack_from_file_and_to_file(tp_env, tmp_path):
    module, _, user_dir = tp_env
    source = user_dir / 'custom.yaml'
    source.write_text(yaml.dump({
        'name': 'custom',
        'dark': False,
        'palette': {'bg': '#000000', 'fg': '#ffffff'},
        'wallpaper': 'wall.png',
        'surfaces': {'foot': {'file': 'colors.yaml'}},
    }, allow_unicode=True))
    pack = module.ThemePack.from_file(str(source))
    assert pack.name == 'custom'
    assert pack.dark is False
    assert pack.wallpaper == 'wall.png'
    assert pack.surfaces['foot']['file'] == 'colors.yaml'
    assert pack.source == str(source)

    # valores por defecto cuando falta información / archivo vacío
    minimal = user_dir / 'minimal.yml'
    minimal.write_text(yaml.dump({'palette': {'bg': '#111111'}}))
    p2 = module.ThemePack.from_file(str(minimal))
    assert p2.name == 'minimal' and p2.dark is True
    assert p2.wallpaper is None and p2.surfaces == {}

    empty = user_dir / 'empty.yaml'
    empty.write_text('')
    p3 = module.ThemePack.from_file(str(empty))
    assert p3.name == 'empty' and p3.palette == {}

    out = tmp_path / 'nuevo' / 'guardado.yaml'
    pack.to_file(str(out))
    assert out.exists()
    assert module.ThemePack.from_file(str(out)).name == 'custom'


def test_tp_list_packs_invalid_and_duplicates(tp_env, monkeypatch, tmp_path):
    module, _, user_dir = tp_env
    (user_dir / 'broken.yaml').write_text('clave: [1, 2')
    (user_dir / 'good.yaml').write_text(
        yaml.dump({'name': 'good', 'palette': {'bg': '#ffffff'}}))

    builtin = tmp_path / 'builtin'
    builtin.mkdir()
    (builtin / 'dup.yaml').write_text(yaml.dump({'name': 'builtin-dup'}))
    (user_dir / 'dup.yaml').write_text(yaml.dump({'name': 'user-dup'}))
    monkeypatch.setattr(module, 'THEMES_DIR', str(builtin))

    packs = module.list_packs()
    names = [p.name for p in packs]
    assert 'good' in names
    assert names.count('user-dup') == 1  # el incluido se descarta por el seen
    assert module.get_pack('good') is not None
    assert module.get_pack('inexistente') is None


def test_tp_install_pack_from_url(tp_env, monkeypatch):
    module, _, user_dir = tp_env

    def retrieve(url, dest):
        from pathlib import Path
        Path(dest).write_text(yaml.dump({
            'name': 'remote', 'palette': {'bg': '#123456'}}))

    monkeypatch.setattr(module.urllib.request, 'urlretrieve', retrieve)
    pack = module.install_pack_from_url(
        'https://ejemplo.invalid/theme.yaml?revision=1')
    assert pack.name == 'remote'
    assert (user_dir / 'theme.yaml').exists()

    pack2 = module.install_pack_from_url('https://ejemplo.invalid/sin-extension')
    assert pack2.name == 'remote'
    assert (user_dir / 'sin-extension.yaml').exists()

    def offline(url, dest):
        raise OSError('sin red')

    monkeypatch.setattr(module.urllib.request, 'urlretrieve', offline)
    assert module.install_pack_from_url('https://ejemplo.invalid/x.yaml') is None


def test_tp_remove_pack(tp_env, monkeypatch, tmp_path):
    module, _, user_dir = tp_env
    (user_dir / 'removable.yaml').write_text(yaml.dump({'name': 'removable'}))
    assert module.remove_pack('removable') is True
    assert module.remove_pack('removable') is False
    monkeypatch.setattr(module, 'user_themes_dir',
                        lambda: str(tmp_path / 'directorio-inexistente'))
    assert module.remove_pack('removable') is False


def test_tp_hex_for(tp_env):
    module, _, _ = tp_env
    assert module._hex_for({'otra': '#111', 'bg': '#222'}, 'bg') == '#222'
    assert module._hex_for({}, 'bg', 'fg') == '#000000'


class _FakeThemeEnv:
    def __init__(self, caps=(), wallpaper_ok=True, dark_ok=True):
        self.caps = set(caps)
        self.wallpaper_ok = wallpaper_ok
        self.dark_ok = dark_ok
        self.wallpaper_path = None
        self.dark_arg = None

    def supports(self, cap):
        return cap in self.caps

    def set_wallpaper(self, path):
        self.wallpaper_path = path
        return self.wallpaper_ok

    def set_dark_mode(self, dark):
        self.dark_arg = dark
        return self.dark_ok


def test_tp_apply_pack_with_environment(tp_env):
    module, tmp_path, _ = tp_env
    from tui_manager.core.environment import Capability

    wallpaper = tmp_path / 'wall.png'
    wallpaper.write_bytes(b'')
    pack = module.ThemePack(
        name='pack', palette={'bg': '#010101'}, wallpaper=str(wallpaper),
        surfaces={'alacritty': {'file': 'colors.toml'}}, dark=False,
        source=str(tmp_path / 'pack.yaml'))

    env = _FakeThemeEnv({Capability.SET_WALLPAPER, Capability.SET_DARK_MODE})
    result = module.apply_pack(pack, environment=env)
    assert set(result['applied']) == {'wallpaper', 'dark_mode', 'alacritty'}
    assert result['skipped'] == []
    assert env.wallpaper_path == str(wallpaper)
    assert env.dark_arg is False

    # wallpaper relativo que SÍ existe junto al yaml
    relative = module.ThemePack(
        name='rel', wallpaper='wall.png', source=str(tmp_path / 'pack.yaml'))
    env2 = _FakeThemeEnv({Capability.SET_WALLPAPER})
    result2 = module.apply_pack(relative, environment=env2)
    assert env2.wallpaper_path == str(wallpaper)
    assert 'wallpaper' in result2['applied']

    # wallpaper relativo que no existe y fallo al aplicar
    missing = module.ThemePack(
        name='miss', wallpaper='no-existe.png', source=str(tmp_path / 'p.yaml'))
    env3 = _FakeThemeEnv({Capability.SET_WALLPAPER}, wallpaper_ok=False)
    result3 = module.apply_pack(missing, environment=env3)
    assert env3.wallpaper_path == 'no-existe.png'
    assert result3['skipped'] == ['wallpaper']

    # sin capacidad de wallpaper pero con wallpaper en el pack
    result4 = module.apply_pack(pack, environment=None)
    assert 'wallpaper' in result4['skipped']


def test_tp_apply_surface_branches(tp_env):
    module, _, _ = tp_env
    home = os.path.join(os.path.expanduser('~'), '.config',
                        'tui-manager', 'theme-terminal')
    os.makedirs(home, exist_ok=True)
    # archivo generado previo: se elimina antes de regenerar
    (open(os.path.join(home, 'foo-theme'), 'w')).write('viejo')

    assert module._apply_surface(
        'alacritty', {'file': 'colors.toml', 'palette': {'bg': '#111'}}, home) is True
    assert os.path.exists(os.path.join(home, 'alacritty-theme'))

    assert module._apply_surface(
        'alacritty', {'file': 'colors.yaml'}, home) is True
    assert module._apply_surface(
        'foot', {'palette': {'fg': '#222'}}, home) is True
    assert module._apply_surface(
        'kitty', {'file': 'colors.yaml'}, home) is True
    assert open(os.path.join(home, 'kitty-theme')).read() == "{'file': 'colors.yaml'}"

    # spec no dict → no se genera nada
    assert module._apply_surface('kitty', 'texto-crudo', home) is False
    # superficie desconocida: se genera pero no se conecta
    assert module._apply_surface('wezterm', {'palette': {}}, home) is False

    assert module._render_alacritty({'bg': '#1', 'fg': '#2', 'accent': '#3'}) == (
        '[colors]\n\n[colors.primary]\nbackground = "#1"\n'
        '\n[colors.primary]\nforeground = "#2"\n'
        '\n[colors.primary]\nbright_foreground = "#3"\n')
    assert module._render_alacritty({'otro': '#0'}) == '[colors]\n'


def test_tp_connect_include_edges(tp_env, monkeypatch, tmp_path):
    module, _, _ = tp_env
    # archivo nuevo (sin contenido previo)
    cfg = tmp_path / 'nuevo' / 'x.conf'
    assert module._connect_include(str(cfg), 'include', '/tmp/g') is True
    assert cfg.read_text() == 'include = "/tmp/g"\n'

    # archivo existente sin salto final
    cfg2 = tmp_path / 'existente.conf'
    cfg2.write_text('a=1')
    assert module._connect_include(str(cfg2), 'include', '/tmp/g') is True
    assert cfg2.read_text().startswith('a=1\ninclude = "/tmp/g"')

    # error al crear el directorio → False
    def no_makedirs(*args, **kwargs):
        raise OSError('solo lectura')

    monkeypatch.setattr(module.os, 'makedirs', no_makedirs)
    assert module._connect_include(str(tmp_path / 'e' / 'x'), 'include', 'g') is False


# ==========================================================================
# sysinfo.py
# ==========================================================================

@pytest.fixture
def si(monkeypatch):
    import tui_manager.core.sysinfo as module
    return module


def test_si_run_exception(si, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(subprocess, 'run', boom)
    assert si._run(['x']) == (-1, '', 'boom')


def test_si_meminfo_error(si, monkeypatch):
    _patch_open(monkeypatch, {'/proc/meminfo': OSError('no')})
    assert si._meminfo() == {}


def test_si_ram_total_fallbacks(si, monkeypatch):
    _patch_open(monkeypatch, {'/proc/meminfo': 'MemTotal: abc kB\n'})
    _fake_commands(monkeypatch,
                   {('sysctl', '-n', 'hw.physmem'): (0, '2147483648\n', '')})
    assert si._ram_total_mb() == '2048 MB'
    _fake_commands(monkeypatch,
                   {('sysctl', '-n', 'hw.physmem'): (1, '', 'error')})
    assert si._ram_total_mb() == ''
    _patch_open(monkeypatch, {'/proc/meminfo': OSError('no')})
    _fake_commands(monkeypatch,
                   {('sysctl', '-n', 'hw.physmem'): RuntimeError('boom')})
    assert si._ram_total_mb() == ''


def test_si_cpu_model_sources(si, monkeypatch):
    _patch_open(monkeypatch,
                {'/proc/cpuinfo': 'model name\t: Ryzen 9 7950X\n'})
    assert si._cpu_model() == 'Ryzen 9 7950X'

    _patch_open(monkeypatch, {'/proc/cpuinfo': OSError('no')})
    _fake_commands(monkeypatch,
                   {('sysctl', '-n', 'hw.model'): (0, 'AMD EPYC\n', '')})
    assert si._cpu_model() == 'AMD EPYC'

    _fake_commands(monkeypatch, {
        ('sysctl', '-n', 'hw.model'): (1, '', ''),
        ('lscpu',): (0, 'Arquitectura: x86_64\nModel name:  Intel Xeon\n', ''),
    })
    assert si._cpu_model() == 'Intel Xeon'

    _fake_commands(monkeypatch, {
        ('sysctl', '-n', 'hw.model'): (1, '', ''),
        ('lscpu',): (1, '', ''),
    })
    assert si._cpu_model() == ''


def test_si_uptime_variants(si, monkeypatch):
    _patch_open(monkeypatch, {'/proc/uptime': '90061.5 100.0\n'})
    assert si._uptime() == '1 d 1 h 1 min'
    _patch_open(monkeypatch, {'/proc/uptime': '0.5 0.0\n'})
    assert si._uptime() == '0 min'

    _patch_open(monkeypatch, {'/proc/uptime': OSError('no')})
    _fake_commands(monkeypatch,
                   {('sysctl', '-n', 'kern.boottime'): (0, ' boottime info\n', '')})
    assert si._uptime() == 'boottime info'
    _fake_commands(monkeypatch,
                   {('sysctl', '-n', 'kern.boottime'): (1, '', '')})
    assert si._uptime() == ''


def test_si_disk_paths(si, monkeypatch):
    Usage = namedtuple('usage', 'total used free')

    def no_disk(path):
        raise OSError('sin disco')

    monkeypatch.setattr(si.shutil, 'disk_usage', no_disk)
    assert si._disk_root() == ''
    assert si._disk_details() == {}

    monkeypatch.setattr(
        si.shutil, 'disk_usage',
        lambda path: Usage(10 * 1024 ** 3, 2 * 1024 ** 3, 8 * 1024 ** 3))
    assert '20% usado' in si._disk_root()
    details = si._disk_details()
    assert details == {'total': '10 GB', 'used': '2 GB',
                       'free': '8 GB', 'percent': 20}


def test_si_collect_error_branches(si, monkeypatch):
    class BadSystemControl:
        def battery_status(self):
            raise RuntimeError('batería rota')

    class BadPackageManager:
        def get_installed_packages(self):
            raise RuntimeError('gestor roto')

    info = si.collect(distribution='arch',
                      environment=type('E', (), {'name': None})(),
                      system_control=BadSystemControl(),
                      package_manager=BadPackageManager(),
                      os_release='Arch Linux')
    assert info['battery'] is None
    assert info['packages'] is None
    assert info['environment'] == '—'
    assert info['os'] == 'Arch Linux'


def test_si_physical_cores(si, monkeypatch):
    _patch_open(monkeypatch, {'/proc/cpuinfo': (
        'physical id\t: 0\ncore id\t\t: 0\n'
        'physical id\t: 1\ncore id\t\t: 1\n')})
    assert si._physical_cores(4) == 4
    _patch_open(monkeypatch, {'/proc/cpuinfo': OSError('no')})
    assert si._physical_cores(4) == 2
    assert si._physical_cores(0) == 0


# ==========================================================================
# void_adapter.py
# ==========================================================================

@pytest.fixture
def void():
    from tui_manager.core.void_adapter import VoidAdapter
    adapter = VoidAdapter()
    calls = []

    def make_exec(table):
        def fake(cmd, sudo=True):
            calls.append((tuple(cmd), sudo))
            key = tuple(cmd)
            if key not in table:
                raise AssertionError(f'Comando no simulado: {list(cmd)}')
            return table[key]
        return fake

    return adapter, calls, make_exec


def test_void_helpers(void):
    import tui_manager.core.void_adapter as module
    assert module._norm_key('  Descripción  ') == 'descripcion'
    assert module._field('Descripción') == 'description'
    assert module._field('Tamano instalado') == 'size'
    assert module._field('Depende de') == 'depends'
    assert module._field('campo-desconocido') == ''
    assert module.split_pkgver('bash-5.2.26_1') == ('bash', '5.2.26_1')
    assert module.split_pkgver('sin-version') == (None, None)


def test_void_execute_command_sudo(void, fake_runner):
    adapter, _, _ = void
    fake_runner.expect(['xbps-query', '-l'], rc=0)
    assert adapter.execute_command(['xbps-query', '-l']) == (0, '', '')
    assert fake_runner.calls[-1] == ('xbps-query', '-l')

    fake_runner.expect(['xbps-install', '-n'], rc=0)
    adapter.execute_command(['xbps-install', '-n'])
    assert fake_runner.calls[-1] == ('xbps-install', '-n')

    fake_runner.expect(['xbps-remove', '-n'], rc=0)
    adapter.execute_command(['xbps-remove', '-n'])
    assert fake_runner.calls[-1] == ('xbps-remove', '-n')

    fake_runner.expect(['sudo', '-n', 'true'], rc=0)
    fake_runner.expect(['sudo', '-n', 'xbps-install', '-S'], rc=0)
    adapter.execute_command(['xbps-install', '-S'])
    assert fake_runner.calls[-1] == ('sudo', '-n', 'xbps-install', '-S')


def test_void_installed_packages(void):
    adapter, _, make_exec = void
    from tui_manager.core.void_adapter import PackageNotFoundError  # noqa: F401

    adapter.execute_command = make_exec(
        {('xbps-query', '-l'): (1, '', 'error')})
    assert adapter.get_installed_packages() == []

    adapter.execute_command = make_exec({
        ('xbps-query', '-l'): (0,
            '\ninvalid\nbash\nii bash-5.2.26_1 The GNU Bourne Again shell\n'
            'ii zsh-5.9_1\n', ''),
    })
    packages = adapter.get_installed_packages()
    assert [p.name for p in packages] == ['bash', 'zsh']
    assert packages[0].description == 'The GNU Bourne Again shell'
    assert packages[0].installed is True


def test_void_package_info_and_dependencies(void):
    adapter, _, make_exec = void
    from tui_manager.core.package_adapter import PackageNotFoundError

    adapter.execute_command = make_exec(
        {('xbps-query', '-S', 'curl'): (1, '', 'no encontrado')})
    with pytest.raises(PackageNotFoundError):
        adapter.get_package_info('curl')

    adapter.execute_command = make_exec({
        ('xbps-query', '-S', 'curl'): (0,
            'Architecture: x86_64\n'
            'Descripción:   Herramienta HTTP\n'
            'Versión: 8.5_1\n'
            'Dependencias: openssl, zlib\n'
            'sin separador\n', ''),
    })
    info = adapter.get_package_info('curl')
    assert info.description == 'Herramienta HTTP'
    assert info.version == '8.5_1'
    assert info.dependencies == ['openssl', 'zlib']
    assert adapter.get_dependencies('curl') == ['openssl', 'zlib']

    adapter.execute_command = make_exec(
        {('xbps-query', '-S', 'nope'): (1, '', '')})
    assert adapter.get_dependencies('nope') == []


def test_void_install_and_remove(void, monkeypatch):
    adapter, _, make_exec = void
    adapter.execute_command = make_exec({
        ('xbps-install', '-y', 'curl'): (0, '', ''),
        ('xbps-remove', '-y', 'curl'): (0, '', ''),
    })
    monkeypatch.setattr('builtins.input', lambda _: 's')
    assert adapter.install_package('curl', confirm=True) is True
    assert adapter.remove_package('curl', confirm=True) is True

    monkeypatch.setattr('builtins.input', lambda _: 'n')
    assert adapter.install_package('curl', confirm=True) is False
    assert adapter.remove_package('curl', confirm=True) is False

    adapter.execute_command = make_exec({
        ('xbps-install', '-y', 'curl'): (1, '', 'error'),
        ('xbps-remove', '-y', 'curl'): (1, '', 'error'),
    })
    assert adapter.install_package('curl', confirm=False) is False
    assert adapter.remove_package('curl', confirm=False) is False


def test_void_search_packages(void):
    adapter, _, make_exec = void
    adapter.execute_command = make_exec(
        {('xbps-query', '-Rs', 'http'): (1, '', 'error')})
    assert adapter.search_packages('http') == []

    adapter.execute_command = make_exec({
        ('xbps-query', '-Rs', 'http'): (0,
            '\nsin corchetes\n'
            '[*] curl-8.5_1 Herramienta HTTP\n'
            '[-] wget-1.21_1\n'
            '[b] nombre-sin-version\n', ''),
    })
    packages = adapter.search_packages('http')
    assert [(p.name, p.installed) for p in packages] == [
        ('curl', True), ('wget', False)]
    assert packages[1].description == ''


def test_void_updates_and_cache(void):
    adapter, _, make_exec = void
    adapter.execute_command = make_exec({('xbps-install', '-n'): (1, '', 'e')})
    assert adapter.get_updates_available() == []

    adapter.execute_command = make_exec({
        ('xbps-install', '-n'): (0, '\nmalo\ncurl-8.5_1 update to 9.0\n', ''),
    })
    assert [p.name for p in adapter.get_updates_available()] == ['curl']

    adapter.execute_command = make_exec({('xbps-install', '-S'): (0, '', '')})
    assert adapter.update_cache() is True
    adapter.execute_command = make_exec({('xbps-install', '-S'): (1, '', 'e')})
    assert adapter.update_cache() is False


def test_void_orphans(void):
    adapter, _, make_exec = void
    adapter.execute_command = make_exec({('xbps-remove', '-y', '-o'): (1, '', 'e')})
    assert adapter.remove_orphans() is False
    adapter.execute_command = make_exec({('xbps-remove', '-y', '-o'): (0, '', '')})
    assert adapter.remove_orphans() is True

    adapter.execute_command = make_exec({('xbps-remove', '-o', '-n'): (1, '', 'e')})
    assert adapter.get_orphans() == []
    adapter.execute_command = make_exec({
        ('xbps-remove', '-o', '-n'): (0, 'libfoo-1.0_1\nmalo\n', ''),
    })
    assert [p.name for p in adapter.get_orphans()] == ['libfoo']

    adapter.execute_command = make_exec({('xbps-remove', '-o', '-y'): (1, '', 'e')})
    assert adapter.clean_orphans(confirm=False) is False
    adapter.execute_command = make_exec({('xbps-remove', '-o', '-y'): (0, '', '')})
    assert adapter.clean_orphans(confirm=False) is True


def test_void_get_category(void):
    adapter, _, _ = void
    assert adapter._get_category('firefox').startswith('[')
    assert isinstance(adapter._get_category('paquete-desconocido-xyz'), str)


# ==========================================================================
# event.py
# ==========================================================================

def test_event_emitter_full_api():
    from tui_manager.core.event import EventEmitter, EVENTS

    emitter = EventEmitter()
    seen = []

    def callback(a, b=0):
        seen.append((a, b))
        return a + b

    assert emitter.on('x', callback) is callback
    assert emitter.has_listeners('x') is True
    assert emitter.has_listeners('otro') is False
    assert emitter.listeners_count('x') == 1
    assert emitter.get_event_names() == ['x']
    assert emitter.emit('x', 1, b=2) == [3]
    assert seen == [(1, 2)]

    def broken(*args, **kwargs):
        raise RuntimeError('fallo')

    emitter.on('x', broken)
    assert emitter.emit('x', 2, b=3) == [5]  # el error se swallowea
    assert emitter.off('x', broken) is True
    assert emitter.off('x', broken) is False
    assert emitter.off('desconocido', callback) is False

    emitter.on('y', callback)
    assert emitter.clear('x') == 1
    assert emitter.listeners_count() == 1
    assert emitter.clear() == 1
    assert emitter.listeners_count() == 0
    assert emitter.emit('x') == []
    assert 'package.installed' in EVENTS
    assert 'theme.changed' in EVENTS


# ==========================================================================
# config.py
# ==========================================================================

def test_config_full_api(tmp_path):
    import logging
    from tui_manager.core.config import Config

    archivo = str(tmp_path / 'config.yaml')
    cfg = Config(config_file=archivo)
    assert cfg.get('clave-inexistente', 'valor') == 'valor'
    assert 'theme' in cfg.get_all()

    cfg.set_all({'theme': 'light', 'language': 'en'})
    assert Config(config_file=archivo).get_all()['theme'] == 'light'

    cfg.reset_to_default()
    assert cfg.get_theme() == 'dark'
    cfg.remove_key('theme')
    assert cfg.get('theme') is None
    cfg.remove_key('theme')  # clave ya ausente: no hace nada

    cfg.set_theme('retro')
    assert cfg.get_theme() == 'retro'
    cfg.set_refresh_interval(0)
    assert cfg.get_refresh_interval() == 1
    cfg.set_refresh_interval(7)
    assert cfg.get_refresh_interval() == 7
    cfg.set_auto_update(False)
    assert cfg.get_auto_update() is False
    cfg.set_show_details(False)
    assert cfg.get_show_details() is False
    cfg.set_sort_by('version')
    assert cfg.get_sort_by() == 'version'
    cfg.set_sort_order('desc')
    assert cfg.get_sort_order() == 'desc'
    cfg.set_default_category('red')
    assert cfg.get_default_category() == 'red'

    for nombre, nivel in (('debug', logging.DEBUG), ('info', logging.INFO),
                          ('warning', logging.WARNING),
                          ('error', logging.ERROR),
                          ('critical', logging.CRITICAL)):
        cfg.config['log_level'] = nombre
        assert cfg.get_log_level() == nivel
    cfg.config['log_level'] = 'desconocido'
    assert cfg.get_log_level() == logging.INFO


def test_config_error_paths(tmp_path, monkeypatch):
    from tui_manager.core.config import Config, ConfigError

    malformed = tmp_path / 'malformed.yaml'
    malformed.write_text('clave: [1, 2')
    assert Config(config_file=str(malformed)).get_all() == Config.DEFAULT_CONFIG

    roto = tmp_path / 'roto.yaml'
    roto.write_text('clave: 1')
    real_open = open

    def boom(path, *args, **kwargs):
        if os.fspath(path) == str(roto):
            raise OSError('no se puede leer')
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr('builtins.open', boom)
    assert Config(config_file=str(roto)).get_all() == Config.DEFAULT_CONFIG

    cfg = Config(config_file=str(tmp_path / 'sin' / 'directorio' / 'c.yaml'))

    def no_makedirs(*args, **kwargs):
        raise OSError('solo lectura')

    monkeypatch.setattr(os, 'makedirs', no_makedirs)
    with pytest.raises(ConfigError):
        cfg.save_config()


# ==========================================================================
# distribution.py
# ==========================================================================

@pytest.fixture
def dd():
    import tui_manager.core.distribution as module
    return module


def _isolated_distro(monkeypatch):
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setenv('PREFIX', '/usr')


def _lsb(monkeypatch, si=None, ds=None, rs=None):
    table = {}
    if si is not None:
        table[('lsb_release', '-si')] = si
    if ds is not None:
        table[('lsb_release', '-ds')] = ds
    if rs is not None:
        table[('lsb_release', '-rs')] = rs
    _fake_commands(monkeypatch, table)


def test_distribution_detect_release_files(dd, monkeypatch):
    _isolated_distro(monkeypatch)
    monkeypatch.setattr(os.path, 'exists', lambda p: p == '/etc/os-release')
    _patch_open(monkeypatch, {'/etc/os-release': "NAME=X\nID='arch'\n"})
    assert dd.DistributionDetector.detect() == 'arch'

    monkeypatch.setattr(os.path, 'exists', lambda p: p == '/etc/lsb-release')
    _patch_open(monkeypatch, {'/etc/lsb-release': 'ID=linuxmint\n'})
    assert dd.DistributionDetector.detect() == 'linuxmint'

    # ID vacío → se continúa con los release files específicos
    monkeypatch.setattr(
        os.path, 'exists',
        lambda p: p in ('/etc/os-release', '/etc/fedora-release'))
    _patch_open(monkeypatch, {'/etc/os-release': 'ID=\n'})
    assert dd.DistributionDetector.detect() == 'fedora'

    # error al leer el release file → se registra y se continúa
    monkeypatch.setattr(os.path, 'exists', lambda p: p == '/etc/os-release')
    monkeypatch.setattr(
        'builtins.open',
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError('no')))
    _lsb(monkeypatch, si=(0, 'Void\n', ''))
    assert dd.DistributionDetector.detect() == 'void'


def test_distribution_detect_fallbacks(dd, monkeypatch):
    _isolated_distro(monkeypatch)
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    _lsb(monkeypatch, si=(0, 'Alpine\n', ''))
    assert dd.DistributionDetector.detect() == 'alpine'

    _lsb(monkeypatch, si=FileNotFoundError())
    monkeypatch.setattr(platform, 'system', lambda: 'DragonFly')
    assert dd.DistributionDetector.detect() == 'dragonfly'
    monkeypatch.setattr(platform, 'system', lambda: 'OpenBSD')
    assert dd.DistributionDetector.detect() == 'openbsd'


def test_distribution_names_versions_and_helpers(dd, monkeypatch):
    detector = dd.DistributionDetector
    real_open = open
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    _lsb(monkeypatch, ds=(0, 'Debian GNU/Linux 12\n', ''), rs=(0, '12\n', ''))
    assert detector.get_distro_name() == 'Debian GNU/Linux 12'
    assert detector.get_distro_version() == '12'

    monkeypatch.setattr(os.path, 'exists', lambda p: p == '/etc/os-release')
    _patch_open(monkeypatch, {'/etc/os-release': (
        'PRETTY_NAME="Fedora 40"\nVERSION_ID="40"\n')})
    _lsb(monkeypatch, ds=FileNotFoundError(), rs=FileNotFoundError())
    assert detector.get_distro_name() == 'Fedora 40'
    assert detector.get_distro_version() == '40'

    # sin lsb_release ni os-release legible → cae a detect()
    def no_release(path, *args, **kwargs):
        if os.fspath(path) == '/etc/os-release':
            raise OSError('no disponible')
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr('builtins.open', no_release)
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    monkeypatch.setattr(detector, 'detect', staticmethod(lambda: 'void'))
    assert detector.get_distro_name() == 'void'
    assert detector.get_distro_version() == 'unknown'
    assert detector.get_package_manager() == 'xbps'
    assert detector.is_supported() is True
    assert detector.get_distro_info()['package_manager'] == 'xbps'

    monkeypatch.setattr(detector, 'detect', staticmethod(lambda: 'plan9'))
    assert detector.get_package_manager() == 'unknown'
    assert detector.is_supported() is False


# ==========================================================================
# package_adapter.py (clase base)
# ==========================================================================

def test_package_adapter_base_not_implemented():
    from tui_manager.core.package_adapter import PackageAdapter, Package

    adapter = PackageAdapter()
    calls = [
        ('get_installed_packages', ()),
        ('get_package_info', ('x',)),
        ('install_package', ('x',)),
        ('remove_package', ('x',)),
        ('search_packages', ('x',)),
        ('update_cache', ()),
        ('get_updates_available', ()),
        ('get_dependencies', ('x',)),
    ]
    for name, args in calls:
        with pytest.raises(NotImplementedError):
            getattr(adapter, name)(*args)
    assert adapter.get_orphans() == []
    assert adapter.clean_orphans() is False
    assert Package('x').dependencies == []
    assert Package('x').recommends == []


def test_package_adapter_execute_command(monkeypatch, fake_runner):
    from tui_manager.core.package_adapter import PackageAdapter

    adapter = PackageAdapter()
    fake_runner.expect(['sudo', '-n', 'true'], rc=0)
    fake_runner.expect(['sudo', '-n', 'apt', 'update'], rc=0, stdout='ok')
    assert adapter.execute_command(['apt', 'update']) == (0, 'ok', '')
    assert fake_runner.calls[-1] == ('sudo', '-n', 'apt', 'update')
    fake_runner.expect(['apt', 'list'], rc=0)
    assert adapter.execute_command(['apt', 'list'], sudo=False) == (0, '', '')

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd='apt', timeout=1)

    monkeypatch.setattr(adapter, '_credentials_cached', lambda tool: True)
    monkeypatch.setattr(subprocess, 'run', timeout)
    assert adapter.execute_command(['apt']) == (-1, '', 'Timeout')

    def boom(*args, **kwargs):
        raise RuntimeError('error raro')

    monkeypatch.setattr(subprocess, 'run', boom)
    assert adapter.execute_command(['apt']) == (-1, '', 'error raro')


# ==========================================================================
# sources_adapter.py (fachada TUI)
# ==========================================================================

def test_sources_adapter_facade(monkeypatch):
    import tui_manager.core.sources_adapter as module

    class FakeManager:
        def __init__(self):
            self.preferred_format = 'deb'

        def build_sources(self, app):
            return ['fuente']

        def get_source_summary(self, app):
            return 'resumen'

        def has_alternative_sources(self, app):
            return True

        def set_preferred_format(self, fmt):
            self.preferred_format = fmt

        def _execute_install(self, app, source):
            return ('ok', app, source)

    monkeypatch.setattr(module, 'AlternativeSourceManager',
                        lambda config=None: FakeManager())
    adapter = module.SourcesAdapter(config=object())
    app = type('App', (), {'name': 'Firefox', 'description': 'Navegador'})()
    source = type('Source', (), {
        'describe': lambda self: 'descripción',
        'is_official': True,
    })()

    assert adapter.list_apps() and all(a.name for a in adapter.list_apps())
    # la búsqueda normaliza a minúsculas y filtra por nombre/descripción
    assert adapter.list_apps(query='firefox') == adapter.list_apps(query='FIREFOX')
    assert adapter.list_apps(query='no-existe-app-xyz') == []
    assert adapter.get_app('firefox') is not None
    assert adapter.get_app('no-existe-app-xyz') is None
    assert adapter.categories()
    assert adapter.sources_for(app) == ['fuente']
    assert adapter.source_summary(app) == 'resumen'
    assert adapter.has_alternatives(app) is True
    assert adapter.preferred_format() == 'deb'
    adapter.set_preferred_format('appimage')
    assert adapter.preferred_format() == 'appimage'
    assert adapter.install(app, source) == ('ok', app, source)
    assert adapter.describe_source(source) == 'descripción'
    assert adapter.is_official(source) is True


# ==========================================================================
# process_monitor.py
# ==========================================================================

def _proc(pid=100, user='u', cpu=1.0, mem=2.0, vsz=4096, rss=2048,
          command='cmd'):
    from tui_manager.core.process_monitor import Process
    return Process(pid=pid, user=user, cpu=cpu, mem=mem, vsz=vsz, rss=rss,
                   nice=0, start='08:00', time='0:01', command=command)


def test_pm_process_helpers(monkeypatch):
    process = _proc(rss=4096, vsz=8192)
    assert process.get_memory_usage_mb() == 4.0
    assert process.get_virtual_memory_mb() == 8.0
    assert process.to_dict()['pid'] == 100

    _patch_open(monkeypatch, {
        '/proc/100/status': 'Name:\tcmd\nState:\tS (sleeping)\n',
        '/proc/100/stat': '100 (cmd) S 1 2 3\n',
    })
    assert process.get_status() == 'S (sleeping)'
    assert process.get_ppid() == 1

    _patch_open(monkeypatch, {
        '/proc/100/status': FileNotFoundError(),
        '/proc/100/stat': FileNotFoundError(),
    })
    assert process.get_status() == 'unknown'
    assert process.get_ppid() == 0


def _ps_output():
    return (
        'USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND\n'
        'root 1 0.1 0.2 10240 4096 ? Ss 08:00 0:01 /sbin/init\n'
        'u 100 15.5 3.2 512000 131072 ? Sl 09:00 1:02 firefox\n'
        'u 200 2.0 1.0 20480 10240 ? S 10:00 0:02 curl\n'
        '\n'
        'linea-mal-formateada\n'
    )


def test_pm_get_processes_and_filters(monkeypatch):
    import tui_manager.core.process_monitor as module
    _fake_commands(monkeypatch, {('ps', 'aux'): (0, _ps_output(), '')})
    monitor = module.ProcessMonitor()

    all_processes = monitor.get_processes()
    assert [p.pid for p in all_processes] == [1, 100, 200]
    assert monitor.get_processes(offset=1, limit=1)[0].pid == 100
    assert [p.pid for p in monitor.get_processes(filters={'user': 'u'})] == [100, 200]
    assert [p.pid for p in monitor.get_processes(filters={'name': 'FIRE'})] == [100]
    assert [p.pid for p in monitor.get_processes(filters={'min_cpu': 10})] == [100]
    assert [p.pid for p in monitor.get_processes(filters={'max_cpu': 1})] == [1]
    assert [p.pid for p in monitor.get_processes(filters={'min_mem': 100})] == [100]
    assert [p.pid for p in monitor.get_processes(filters={'max_mem': 10})] == [1, 200]
    assert [p.pid for p in monitor.get_processes(filters={'pid': 200})] == [200]

    assert monitor.get_process_by_pid(100).pid == 100
    with pytest.raises(module.ProcessNotFoundError):
        monitor.get_process_by_pid(999)

    assert monitor.get_total_cpu_usage() == pytest.approx(17.6)
    assert [p.pid for p in monitor.get_top_processes(count=2)] == [100, 200]
    assert [p.pid for p in monitor.get_top_processes(count=2, by='mem')] == [100, 200]


def test_pm_subprocess_and_audit_branches(monkeypatch):
    import tui_manager.core.process_monitor as module

    def boom(*args, **kwargs):
        raise OSError('ps no disponible')

    monkeypatch.setattr(subprocess, 'run', boom)
    monitor = module.ProcessMonitor()
    assert monitor.get_processes() == []

    class FakeAudit:
        def __init__(self):
            self.records = []

        def record(self, action, target, result):
            self.records.append((action, target, result))

    audit = FakeAudit()
    monitor = module.ProcessMonitor(audit_log=audit)

    _fake_commands(monkeypatch, {
        ('kill', '-s', '15', '100'): (0, '', ''),
        ('kill', '-s', '9', '200'): (1, '', 'sin permiso'),
        ('renice', '5', '-p', '100'): (0, '', ''),
        ('renice', '-5', '-p', '200'): (1, '', 'fallo'),
    })
    assert monitor.kill_process(100) is True
    assert monitor.kill_process(200, signal=9) is False
    assert monitor.renice_process(100, 5) is True
    assert monitor.renice_process(200, -5) is False
    assert audit.records == [
        ('kill_process', '100', True),
        ('kill_process', '200', False),
        ('renice_process', '100', True),
        ('renice_process', '200', False),
    ]

    def no_signal(*args, **kwargs):
        raise OSError('sin señal')

    monkeypatch.setattr(subprocess, 'run', no_signal)
    assert monitor.kill_process(100) is False
    assert monitor.renice_process(100, 0) is False


def test_pm_memory_usage(monkeypatch):
    import tui_manager.core.process_monitor as module
    _patch_open(monkeypatch, {'/proc/meminfo': (
        'MemTotal:       2048000 kB\n'
        'MemFree:         512000 kB\n'
        'MemAvailable:   1024000 kB\n'
    )})
    usage = module.ProcessMonitor().get_total_memory_usage()
    assert usage['total'] == 2000.0
    assert usage['free'] == 500.0
    assert usage['available'] == 1000.0
    assert usage['used'] == 1500.0
    assert usage['percentage'] == 75.0

    _patch_open(monkeypatch, {
        '/proc/meminfo': 'MemFree: 512000 kB\n',
    })
    assert module.ProcessMonitor().get_total_memory_usage() == {
        'total': 0, 'used': 0, 'free': 0, 'available': 0, 'percentage': 0}
