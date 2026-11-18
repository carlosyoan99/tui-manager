"""
B · Info del sistema para la pantalla «Acerca de» [OM].

Todo portable: /proc/meminfo en Linux, sysctl en BSD, fallback honesto a
None («N/D») cuando no hay dato. Sin subprocesos salvo lo existente.
"""

from __future__ import annotations

import os
import platform
import shutil


def _ram_total_mb() -> str:
    try:  # Linux
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal'):
                    kb = int(line.split()[1])
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


def _disk_root() -> str:
    try:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        used_pct = int(usage.used / usage.total * 100)
        return f'{usage.total // (1024 ** 3)} GB ({used_pct}% usado)'
    except OSError:
        return ''


def collect(distribution: str = '', environment=None,
            system_control=None, package_manager=None,
            os_release=None) -> dict:
    """Reúne los campos de la pantalla Acerca de.

    Args inyectables para tests: os_release (SO de display), environment
    (adapter con .name), system_control (batería), package_manager (N paquetes).
    """
    info = {
        'os': os_release or f'{platform.system()} {platform.release()} '
                            f'({platform.machine()})',
        'kernel': platform.release(),
        'distro': distribution or '—',
        'environment': getattr(environment, 'name', '—') or '—',
        'cpu': (str(os.cpu_count() or '?') + ' núcleos'),
        'ram': _ram_total_mb(),
        'disk': _disk_root(),
        'battery': None,
        'packages': None,
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


def _run(cmd, timeout=10):
    import subprocess
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return -1, '', str(exc)
