"""
Función I · Capacidades de hardware: detección simulada, sin subprocess real.

Los paths de /sys se sustituyen por ``tmp_path`` y todas las órdenes pasan
por un runner falso. La UI se comprueba con ``run_test()`` y un detector
inyectado: ninguna prueba ejecuta systemctl, lspci ni rfkill de verdad.
"""
import pytest

from tui_manager.core.hardware import (
    REASON_KEYS,
    REASON_NO_BACKLIGHT,
    REASON_NO_BATTERY,
    REASON_NO_BLUETOOTH,
    REASON_NO_GPU,
    REASON_NO_HIBERNATE,
    REASON_NO_SCREENSAVER,
    REASON_NO_WIFI,
    HardwareCapability as C,
    detect_hardware_capabilities,
)
from tui_manager.i18n import STRINGS, set_language, t


class Runner:
    """Runner falso: (rc, stdout, stderr) por comando; nunca subprocess."""

    def __init__(self, canned=None):
        self.canned = canned or {}
        self.calls = []

    def __call__(self, cmd, timeout=5):
        key = tuple(cmd)
        self.calls.append(key)
        return self.canned.get(key, (1, '', ''))


def detect(tmp_path, runner=None, system='Linux', which=None, **overrides):
    options = dict(
        runner=runner or Runner(),
        system=system,
        backlight_path=str(tmp_path / 'backlight'),
        power_supply_path=str(tmp_path / 'power_supply'),
        power_state_path=str(tmp_path / 'power_state'),
        which=which or (lambda tool: None),
    )
    options.update(overrides)
    return detect_hardware_capabilities(**options)


# --- Detección de fuentes simulables ----------------------------------------

def test_backlight_detected_and_missing(tmp_path):
    (tmp_path / 'backlight' / 'intel_backlight').mkdir(parents=True)
    caps = detect(tmp_path)
    assert caps[C.BRIGHTNESS] is True

    caps = detect(tmp_path, backlight_path=str(tmp_path / 'sin_backlight'))
    assert caps[C.BRIGHTNESS] == REASON_NO_BACKLIGHT


def test_battery_from_power_supply_and_missing(tmp_path):
    battery = tmp_path / 'power_supply' / 'BAT0'
    battery.mkdir(parents=True)
    (battery / 'type').write_text('Battery\n')
    caps = detect(tmp_path)
    assert caps[C.BATTERY] is True

    # Un AC0 no cuenta como batería; motivo claro si solo hay el adaptador.
    (battery / 'type').write_text('Mains\n')
    caps = detect(tmp_path)
    assert caps[C.BATTERY] == REASON_NO_BATTERY


def test_gpu_from_lspci_and_missing(tmp_path):
    runner = Runner({
        ('lspci',): (0, '00:02.0 VGA compatible controller: Intel Corp.\n', ''),
    })
    caps = detect(tmp_path, runner=runner)
    assert caps[C.GPU] is True
    assert ('lspci',) in runner.calls

    caps = detect(tmp_path, runner=Runner({('lspci',): (1, '', 'no lspci')}))
    assert caps[C.GPU] == REASON_NO_GPU


def test_gpu_sources_by_platform(tmp_path, monkeypatch):
    runner = Runner({
        ('sysctl', '-n', 'hw.model'): (0, 'AMD Ryzen\n', ''),
        ('getprop', 'ro.gpu'): (0, 'Adreno\n', ''),
    })
    assert detect(tmp_path, runner=runner,
                  system='FreeBSD')[C.GPU] is True
    monkeypatch.setenv('TERMUX_VERSION', '0.118')  # GPU de Termux: getprop
    assert detect(tmp_path, runner=runner,
                  system='Linux')[C.GPU] is True


def test_hibernate_uses_dry_run_never_changes_state(tmp_path):
    runner = Runner({('systemctl', 'hibernate', '--dry-run'): (0, '', '')})
    caps = detect(tmp_path, runner=runner)
    assert caps[C.HIBERNATE] is True
    # Ninguna orden ejecutó una hibernación real.
    assert ('systemctl', 'hibernate', '--dry-run') in runner.calls
    assert all('hibernate' not in call or '--dry-run' in call
               for call in runner.calls)

    # Sin systemctl: /sys/power/state también se lee en modo seguro.
    (tmp_path / 'power_state').write_text('freeze mem disk\n')
    caps = detect(tmp_path, runner=Runner())
    assert caps[C.HIBERNATE] is True

    (tmp_path / 'power_state').write_text('freeze mem\n')
    caps = detect(tmp_path, runner=Runner())
    assert caps[C.HIBERNATE] == REASON_NO_HIBERNATE


def test_wifi_and_bluetooth_from_rfkill(tmp_path):
    runner = Runner({
        ('rfkill', 'list', 'wifi'):
            (0, '0: phy0: Wireless LAN\n\tSoft blocked: no\n', ''),
        ('rfkill', 'list', 'bluetooth'):
            (0, '1: hci0: Bluetooth\n\tSoft blocked: no\n', ''),
    })
    caps = detect(tmp_path, runner=runner)
    assert caps[C.WIFI] is True
    assert caps[C.BLUETOOTH] is True


