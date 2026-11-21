"""
Tests de la salida `--json` (tarea 1.2-B del PLAN-1.2).

Todos los datos son simulados (FakeRunner/monkeypatch): **no se ejecuta
ningún subprocess real**. Se valida el contrato estable del documento,
la separación stdout/stderr y que no se mezclan logs con el JSON.
"""

import json
import logging
import sys

import pytest

from tui_manager import __version__
from tui_manager import cli_json
from tui_manager import main as main_module
from tui_manager.main import CLI_VERSION_COMMANDS, main
from tui_manager.core.package_adapter import Package
from tui_manager.core.process_monitor import Process

STABLE_KEYS = {'version', 'distribution', 'items'}


class _FakePackageManager:
    def __init__(self, packages):
        self._packages = list(packages)

    def get_installed_packages(self, *args, **kwargs):
        return list(self._packages)


class _FakeProcessMonitor:
    def __init__(self, processes):
        self._processes = list(processes)

    def get_processes(self, *args, **kwargs):
        return list(self._processes)


def _patch_distro(monkeypatch, distro='debian'):
    """Fija la detección de distro (la clase es compartida con main.py)."""
    monkeypatch.setattr(cli_json.DistributionDetector, 'detect',
                        staticmethod(lambda: distro))


# --------------------------------------------------------------------------
# Contrato estable del documento.
# --------------------------------------------------------------------------

def test_json_packages_schema(monkeypatch, capsys):
    _patch_distro(monkeypatch, 'debian')
    pkg = Package(name='htop', version='3.2.2', description='Monitor',
                  installed=True, size='300 kB', category='system',
                  dependencies=['libc6'], recommends=[])
    monkeypatch.setattr(cli_json, 'PackageManager',
                        lambda distribution=None: _FakePackageManager([pkg]))

    assert main(['--json', 'packages']) == 0
    doc = json.loads(capsys.readouterr().out)

    assert set(doc) == STABLE_KEYS
    assert doc['version'] == __version__
    assert doc['distribution'] == 'debian'
    assert len(doc['items']) == 1
    item = doc['items'][0]
    assert set(item) == {
        'name', 'version', 'description', 'installed', 'size',
        'category', 'dependencies', 'recommends',
    }
    assert item['name'] == 'htop'
    assert item['version'] == '3.2.2'
    assert item['installed'] is True
    assert item['dependencies'] == ['libc6']


def test_json_processes_schema(monkeypatch, capsys):
    _patch_distro(monkeypatch, 'arch')
    proc = Process(pid=42, user='root', cpu=1.5, mem=0.2, vsz=1000, rss=200,
                   nice=0, start='10:00', time='0:01', command='python')
    monkeypatch.setattr(cli_json, 'ProcessMonitor',
                        lambda: _FakeProcessMonitor([proc]))

    assert main(['--json', 'processes']) == 0
    doc = json.loads(capsys.readouterr().out)

    assert set(doc) == STABLE_KEYS
    assert doc['distribution'] == 'arch'
    assert doc['items'] == [proc.to_dict()]


def test_build_document_with_explicit_distribution(monkeypatch):
    """Si se pasa la distro, no se vuelve a detectar."""
    monkeypatch.setattr(cli_json, 'ProcessMonitor',
                        lambda: _FakeProcessMonitor([]))
    doc = cli_json.build_document('processes', distribution='termux')
    assert set(doc) == STABLE_KEYS
    assert doc['distribution'] == 'termux'
    assert doc['items'] == []


# --------------------------------------------------------------------------
# Doctor: reutiliza la lógica compartida, sin duplicar subprocess.
# --------------------------------------------------------------------------

def test_json_doctor_reuses_shared_cli_version_logic(monkeypatch, capsys):
    _patch_distro(monkeypatch, 'debian')
    calls = []
    versions = {cli: f'{cli} 1.2.3' for cli in CLI_VERSION_COMMANDS}

    def fake_cli_version(cli):
        calls.append(cli)
        return versions[cli]

    monkeypatch.setattr(main_module, '_cli_version', fake_cli_version)

    from tui_manager.core.environment import Capability, EnvironmentAdapter

    class FakeEnv(EnvironmentAdapter):
        name = 'fake-env'

        def capabilities(self):
            return {Capability.SET_WALLPAPER}

    monkeypatch.setattr(main_module.EnvironmentDetector, 'detect',
                        staticmethod(lambda: FakeEnv()))

    assert main(['--json', 'doctor']) == 0
    doc = json.loads(capsys.readouterr().out)

    assert set(doc) == STABLE_KEYS
    assert calls == ['apt']  # solo la CLI relevante de la distro (debian)
    reported = {i['key']: i['value'] for i in doc['items']
                if i['key'] in versions}
    assert reported == {'apt': versions['apt']}
    assert all(i['type'] in {'diagnostic', 'suggestion'}
               for i in doc['items'])
    assert any(i['key'] == 'doctor.python' for i in doc['items'])


def test_json_doctor_collects_once(monkeypatch, capsys):
    """La recolección del doctor se invoca una sola vez por documento."""
    calls = []
    data = {
        'distribution': 'freebsd',
        'rows': [{'key': 'doctor.os', 'value': 'FreeBSD 14', 'warn': False}],
        'suggestions': [],
    }

    def collect():
        calls.append(1)
        return data

    monkeypatch.setattr(main_module, 'collect_doctor_data', collect)

    assert main(['--json', 'doctor']) == 0
    doc = json.loads(capsys.readouterr().out)

    assert len(calls) == 1
    assert doc['distribution'] == 'freebsd'
    assert doc['items'][0]['value'] == 'FreeBSD 14'


# --------------------------------------------------------------------------
# Errores y aislamiento de streams.
# --------------------------------------------------------------------------

def test_json_error_goes_to_stderr_with_exit_1(monkeypatch, capsys):
    _patch_distro(monkeypatch)

    def boom(distribution=None):
        raise RuntimeError('fallo simulado')

    monkeypatch.setattr(cli_json, 'PackageManager', boom)

    assert main(['--json', 'packages']) == 1
    captured = capsys.readouterr()
    assert captured.out == ''
    assert 'fallo simulado' in captured.err


def test_json_does_not_mix_logging_into_stdout(monkeypatch, capsys):
    """Ni un handler StreamHandler(sys.stdout) contamina el documento."""
    _patch_distro(monkeypatch)

    def noisy_manager(distribution=None):
        logging.getLogger('ruidoso').info('RUIDO DE LOG')
        return _FakePackageManager([])

    monkeypatch.setattr(cli_json, 'PackageManager', noisy_manager)

    root = logging.getLogger()
    old_level = root.level
    handler = logging.StreamHandler(sys.stdout)
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        assert main(['--json', 'packages']) == 0
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)

    out = capsys.readouterr().out
    doc = json.loads(out)
    assert 'RUIDO DE LOG' not in out
    assert doc['items'] == []


def test_json_rejects_unknown_kind(capsys):
    with pytest.raises(SystemExit):
        main(['--json', 'no-existe'])
    assert 'invalid choice' in capsys.readouterr().err
