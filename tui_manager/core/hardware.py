"""
I · Capacidades de hardware: detección de SOLO LECTURA [OM].

Spec: roadmap post-1.0, función I. Reglas:

1. Nunca se ejecuta nada que cambie el sistema: hibernación se comprueba
   con ``systemctl hibernate --dry-run`` (o ``pmset -g`` / ``powercfg /a``,
   que solo consultan), y el resto son lecturas de ``/sys`` u órdenes de
   inventario (``lspci``, ``sysctl``, ``getprop``, ``rfkill``, ...).
2. Todo subproceso pasa por un ``runner`` inyectable. Bajo pytest, sin
   inyección, el runner no ejecuta nada ( patrón de ``core/sysinfo.py`` ).
3. El resultado es ``dict[HardwareCapability, bool | str]``: ``True`` cuando
   la capacidad existe; si no, una clave i18n ``hardware.reason.*`` que la UI
   traduce con ``t()``. El core no importa i18n (plano separado).
"""
from __future__ import annotations

import logging
import os
import platform
import shutil
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional, Union

logger = logging.getLogger(__name__)

# Rutas de datos (monkeypatchables en tests: nunca subprocess real).
BACKLIGHT_PATH = '/sys/class/backlight'
POWER_SUPPLY_PATH = '/sys/class/power_supply'
POWER_STATE_PATH = '/sys/power/state'


class HardwareCapability(Enum):
    """Capacidades de hardware detectables en la pantalla Sistema."""

    HIBERNATE = auto()
    SCREENSAVER = auto()
    BRIGHTNESS = auto()
    BATTERY = auto()
    GPU = auto()
    BLUETOOTH = auto()
    WIFI = auto()


# Motivos de no disponibilidad: claves i18n, traducidas en la UI.
REASON_NO_HIBERNATE = 'hardware.reason.no_hibernate'
REASON_NO_SCREENSAVER = 'hardware.reason.no_screensaver'
REASON_NO_BACKLIGHT = 'hardware.reason.no_backlight'
REASON_NO_BATTERY = 'hardware.reason.no_battery'
REASON_NO_GPU = 'hardware.reason.no_gpu'
REASON_NO_BLUETOOTH = 'hardware.reason.no_bluetooth'
REASON_NO_WIFI = 'hardware.reason.no_wifi'

REASON_KEYS = (
    REASON_NO_HIBERNATE, REASON_NO_SCREENSAVER, REASON_NO_BACKLIGHT,
    REASON_NO_BATTERY, REASON_NO_GPU, REASON_NO_BLUETOOTH, REASON_NO_WIFI,
)

Status = Union[bool, str]


def _effective_runner(runner: Optional[Callable]):
    """Runner inyectado; en tests sin inyección no ejecuta nada."""
    if runner is not None:
        return runner
    if 'pytest' in sys.modules:
        return lambda cmd, timeout=5: (1, '', '')
    import subprocess

    def _run(cmd, timeout=5):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except Exception as exc:  # binario ausente, timeout, permisos...
            return -1, '', str(exc)

    return _run


def _ask(runner: Callable, cmd: list, timeout: int = 5) -> tuple:
    """Consulta de solo lectura vía runner; nunca propaga excepciones."""
    try:
        result = runner(cmd, timeout=timeout)
    except Exception as exc:
        logger.debug('detección hardware: %s no disponible (%s)', cmd, exc)
        return -1, '', str(exc)
    if isinstance(result, tuple):
        return result
    return (getattr(result, 'returncode', -1),
            getattr(result, 'stdout', ''),
            getattr(result, 'stderr', ''))


def _has(out: str, *needles: str) -> bool:
    text = str(out or '').lower()
    return any(needle in text for needle in needles)


def _entries(path: str) -> list:
    """Entradas de un directorio simulable; lista vacía si no existe."""
    try:
        return list(Path(path).iterdir())
    except OSError:
        return []


def _safe(detector: Callable, reason: str) -> Status:
    """Degrada a ``reason`` si un detector falla inesperadamente."""
    try:
        return detector()
    except Exception as exc:
        logger.debug('detección hardware fallida: %s', exc)
        return reason


# --- Detectores individuales (todos de solo lectura) ------------------------

def _detect_brightness(backlight_path: str) -> Status:
    return True if _entries(backlight_path) else REASON_NO_BACKLIGHT


def _detect_battery(runner: Callable, system: str,
                    power_supply_path: str) -> Status:
    if os.environ.get('TERMUX_VERSION'):
        code, out, _ = _ask(runner, ['termux-battery-status'])
        return True if code == 0 and out.strip() else REASON_NO_BATTERY
    if system == 'Darwin':
        code, out, _ = _ask(runner, ['pmset', '-g', 'batt'])
        return True if code == 0 and out.strip() else REASON_NO_BATTERY
    if system == 'Windows':
        code, out, _ = _ask(runner, ['wmic', 'path', 'win32_battery',
                                     'get', 'batterystatus'])
        if code == 0 and any(line.strip().isdigit()
                             for line in (out or '').splitlines()):
            return True
        return REASON_NO_BATTERY
    for entry in _entries(power_supply_path):
        try:
            kind = (entry / 'type').read_text().strip().lower()
        except OSError:
            continue
        if kind == 'battery':
            return True
    return REASON_NO_BATTERY