def test_screensaver_via_injectable_which(tmp_path):
    caps = detect(tmp_path, which=lambda tool: None)
    assert caps[C.SCREENSAVER] == REASON_NO_SCREENSAVER
    caps = detect(tmp_path, which=lambda tool: '/usr/bin/xscreensaver-command'
                  if tool == 'xscreensaver-command' else None)
    assert caps[C.SCREENSAVER] is True


def test_all_capabilities_present_with_readable_reasons(tmp_path):
    caps = detect(tmp_path)
    assert set(caps) == set(C)
    assert all(isinstance(v, (bool, str)) for v in caps.values())
    for reason in (v for v in caps.values() if isinstance(v, str)):
        assert reason in REASON_KEYS

    for lang in ('es', 'en'):
        for key in REASON_KEYS:
            assert key in STRINGS[lang], f'{key} fuera del dict {lang}'
            set_language(lang)
            assert t(key) != key
    set_language('es')


def test_no_real_subprocess_even_with_default_runner(tmp_path, monkeypatch):
    import subprocess

    def boom(*args, **kwargs):
        raise AssertionError('subprocess real ejecutado en un test')

    monkeypatch.setattr(subprocess, 'run', boom)
    # Con runner inyectado y con el runner por defecto bajo pytest.
    assert set(detect(tmp_path)) == set(C)
    caps = detect_hardware_capabilities(system='Linux', which=lambda tool: None,
                                        backlight_path=str(tmp_path / 'backlight'),
                                        power_supply_path=str(tmp_path / 'ps'),
                                        power_state_path=str(tmp_path / 'state'))
    assert set(caps) == set(C)


# --- Integración en la UI ----------------------------------------------------

def _services(tmp_path, monkeypatch):
    from tui_manager.core.config import Config
    from tui_manager.core.environment import EnvironmentAdapter
    from tui_manager.core.theme_manager import ThemeManager
    from tui_manager.ui.app import Services

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    import tui_manager.core.system_control as sc_module
    monkeypatch.setattr(sc_module.shutil, 'which', lambda tool, *a, **k: None)
    config = Config(config_file=str(tmp_path / 'config.yaml'))
    config.config['language'] = 'es'
    set_language('es')
    return Services(config=config, theme_manager=ThemeManager('dark'),
                    environment=EnvironmentAdapter(), distribution='arch')


@pytest.mark.asyncio
async def test_system_screen_hardware_section(tmp_path, monkeypatch):
    from textual.widgets import Static
    from tui_manager.ui.app import TuiManagerApp
    from tui_manager.ui.screens import SystemScreen, MainMenuScreen

    assert len(MainMenuScreen.ENTRIES) == 10  # menú fijo, sin cambios
    caps = {
        C.BRIGHTNESS: True,
        C.BATTERY: REASON_NO_BATTERY,
        C.GPU: REASON_NO_GPU,
        C.HIBERNATE: REASON_NO_HIBERNATE,
        C.SCREENSAVER: REASON_NO_SCREENSAVER,
        C.BLUETOOTH: REASON_NO_BLUETOOTH,
        C.WIFI: REASON_NO_WIFI,
    }
    services = _services(tmp_path, monkeypatch)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(SystemScreen(services, hardware_detector=lambda **kw: caps))
        await pilot.pause()
        for _ in range(30):
            await pilot.pause(0.02)
        assert isinstance(app.screen, SystemScreen)
        text = app.screen.query_one('#hardware-info', Static).content
        assert t('hardware.title') in app.screen.query_one(
            '#hardware-title', Static).content
        assert '✓' in text and '✗' in text
        assert t('hardware.capability.brightness') in text
        assert t(REASON_NO_BATTERY) in text
        # Las acciones siguen intactas: 10 entradas en el ORDER del sistema.
        assert len(app.screen.ORDER) == 10

        # Sin datos: degrada limpiamente, sin traceback ni loading eterno.
        app.push_screen(SystemScreen(services, hardware_detector=lambda **kw: {}))
        await pilot.pause()
        for _ in range(10):
            await pilot.pause(0.02)
        text = app.screen.query_one('#hardware-info', Static).content
        assert t('hardware.empty') in text


def test_hardware_i18n_keys_in_both_languages():
    from tui_manager.core.hardware import HardwareCapability

    keys = (
        'hardware.title', 'hardware.empty', 'hardware.available',
        'hardware.unavailable',
    )
    keys += tuple(f'hardware.capability.{cap.name.lower()}'
                  for cap in HardwareCapability)
    keys += REASON_KEYS
    for lang, strings in STRINGS.items():
        for key in keys:
            assert key in strings, f'{key} falta en {lang}'
    for key in keys:
        assert t(key) != key, f't() devolvió la clave {key}'
