#!/usr/bin/env python3
"""
Prueba prolongada (soak) para el criterio 8 de 1.0.

Repite operaciones de SOLO LECTURA durante `duration` segundos y cuenta
tracebacks. No escribe archivos, no ejecuta red, no instala nada.

Uso:
    python -m tests.soak --duration 120

Salida:
    SOAK host=<uname> duration=...s iterations=... errors=0
    (un error por línea si aparece)
"""
from __future__ import annotations

import argparse
import platform
import time
import traceback

from tui_manager.core.distribution import DistributionDetector
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.process_monitor import ProcessMonitor
from tui_manager.core.sysinfo import collect as sysinfo_collect


def soak(duration: int) -> dict:
    distro = DistributionDetector.detect()
    pm = PackageManager(distribution=distro)
    monitor = ProcessMonitor()
    started = time.monotonic()
    iterations = 0
    errors = []

    while time.monotonic() - started < duration:
        try:
            processes = monitor.get_processes(limit=100)
            assert isinstance(processes, list)
            mem = sysinfo_collect(distribution=distro)
            assert isinstance(mem, dict)
            # Solo lectura; get_installed_packages cacheado en Beta 3.
            packages = pm.get_installed_packages(use_cache=True, limit=100)
            assert isinstance(packages, list)
            iterations += 1
        except Exception as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
            if len(errors) <= 3:
                traceback.print_exc()

    return {
        'host': platform.node(),
        'duration': duration,
        'iterations': iterations,
        'errors': errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Prueba prolongada de solo lectura')
    parser.add_argument('--duration', type=int, default=120)
    args = parser.parse_args()

    result = soak(args.duration)
    print(f"SOAK host={result['host']} duration={result['duration']}s "
          f"iterations={result['iterations']} errors={len(result['errors'])}")
    for err in result['errors'][:10]:
        print(f'  ERROR {err}')
    return 0 if not result['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
