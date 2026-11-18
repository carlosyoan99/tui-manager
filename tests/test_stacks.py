"""
Tests simulados de stacks por rol, fwupd opcional y snapshots sobre .bak-tm.

Nunca se instala nada real ni se ejecuta fwupdmgr: los adapters son dobles
de prueba o adaptadores reales con ``execute_command`` interceptado.
"""
import subprocess
from pathlib import Path

import pytest

from tui_manager.core.app_catalog import STACKS, get_app_by_name
from tui_manager.core.stacks import (
    StackInstaller, StackInstallResult, UnknownStackError, fwupd_available,
)
from tui_manager.core.snapshots import (
    UnsafePathError, SnapshotNotFoundError,
    snapshot_config, restore_config,
)


class FakeAdapter:
    """Doble de adapter: registra llamadas y simula éxito/fracaso."""

    def __init__(self, fail=(), raise_on=()):
        self.fail = set(fail)
        self.raise_on = set(raise_on)
        self.calls = []

    def install_package(self, name, confirm=False):
        self.calls.append((name, confirm))
        if name in self.raise_on:
            raise RuntimeError(f'fallo simulado al instalar {name}')
        return name not in self.fail


# ---------------------------------------------------------------- stacks ----
def test_stacks_defined_for_three_roles():
    assert set(STACKS) == {'dev', 'terminal', 'web'}
    for role, packages in STACKS.items():
        assert isinstance(packages, list) and len(packages) >= 3, role
        assert len(packages) == len(set(packages)), role
        for package in packages:
            assert get_app_by_name(package) is not None, f'{role}: {package}'


def test_install_stack_returns_one_result_per_package():
    adapter = FakeAdapter()
    result = StackInstaller().install_stack('dev', adapter, confirm=False)

    assert isinstance(result, dict)
    assert set(result) == set(STACKS['dev'])
    assert all(result.values())
    assert result.success is True and result.failed == []
    assert result.installed == STACKS['dev']
    assert [name for name, _ in adapter.calls] == STACKS['dev']
    assert all(confirm is False for _, confirm in adapter.calls)


def test_install_stack_uses_adapter_from_constructor():
    adapter = FakeAdapter()
    result = StackInstaller(adapter).install_stack('web')
    assert isinstance(result, StackInstallResult)
    assert result.success is True
    assert [name for name, _ in adapter.calls] == STACKS['web']


def test_install_stack_continues_after_failures():
    adapter = FakeAdapter(fail={'git'}, raise_on={'gdb'})
    result = StackInstaller().install_stack('dev', adapter)

    assert result['git'] is False       # install_package devolvió False
    assert result['gdb'] is False       # install_package lanzó excepción
    assert result.failed == ['git', 'gdb']
    assert 'python3' in result.installed
    assert result.success is False
    # El lote completo se intenta aunque haya fallos parciales.
    assert {name for name, _ in adapter.calls} == set(STACKS['dev'])


@pytest.mark.parametrize('module_name,class_name', [
    ('debian_adapter', 'DebianAdapter'),
    ('arch_adapter', 'ArchAdapter'),
])
def test_install_stack_simulated_in_debian_and_arch(
        monkeypatch, module_name, class_name):
    """Adaptadores reales, pero sin ejecutar ningún comando del sistema."""
    import importlib
    module = importlib.import_module(f'tui_manager.core.{module_name}')
    adapter = getattr(module, class_name)()

    calls = []

    def fake_execute(command, sudo=True):
        calls.append((tuple(command), sudo))
        return 0, '', ''

    def no_real_subprocess(*args, **kwargs):
        raise AssertionError('No se debe ejecutar ningún comando real')

    monkeypatch.setattr(adapter, 'execute_command', fake_execute)
    monkeypatch.setattr(subprocess, 'run', no_real_subprocess)

    result = StackInstaller().install_stack('terminal', adapter, confirm=False)

    assert result.success is True
    assert len(calls) == len(STACKS['terminal'])
    for command, sudo in calls:
        assert command[-1] in STACKS['terminal']
        assert sudo is True


def test_install_all_roles():
    result = StackInstaller().install_all(FakeAdapter())
    assert set(result) == set(STACKS)
    assert all(item.success for item in result.values())


def test_unknown_stack_role_rejected():
    with pytest.raises(UnknownStackError):
        StackInstaller().install_stack('no-existe', FakeAdapter())


