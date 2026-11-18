"""
B3-1 — Medición y optimización de rendimiento.

Benchmarks con ``time.perf_counter()`` y fakes: 5000 paquetes simulados,
paginación (ventana de filas) y verificación de que la caché evita
recomputar.  Nunca se lanza un subprocess real.
"""

import time

import pytest

from tui_manager.core.package_adapter import Package
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.perf import (
    PackageCache, format_result, measure_call, paginate,
)


# ---------------- Fakes ----------------

def make_packages(count=5000):
    """Genera ``count`` paquetes simulados (sin tocar el sistema)."""
    return [
        Package(
            name=f'pkg-{i:05d}',
            version='1.0',
            description=f'Paquete simulado {i}',
            installed=True,
            category='system' if i % 2 else 'other',
        )
        for i in range(count)
    ]


class CountingPackageAdapter:
    """Adapter falso que cuenta cuántas veces se le pide el listado."""

    def __init__(self, packages):
        self.packages = packages
        self.calls = 0

    def get_installed_packages(self):
        self.calls += 1
        # Copia la lista para simular el coste de consultar el gestor real,
        # sin lanzar subprocess. El periodo de la copia escala con N.
        return list(self.packages)


class FakeCompleted:
    """Sustituto mínimo de subprocess.CompletedProcess."""

    def __init__(self, stdout):
        self.stdout = stdout
        self.stderr = ''
        self.returncode = 0


def make_ps_aux(count=5000):
    """Salida falsa de `ps aux` con ``count`` procesos."""
    lines = ['USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND']
    for i in range(count):
        lines.append(
            f'user {i + 1} 0.1 0.2 10240 4096 ? S 08:00 0:01 proc-{i:05d}'
        )
    return '\n'.join(lines)


def make_package_manager(adapter):
    """PackageManager con distribución fija y adapter inyectado (sin IO)."""
    pm = PackageManager(distribution='debian')
    pm.adapter = adapter
    return pm


# ---------------- perf.py: medición y formato ----------------

def test_measure_call_reports_elapsed_value_and_format():
    def work():
        return sum(range(1000))

    measurement = measure_call(work, name='suma')
    assert measurement.name == 'suma'
    assert measurement.value == sum(range(1000))
    assert measurement.elapsed >= 0
    assert measurement.calls == 1
    text = measurement.format()
    assert 'suma' in text and 'ms' in text


def test_measure_call_repeat_and_format_result():
    measurement = measure_call(lambda x: x + 1, 41, name='inc', repeat=3)
    assert measurement.value == 42
    assert measurement.calls == 3
    assert measurement.average_ms >= 0
    assert '3 llamadas' in str(measurement)

    formatted = format_result('manual', 0.0125, calls=2, precision=2)
    assert formatted == 'manual: 12.50 ms [media 6.25 ms] (2 llamadas)'


def test_measure_call_rejects_zero_repeat():
    with pytest.raises(ValueError):
        measure_call(lambda: None, repeat=0)


# ---------------- perf.py: paginación ----------------

def test_paginate_returns_window_without_mutating():
    items = list(range(10))
    assert list(paginate(items, offset=2, limit=3)) == [2, 3, 4]
    assert list(paginate(items, offset=8, limit=5)) == [8, 9]
    assert list(paginate(items, offset=99)) == []
    assert list(paginate(items, offset=-5, limit=2)) == [0, 1]
    assert list(paginate(items, limit=0)) == []
    assert items == list(range(10))  # intacto


# ---------------- perf.py: PackageCache ----------------

def test_package_cache_hits_misses_and_invalidation():
    calls = []

    def factory():
        calls.append(1)
        return ['a', 'b']

    cache = PackageCache()
    assert cache.get('installed', factory) == ['a', 'b']
    assert cache.get('installed', factory) == ['a', 'b']
    assert len(calls) == 1  # el factory se ejecutó una sola vez

    stats = cache.stats()
    assert stats == {'hits': 1, 'misses': 1, 'size': 1}

    cache.invalidate('installed')
    assert cache.size == 0
    assert cache.get('installed', factory) == ['a', 'b']
    assert len(calls) == 2
    assert cache.stats()['misses'] == 2

    cache.set('otra', [1])
    cache.clear()
    assert cache.size == 0 and cache.stats()['hits'] == 1


# ---------------- PackageManager: caché opcional ----------------

def test_cache_disabled_by_default_keeps_behaviour():
    adapter = CountingPackageAdapter(make_packages(20))
    pm = make_package_manager(adapter)

    pm.get_installed_packages()
    pm.get_installed_packages()
    assert adapter.calls == 2  # sin caché, se consulta siempre


