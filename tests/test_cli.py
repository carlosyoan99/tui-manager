"""
Tests de la CLI (main.py): --version y --doctor.

El doctor usa las detecciones reales del entorno de test (Termux u otro);
se verifica estructura del informe, no valores concretos del SO anfitrión.
"""

import subprocess

import pytest

from tui_manager import __version__
from tui_manager import main as main_module
from tui_manager.main import CLI_VERSION_COMMANDS, _cli_version, main, run_doctor


def test_cli_version(capsys):
    assert main(['--version']) == 0
    out = capsys.readouterr().out
    assert f'tui-manager {__version__}' in out


def test_cli_doctor_exits_zero(capsys):
    assert main(['--doctor']) == 0
    out = capsys.readouterr().out
    assert 'TUI Manager' in out


def test_doctor_report_sections():
    report = run_doctor()
    lines = report.splitlines()
    # etiquetas clave del informe (i18n)
    assert any('SO' in l or 'OS' in l for l in lines)
    assert any('Python' in l for l in lines)
    assert any('textual' in l for l in lines)
    assert any('Config' in l for l in lines)


def test_cli_invalid_lang_exits_with_error(capsys):
    with pytest.raises(SystemExit):
        main(['--lang', 'fr'])


# ------------------------------------------- B2-2: --doctor ampliado --------

def test_doctor_reports_cli_versions(monkeypatch):
    """Informa de las 5 CLIs y solo invoca `<cli> --version` (nunca acciones)."""
    versions = {
        'apt': 'apt 2.6.1',
        'pacman': 'Pacman v6.0.1',
        'dnf': '4.14.0',
        'pkg': 'pkg 1.20.9',
        'xbps-query': 'xbps-query 0.59.1',
    }
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(tuple(cmd))
        assert cmd[1:] == ['--version'], 'solo se permite `--version`'
        assert kwargs.get('check') is False
        assert kwargs.get('capture_output') is True
        return subprocess.CompletedProcess(
            cmd, 0, stdout=versions[cmd[0]], stderr='')

    monkeypatch.setattr(main_module.subprocess, 'run', fake_run)
    report = run_doctor()

    assert sorted(calls) == sorted(
        (cli, '--version') for cli in CLI_VERSION_COMMANDS)
    for cli, version in versions.items():
        assert cli in report
        assert version in report


@pytest.mark.parametrize('cli', CLI_VERSION_COMMANDS)
def test_cli_version_graceful_fallback(monkeypatch, cli):
    """Ausente, error o salida vacía → «N/D», sin lanzar excepción."""
    def missing(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(main_module.subprocess, 'run', missing)
    assert _cli_version(cli) == 'N/D'

    def failing(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout='', stderr='falló')

    monkeypatch.setattr(main_module.subprocess, 'run', failing)
    assert _cli_version(cli) == 'N/D'

    def empty(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout='', stderr='')

    monkeypatch.setattr(main_module.subprocess, 'run', empty)
    assert _cli_version(cli) == 'N/D'


def test_cli_version_uses_first_line_of_stderr(monkeypatch):
    """Algunas CLIs imprimen la versión en stderr: se captura igualmente."""
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, 0, stdout='', stderr='apt 2.7.14\notros detalles')

    monkeypatch.setattr(main_module.subprocess, 'run', fake_run)
    assert _cli_version('apt') == 'apt 2.7.14'


def test_cli_version_skips_ascii_art(monkeypatch):
    """pacman --version empieza con arte ASCII: se toma la línea con versión."""
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, 0,
            stdout='.--.\nPacman v7.1.0 - libalpm v16.0.1\nCopyright (C)',
            stderr='')

    monkeypatch.setattr(main_module.subprocess, 'run', fake_run)
    assert _cli_version('pacman') == 'Pacman v7.1.0 - libalpm v16.0.1'


def test_doctor_reports_environment_capabilities(monkeypatch):
    """Las capacidades vienen de `environment.capabilities()`."""
    from tui_manager.core.environment import Capability, EnvironmentAdapter

    class FakeEnv(EnvironmentAdapter):
        name = 'fake-env'

        def capabilities(self):
            return {Capability.SET_WALLPAPER, Capability.LOCK_SCREEN}

    monkeypatch.setattr(main_module.EnvironmentDetector, 'detect',
                        staticmethod(lambda: FakeEnv()))
    report = run_doctor()
    assert 'FakeEnv' in report  # etiqueta = tipo del adapter detectado
    assert 'set_wallpaper' in report
    assert 'lock_screen' in report
