"""
B · Info del sistema para la pantalla «Acerca de» [OM].

Portable: /proc en Linux, sysctl en BSD, fallback honesto a '' / None
(«N/D» en la UI) cuando no hay dato. Sin subprocesos costosos: solo se
usan cuando la plataforma lo requiere (sysctl en BSD, lspci opcional).
"""
from __future__ import annotations

import os
import platform
import shutil
import sys
import time


def _run(cmd, timeout=5):
    import subprocess
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return -1, '', str(exc)


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


def collect(distribution: str = '', environment=None,
            system_control=None, package_manager=None,
            os_release=None) -> dict:
    """Reúne los campos de la pantalla Acerca de.

    Args inyectables para tests: os_release, environment (adapter con .name),
    system_control (batería), package_manager (N paquetes).

    Los campos原有 se mantienen por compatibilidad; los nuevos amplían
    hardware y software.
    """
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
