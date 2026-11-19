"""
B · Info del sistema para la pantalla «Acerca de» [OM].

Portable: /proc en Linux, sysctl en BSD, fallback honesto a '' / None
(«N/D» en la UI) cuando no hay dato. Sin subprocesos costosos: solo se
usan cuando la plataforma lo requiere (sysctl en BSD, lspci opcional).
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import time

# Rutas de datos del sistema (monkeypatchables en tests: nunca subprocess real)
OS_RELEASE_PATH = '/etc/os-release'
DMI_CHASSIS_PATH = '/sys/class/dmi/id/chassis_type'


def _run(cmd, timeout=5):
    import subprocess
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return -1, '', str(exc)


def _noop_runner(cmd, timeout=5):
    """Runner sin comandos reales: se usa por defecto bajo pytest."""
    return 1, '', ''


def _effective_runner(runner):
    """En producción usa _run; bajo pytest, sin inyección, nunca ejecuta nada."""
    if runner is not None:
        return runner
    return _noop_runner if 'pytest' in sys.modules else _run


def _meminfo() -> dict:
    """Lee /proc/meminfo y devuelve MB (Linux)."""
    values = {}
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if ':' in line:
                    key, val = line.split(':', 1)
                    parts = val.split()
                    if parts and parts[0].isdigit():
                        values[key] = int(parts[0]) // 1024  # MB
    except (OSError, ValueError):
        pass
    return values


def _ram_total_mb() -> str:
    try:  # Linux
        kb = None
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal'):
                    kb = int(line.split()[1])
                    break
        if kb is not None:
            return f'{kb // 1024} MB'
    except (OSError, ValueError, IndexError):
        pass
    try:  # FreeBSD/NetBSD
        code, out, _ = _run(['sysctl', '-n', 'hw.physmem'])
        if code == 0 and out.strip().isdigit():
            return f'{int(out.strip()) // (1024 * 1024)} MB'
    except Exception:
        pass
    return ''


def _cpu_model() -> str:
    """Modelo de CPU desde /proc/cpuinfo, sysctl o lscpu."""
    try:
        with open('/proc/cpuinfo') as f:
            for line in f:
                if line.startswith('model name'):
                    return line.split(':', 1)[1].strip()
    except OSError:
        pass
    for cmd in (['sysctl', '-n', 'hw.model'], ['lscpu']):
        code, out, _ = _run(cmd)
        if code == 0 and out.strip():
            if cmd[0] == 'lscpu':
                for line in out.splitlines():
                    if line.startswith('Model name:'):
                        return line.split(':', 1)[1].strip()
            else:
                return out.strip()
    return ''


def _uptime() -> str:
    """Tiempo de actividad en formato legible."""
    try:
        with open('/proc/uptime') as f:
            seconds = int(float(f.read().split()[0]))
    except (OSError, ValueError, IndexError):
        code, out, _ = _run(['sysctl', '-n', 'kern.boottime'])
        if code == 0 and out.strip():
            return out.strip()
        return ''
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    parts = []
    if days:
        parts.append(f'{days} d')
    if hours:
        parts.append(f'{hours} h')
    parts.append(f'{minutes} min')
    return ' '.join(parts)


def _disk_root() -> str:
    try:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        used_pct = int(usage.used / usage.total * 100)
        return f'{usage.total // (1024 ** 3)} GB ({used_pct}% usado)'
    except OSError:
        return ''


def _disk_details() -> dict:
    try:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        return {
            'total': f'{usage.total // (1024 ** 3)} GB',
            'used': f'{usage.used // (1024 ** 3)} GB',
            'free': f'{usage.free // (1024 ** 3)} GB',
            'percent': int(usage.used / usage.total * 100),
        }
    except OSError:
        return {}


# ---------------- detectores estilo fastfetch (subprocess simulable) --------
#
# Toda llamada externa pasa por el ``runner`` inyectable (por defecto ``_run``,
# que a su vez usa subprocess.run). En tests se inyecta un runner falso o se
# monkeypatchea subprocess.run: NUNCA se ejecuta un comando real.


def _clean(value) -> str:
    """Limpia un valor KEY=value de os-release (comillas y espacios)."""
    if value is None:
        return ''
    return value.strip().strip('"').strip("'").strip()


def _read_text(path: str) -> str:
    """Lee texto de un archivo de sistema; fallo honesto a ''."""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    except (OSError, ValueError):
        return ''


def _parse_os_release(text: str) -> dict:
    values = {}
    for line in (text or '').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        values[key.strip()] = _clean(val)
    return values


def _os_version(os_release_text=None) -> str:
    """VERSION_ID o VERSION de os-release; PRETTY_NAME si no hay versión."""
    text = os_release_text
    if text is None:
        text = _read_text(OS_RELEASE_PATH)
    values = _parse_os_release(text)
    return (values.get('VERSION_ID') or values.get('VERSION')
            or values.get('PRETTY_NAME', '') or '')


def _is_termux() -> bool:
    return (bool(os.environ.get('TERMUX_VERSION'))
            or 'com.termux' in os.environ.get('PREFIX', ''))


def _device_name(runner, termux=False) -> str:
    """Hostname; en Termux, modelo del equipo vía getprop."""
    if termux:
        code, out, _ = runner(['getprop', 'ro.product.model'], timeout=5)
        if code == 0 and out.strip():
            return out.strip()
    try:
        return os.uname().nodename
    except (AttributeError, OSError):
        return os.environ.get('HOSTNAME', '')


_LAPTOP_CHASSIS = {'8', '9', '10', '11', '12', '14', '15', '28', '29',
                   '30', '31'}
_DESKTOP_CHASSIS = {'3', '4', '5', '6', '7', '13', '16', '17', '18', '19',
                    '20', '21', '22', '23', '24', '25', '26', '27'}


def _device_type(runner, termux=False) -> str:
    """Termux / VM / laptop / desktop; '' si no hay dato fiable."""
    if termux:
        return 'Termux'
    code, out, _ = runner(['systemd-detect-virt'], timeout=5)
    if code == 0 and out.strip() and out.strip().lower() != 'none':
        return 'VM'
    chassis = _read_text(DMI_CHASSIS_PATH).strip()
    if chassis in _LAPTOP_CHASSIS:
        return 'laptop'
    if chassis in _DESKTOP_CHASSIS:
        return 'desktop'
    return ''


def _detect_gpu(runner, termux=False, system='') -> str:
    """GPU: getprop en Termux, sysctl en BSD, lspci (VGA/3D) en Linux."""
    if termux:
        code, out, _ = runner(['getprop', 'ro.gpu'], timeout=5)
        return out.strip() if code == 0 and out.strip() else ''
    if system in ('FreeBSD', 'NetBSD', 'OpenBSD', 'DragonFly'):
        code, out, _ = runner(['sysctl', '-n', 'hw.model'], timeout=5)
        return out.strip() if code == 0 and out.strip() else ''
    code, out, _ = runner(['lspci'], timeout=5)
    if code == 0 and out:
        for line in out.splitlines():
            low = line.lower()
            if 'vga' in low or '3d controller' in low:
                parts = line.split(None, 1)
                desc = parts[1] if len(parts) > 1 else line
                if ':' in desc:
                    desc = desc.split(':', 1)[1]
                desc = desc.strip()
                if desc:
                    return desc
    return ''


def _parse_hyprctl(out: str) -> list:
    name = ''
    res = ''
    for line in out.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('Monitor '):
            tail = s.split(None, 1)[1].strip() if len(s.split(None, 1)) > 1 else ''
            name = tail.split()[0] if tail else ''
            continue
        tokens = s.split()
        first = tokens[0] if tokens else ''
        if 'x' in first and '@' in first and first[:1].isdigit():
            res = first
            break
    text = (name + ' ' + res).strip()
    return [text] if text else []


def _parse_sway(out: str) -> list:
    try:
        data = json.loads(out)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return []
    first = data[0]
    name = str(first.get('name', '') or '')
    rect = first.get('rect') or {}
    width = rect.get('width') if isinstance(rect, dict) else None
    height = rect.get('height') if isinstance(rect, dict) else None
    res = f'{width}x{height}' if width and height else ''
    text = (name + ' ' + res).strip()
    return [text] if text else []


def _parse_xrandr(out: str) -> list:
    for line in out.splitlines():
        if ' connected' not in line:
            continue
        parts = line.split()
        name = parts[0] if parts else ''
        res = ''
        for token in parts[1:]:
            if token and token[:1].isdigit() and 'x' in token and '+' in token:
                res = token.split('+', 1)[0]
                break
        text = (name + ' ' + res).strip()
        if text:
            return [text]
    return []


def _displays(runner) -> list:
    """Resolución del primer monitor: hyprctl → swaymsg → xrandr."""
    for cmd, parser in (
        (['hyprctl', 'monitors'], _parse_hyprctl),
        (['swaymsg', '-t', 'get_outputs'], _parse_sway),
        (['xrandr', '--query'], _parse_xrandr),
    ):
        code, out, _ = runner(cmd, timeout=5)
        if code == 0 and out.strip():
            result = parser(out)
            if result:
                return result
    return []


def _session() -> str:
    parts = []
    for key in ('XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'WAYLAND_DISPLAY'):
        val = os.environ.get(key, '')
        if val:
            parts.append(val)
    return ' · '.join(parts)


def collect(distribution: str = '', environment=None,
            system_control=None, package_manager=None,
            os_release=None, *, runner=None, os_release_text=None,
            pm_name=None) -> dict:
    """Reúne los campos de la pantalla Acerca de.

    Args inyectables para tests: os_release, environment (adapter con .name),
    system_control (batería), package_manager (N paquetes). Los nuevos:
    runner (callable que sustituye subprocess), os_release_text (contenido de
    os-release), pm_name (nombre del gestor de paquetes). Ningún test ejecuta
    subprocess real: se inyecta un runner falso.

    Los campos原有 se mantienen por compatibilidad; los nuevos amplían
    hardware y software.
    """
    runner = _effective_runner(runner)
    termux = _is_termux()
    system = platform.system()

    if pm_name is None:
        try:
            from tui_manager.core.distribution import DistributionDetector
            pm_name = DistributionDetector.get_package_manager()
        except Exception:
            pm_name = ''

    mem = _meminfo()
    ram_total = mem.get('MemTotal', 0)
    ram_avail = mem.get('MemAvailable', mem.get('MemFree', 0))
    swap_total = mem.get('SwapTotal', 0)
    swap_free = mem.get('SwapFree', 0)

    ram_detail = ''
    if ram_total:
        used = ram_total - ram_avail
        pct = int(used / ram_total * 100)
        ram_detail = (f'{ram_total} MB_total · {used} MB usada · '
                      f'{pct}%')

    swap_detail = ''
    if swap_total:
        swap_used = swap_total - swap_free
        swap_detail = f'{swap_total} MB · {swap_used} MB usada'

    disk = _disk_details()
    cores = os.cpu_count() or 0

    info = {
        # --- campos originales (compatibilidad) ---
        'os': os_release or f'{platform.system()} {platform.release()} '
                            f'({platform.machine()})',
        'kernel': platform.release(),
        'distro': distribution or '—',
        'environment': getattr(environment, 'name', '—') or '—',
        'cpu': (str(cores or '?') + ' núcleos'),
        'ram': _ram_total_mb(),
        'disk': f'{disk["total"]} ({disk["percent"]}% usado)' if disk else '',
        'battery': None,
        'packages': None,

        # --- nuevos: software ---
        'hostname': os.uname().nodename if hasattr(os, 'uname') else '',
        'user': os.environ.get('USER', ''),
        'platform': platform.platform(),
        'arch': platform.machine(),
        'python': f'{sys.version_info.major}.{sys.version_info.minor}.'
                  f'{sys.version_info.micro}',
        'python_impl': platform.python_implementation(),
        'shell': os.environ.get('SHELL', ''),
        'term': os.environ.get('TERM', ''),
        'uptime': _uptime(),

        # --- nuevos: hardware ---
        'cpu_model': _cpu_model(),
        'cpu_logical': cores,
        'cpu_physical': _physical_cores(cores),
        'ram_total': f'{ram_total} MB' if ram_total else '',
        'ram_available': f'{ram_avail} MB' if ram_avail else '',
        'ram_detail': ram_detail,
        'swap': swap_detail,
        'disk_total': disk.get('total', ''),
        'disk_used': disk.get('used', ''),
        'disk_free': disk.get('free', ''),
        'disk_percent': disk.get('percent', 0),

        # --- nuevos: estilo fastfetch (datos ausentes → '' / []) ---
        'os_version': _os_version(os_release_text),
        'device_name': _device_name(runner, termux),
        'device_type': _device_type(runner, termux),
        'gpu': _detect_gpu(runner, termux, system),
        'package_manager': pm_name or '',
        'displays': _displays(runner),
        'session': _session(),
    }

    if system_control is not None:
        try:
            info['battery'] = system_control.battery_status()
        except Exception:
            info['battery'] = None
    if package_manager is not None:
        try:
            info['packages'] = len(package_manager.get_installed_packages())
        except Exception:
            info['packages'] = None
    return info


def _physical_cores(logical: int) -> int:
    """Estima núcleos físicos (mejor esfuerzo, portable)."""
    try:
        with open('/proc/cpuinfo') as f:
            physical = set()
            core_ids = set()
            for line in f:
                if line.startswith('physical id'):
                    physical.add(line.split(':', 1)[1].strip())
                elif line.startswith('core id'):
                    core_ids.add(line.split(':', 1)[1].strip())
            if physical and core_ids:
                return len(physical) * len(core_ids)
    except OSError:
        pass
    return max(1, logical // 2) if logical else 0