def _detect_hibernate(runner: Callable, system: str,
                      power_state_path: str) -> Status:
    # --dry-run / -g / /a: ninguno cambia el estado del equipo.
    if system == 'Darwin':
        code, out, _ = _ask(runner, ['pmset', '-g'])
        if code == 0 and _has(out, 'hibernatemode'):
            return True
        return REASON_NO_HIBERNATE
    if system == 'Windows':
        code, out, _ = _ask(runner, ['powercfg', '/a'])
        if code == 0 and _has(out, 'hibernate'):
            return True
        return REASON_NO_HIBERNATE
    code, _, _ = _ask(runner, ['systemctl', 'hibernate', '--dry-run'])
    if code == 0:
        return True
    # systemd ausente o sin permisos: /sys/power/state también es lectura.
    try:
        if 'disk' in Path(power_state_path).read_text().lower():
            return True
    except OSError:
        pass
    return REASON_NO_HIBERNATE


def _detect_screensaver(which: Callable) -> Status:
    tools = ('xscreensaver-command', 'gnome-screensaver-command',
             'xset', 'caffeinate')
    for tool in tools:
        try:
            if which(tool):
                return True
        except Exception:
            continue
    return REASON_NO_SCREENSAVER


def _detect_gpu(runner: Callable, system: str) -> Status:
    if os.environ.get('TERMUX_VERSION'):
        code, out, _ = _ask(runner, ['getprop', 'ro.gpu'])
        return True if code == 0 and out.strip() else REASON_NO_GPU
    if system == 'Darwin':
        code, out, _ = _ask(runner,
                            ['system_profiler', 'SPDisplaysDataType'])
        return True if code == 0 and _has(out, 'chipset model:', 'vendor:',
                                         'gpu', 'graphics') else REASON_NO_GPU
    if system == 'Windows':
        code, out, _ = _ask(runner, ['wmic', 'path', 'win32_videocontroller',
                                     'get', 'name'])
        if code == 0 and any(line.strip() and not line.strip().islower()
                             for line in (out or '').splitlines()[1:]):
            return True
        return REASON_NO_GPU
    if system in ('FreeBSD', 'NetBSD', 'OpenBSD', 'DragonFly'):
        code, out, _ = _ask(runner, ['sysctl', '-n', 'hw.model'])
        return True if code == 0 and out.strip() else REASON_NO_GPU
    code, out, _ = _ask(runner, ['lspci'])
    return True if code == 0 and _has(out, 'vga compatible controller',
                                      '3d controller', 'display controller') \
        else REASON_NO_GPU


def _detect_bluetooth(runner: Callable, system: str) -> Status:
    if system == 'Windows':
        code, out, _ = _ask(runner, ['powershell', '-NoProfile', '-Command',
                                     'Get-NetAdapter -Name "*Bluetooth*"'])
        return True if code == 0 and out.strip() else REASON_NO_BLUETOOTH
    for cmd, needles in (
        (['rfkill', 'list', 'bluetooth'], ('bluetooth',)),
        (['bluetoothctl', 'show'], ('controller', 'powered')),
    ):
        code, out, _ = _ask(runner, cmd)
        if code == 0 and _has(out, *needles):
            return True
    return REASON_NO_BLUETOOTH


def _detect_wifi(runner: Callable, system: str) -> Status:
    if system == 'Darwin':
        code, out, _ = _ask(runner, ['networksetup',
                                     '-listallhardwareports'])
        return True if code == 0 and _has(out, 'wi-fi', 'airport') \
            else REASON_NO_WIFI
    if system == 'Windows':
        code, out, _ = _ask(runner, ['netsh', 'wlan', 'show', 'interfaces'])
        return True if code == 0 and _has(out, 'ssid', 'wireless') \
            else REASON_NO_WIFI
    for cmd, needles in (
        (['rfkill', 'list', 'wifi'], ('wireless', 'wifi', 'wlan')),
        (['iw', 'dev'], ('interface',)),
    ):
        code, out, _ = _ask(runner, cmd)
        if code == 0 and _has(out, *needles):
            return True
    return REASON_NO_WIFI


def detect_hardware_capabilities(
    runner: Optional[Callable] = None,
    system: Optional[str] = None,
    *,
    backlight_path: Optional[str] = None,
    power_supply_path: Optional[str] = None,
    power_state_path: Optional[str] = None,
    which: Optional[Callable] = None,
) -> dict:
    """Detecta capacidades de hardware sin modificar el sistema.

    Args inyectables para tests: ``runner`` (sustituye subprocess), ``system``
    (sustituye ``platform.system()``), las rutas ``/sys`` (``tmp_path``) y
    ``which`` (para el salvapantallas). Devuelve siempre las 7 capacidades:
    ``True`` o una clave ``hardware.reason.*`` que la UI traduce.
    """
    runner = _effective_runner(runner)
    system = system or platform.system()
    which = which or shutil.which
    backlight_path = backlight_path or BACKLIGHT_PATH
    power_supply_path = power_supply_path or POWER_SUPPLY_PATH
    power_state_path = power_state_path or POWER_STATE_PATH

    return {
        HardwareCapability.HIBERNATE: _safe(
            lambda: _detect_hibernate(runner, system, power_state_path),
            REASON_NO_HIBERNATE),
        HardwareCapability.SCREENSAVER: _safe(
            lambda: _detect_screensaver(which), REASON_NO_SCREENSAVER),
        HardwareCapability.BRIGHTNESS: _safe(
            lambda: _detect_brightness(backlight_path), REASON_NO_BACKLIGHT),
        HardwareCapability.BATTERY: _safe(
            lambda: _detect_battery(runner, system, power_supply_path),
            REASON_NO_BATTERY),
        HardwareCapability.GPU: _safe(
            lambda: _detect_gpu(runner, system), REASON_NO_GPU),
        HardwareCapability.BLUETOOTH: _safe(
            lambda: _detect_bluetooth(runner, system), REASON_NO_BLUETOOTH),
        HardwareCapability.WIFI: _safe(
            lambda: _detect_wifi(runner, system), REASON_NO_WIFI),
    }