def test_cache_avoids_recomputing_installed_packages():
    adapter = CountingPackageAdapter(make_packages(5000))
    pm = make_package_manager(adapter)

    first = pm.get_installed_packages(use_cache=True)
    second = pm.get_installed_packages(use_cache=True)
    assert len(first) == len(second) == 5000
    assert first == second
    assert adapter.calls == 1  # clave: la caché evita recomputar
    assert pm._package_cache.stats() == {'hits': 1, 'misses': 1, 'size': 1}


def test_invalidate_cache_forces_recompute():
    adapter = CountingPackageAdapter(make_packages(10))
    pm = make_package_manager(adapter)

    pm.get_installed_packages(use_cache=True)
    pm.get_installed_packages(use_cache=True)
    assert adapter.calls == 1

    pm.invalidate_cache()
    pm.get_installed_packages(use_cache=True)
    assert adapter.calls == 2


def test_filters_work_with_cache():
    packages = make_packages(100)
    adapter = CountingPackageAdapter(packages)
    pm = make_package_manager(adapter)

    systems = pm.get_installed_packages(
        filters={'category': 'system'}, use_cache=True)
    by_name = pm.get_installed_packages(
        filters={'name': 'pkg-00042'}, use_cache=True)
    assert len(systems) == 50
    assert [p.name for p in by_name] == ['pkg-00042']
    assert adapter.calls == 1  # un solo listado, dos filtrados distintos


def test_cached_list_is_not_exposed_to_mutation():
    adapter = CountingPackageAdapter(make_packages(5))
    pm = make_package_manager(adapter)

    window = pm.get_installed_packages(use_cache=True)
    window.clear()
    assert len(pm.get_installed_packages(use_cache=True)) == 5


# ---------------- Benchmarks (<500 ms con fakes) ----------------

def test_benchmark_5000_packages_pagination_under_500ms():
    packages = make_packages(5000)
    adapter = CountingPackageAdapter(packages)
    pm = make_package_manager(adapter)

    start = time.perf_counter()
    first = measure_call(pm.get_installed_packages, use_cache=True,
                         name='carga_inicial')
    assert len(first.value) == 5000

    # 50 ventanas de 100 filas recorren los 5000 paquetes paginados.
    total_rows = 0
    for page in range(50):
        window = pm.get_installed_packages(use_cache=True,
                                           offset=page * 100, limit=100)
        assert len(window) == 100
        total_rows += len(window)
    elapsed = time.perf_counter() - start

    assert total_rows == 5000
    assert adapter.calls == 1
    assert elapsed < 0.5, f"paginar 5000 paquetes tardó {elapsed * 1000:.1f} ms"
    assert first.elapsed < 0.5


def test_benchmark_uncached_vs_cached():
    """La versión cacheada no debe repetir el listado costoso."""
    packages = make_packages(5000)
    cached_adapter = CountingPackageAdapter(packages)
    uncached_adapter = CountingPackageAdapter(packages)
    cached_pm = make_package_manager(cached_adapter)
    uncached_pm = make_package_manager(uncached_adapter)

    start = time.perf_counter()
    for _ in range(20):
        cached_pm.get_installed_packages(use_cache=True, offset=0, limit=50)
    cached_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(20):
        uncached_pm.get_installed_packages(offset=0, limit=50)
    uncached_elapsed = time.perf_counter() - start

    assert cached_adapter.calls == 1
    assert uncached_adapter.calls == 20
    assert cached_elapsed < 0.5 and uncached_elapsed < 0.5
    # Misma cantidad de llamadas: la caché hace menos trabajo en cada una.
    assert cached_adapter.calls < uncached_adapter.calls


def test_benchmark_process_window_with_fake_ps(monkeypatch):
    """Ventana de filas de procesos, con `ps aux` simulado (sin subprocess)."""
    import subprocess
    from tui_manager.core.process_monitor import ProcessMonitor

    output = make_ps_aux(5000)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(tuple(cmd))
        return FakeCompleted(output)

    monkeypatch.setattr(subprocess, 'run', fake_run)
    monitor = ProcessMonitor()

    start = time.perf_counter()
    window = monitor.get_processes(offset=2000, limit=100)
    elapsed = time.perf_counter() - start

    assert len(window) == 100
    assert window[0].pid == 2001
    assert window[-1].pid == 2100
    assert calls == [('ps', 'aux')]
    assert elapsed < 0.5, f"ventana de procesos tardó {elapsed * 1000:.1f} ms"


def test_process_pagination_combines_with_filters(monkeypatch):
    import subprocess
    from tui_manager.core.process_monitor import ProcessMonitor

    def fake_run(cmd, **kwargs):
        return FakeCompleted(make_ps_aux(200))

    monkeypatch.setattr(subprocess, 'run', fake_run)
    monitor = ProcessMonitor()
    window = monitor.get_processes(filters={'pid': 1}, offset=0, limit=5)
    assert [p.pid for p in window] == [1]