# ------------------------------------------------------------------ fwupd ----
def test_fwupd_available_detects_without_executing(monkeypatch):
    import shutil
    seen = []

    def fake_which(command):
        seen.append(command)
        return '/usr/bin/fwupdmgr'

    def no_real_subprocess(*args, **kwargs):
        raise AssertionError('fwupdmgr nunca debe ejecutarse')

    monkeypatch.setattr(shutil, 'which', fake_which)
    monkeypatch.setattr(subprocess, 'run', no_real_subprocess)

    assert fwupd_available() is True
    assert seen == ['fwupdmgr']


def test_fwupd_unavailable(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, 'which', lambda command: None)
    assert fwupd_available() is False


# -------------------------------------------------------------- snapshots ----
def test_snapshot_and_restore_preserve_original_bak_tm(tmp_path):
    cfg = tmp_path / 'bar.conf'
    cfg.write_text('configuración previa', encoding='utf-8')
    sidecar = tmp_path / 'bar.conf.bak-tm'
    sidecar.write_text('backup original', encoding='utf-8')
    store = tmp_path / 'store'

    manifest = snapshot_config('bar', [cfg], base_dir=store)
    # El .bak-tm preexistente NO se sobrescribe al snapshotear.
    assert sidecar.read_text(encoding='utf-8') == 'backup original'
    assert manifest['items'][0]['original'] == str(cfg)

    cfg.write_text('configuración modificada', encoding='utf-8')
    restored = restore_config('bar', base_dir=store)

    assert restored == {str(cfg): True}
    assert cfg.read_text(encoding='utf-8') == 'configuración previa'
    assert sidecar.exists()
    assert sidecar.read_text(encoding='utf-8') == 'backup original'


def test_snapshot_creates_sidecar_when_missing(tmp_path):
    cfg = tmp_path / 'wm.conf'
    cfg.write_text('A', encoding='utf-8')
    sidecar = tmp_path / 'wm.conf.bak-tm'
    store = tmp_path / 'store'
    assert not sidecar.exists()

    snapshot_config('wm', [str(cfg)], base_dir=store)
    assert sidecar.read_text(encoding='utf-8') == 'A'

    cfg.write_text('B', encoding='utf-8')
    restore_config('wm', base_dir=store)
    assert cfg.read_text(encoding='utf-8') == 'A'
    assert sidecar.read_text(encoding='utf-8') == 'A'


@pytest.mark.parametrize('relative', [
    'btrfs/home/.config/x',
    '@home/.config/x',
    '.zfs/config/x',
    '.snapshots/config/x',
])
def test_snapshot_rejects_btrfs_zfs_paths(tmp_path, relative):
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('x', encoding='utf-8')

    with pytest.raises(UnsafePathError):
        snapshot_config('sys', [path], base_dir=tmp_path / 'store')
    assert not (tmp_path / 'store').exists()


def test_snapshot_rejects_absolute_system_path(tmp_path):
    # La ruta se rechaza antes de leerla: no se toca /proc ni nada del sistema.
    with pytest.raises(UnsafePathError):
        snapshot_config('sys', [Path('/proc/cpuinfo')],
                        base_dir=tmp_path / 'store')
    assert not (tmp_path / 'store').exists()


@pytest.mark.parametrize('name', ['', '.', '..', '../escape', 'a/b', 'con espacio'])
def test_snapshot_invalid_names_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        snapshot_config(name, [tmp_path / 'x'], base_dir=tmp_path / 'store')


def test_restore_unknown_snapshot(tmp_path):
    with pytest.raises(SnapshotNotFoundError):
        restore_config('inexistente', base_dir=tmp_path / 'store')


def test_multiple_named_snapshots_are_independent(tmp_path):
    a = tmp_path / 'a.conf'
    b = tmp_path / 'b.conf'
    a.write_text('a1', encoding='utf-8')
    b.write_text('b1', encoding='utf-8')
    store = tmp_path / 'store'

    snapshot_config('first', [a], base_dir=store)
    snapshot_config('second', [b], base_dir=store)
    a.write_text('a2', encoding='utf-8')
    b.write_text('b2', encoding='utf-8')

    restore_config('first', base_dir=store)
    assert a.read_text(encoding='utf-8') == 'a1'
    assert b.read_text(encoding='utf-8') == 'b2'
    assert (tmp_path / 'a.conf.bak-tm').read_text(encoding='utf-8') == 'a1'
    assert (tmp_path / 'b.conf.bak-tm').read_text(encoding='utf-8') == 'b1'
