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
    """Informa de todas las CLIs y solo invoca `<cli> --version` si existen."""
    versions = {
        'apt': 'apt 2.6.1',
        'pacman': 'Pacman v6.0.1',
        'dnf': '4.14.0',
        'pkg': 'pkg 1.20.9',
        'xbps-query': 'xbps-query 0.59.1',
        'brew': 'Homebrew 4.2.1',
        'winget': 'v1.7.10582',
        'scoop': 'Current Version: 0.5.1',
        'choco': 'Chocolatey v2.2.2',
    }
    assert set(versions) == set(CLI_VERSION_COMMANDS)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(tuple(cmd))
        assert cmd[1:] == ['--version'], 'solo se permite `--version`'
        assert kwargs.get('check') is False
        assert kwargs.get('capture_output') is True
        return subprocess.CompletedProcess(
            cmd, 0, stdout=versions[cmd[0]], stderr='')

    def fake_which(command, *args, **kwargs):
        return f'/usr/bin/{command}'

    monkeypatch.setattr(main_module.subprocess, 'run', fake_run)
    monkeypatch.setattr(main_module.shutil, 'which', fake_which)
    report = run_doctor()

    assert sorted(calls) == sorted(
        (cli, '--version') for cli in CLI_VERSION_COMMANDS)
    for cli, version in versions.items():
        assert cli in report
        assert version in report


def test_doctor_cli_commands_include_macos_and_windows():
    """macOS (brew) y Windows (winget/scoop/choco) están en el doctor."""
    for cli in ('brew', 'winget', 'scoop', 'choco'):
        assert cli in CLI_VERSION_COMMANDS


def test_doctor_skips_absent_clis_without_running_them(monkeypatch):
    """Un comando no instalado se reporta N/D sin llegar a ejecutarse."""
    present = ('apt', 'pacman', 'dnf', 'pkg', 'xbps-query')
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(tuple(cmd))
        return subprocess.CompletedProcess(
            cmd, 0, stdout=f'{cmd[0]} 1.0', stderr='')

    def fake_which(command, *args, **kwargs):
        return f'/usr/bin/{command}' if command in present else None

    monkeypatch.setattr(main_module.subprocess, 'run', fake_run)
    monkeypatch.setattr(main_module.shutil, 'which', fake_which)
    report = run_doctor()

    assert sorted(calls) == sorted((cli, '--version') for cli in present)
    for cli in CLI_VERSION_COMMANDS:
        if cli not in present:
            assert any(line.strip().startswith(cli) and 'N/D' in line
                       for line in report.splitlines()), cli


@pytest.mark.parametrize('cli', CLI_VERSION_COMMANDS)
def test_cli_version_graceful_fallback(monkeypatch, cli):
    """Ausente, error o salida vacía → «N/D», sin lanzar excepción."""
    # Fingimos que la CLI existe para ejercitar también las 3 rutas de error
    # del subprocess (shutil.which se comprueba en test_doctor_skips_absent).
    monkeypatch.setattr(main_module.shutil, 'which',
                        lambda name, *a, **k: f'/usr/bin/{name}')

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

    monkeypatch.setattr(main_module.shutil, 'which',
                        lambda name, *a, **k: '/usr/bin/apt')
    monkeypatch.setattr(main_module.subprocess, 'run', fake_run)
    assert _cli_version('apt') == 'apt 2.7.14'


def test_cli_version_skips_ascii_art(monkeypatch):
    """pacman --version empieza con arte ASCII: se toma la línea con versión."""
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, 0,
            stdout='.--.\nPacman v7.1.0 - libalpm v16.0.1\nCopyright (C)',
            stderr='')

    monkeypatch.setattr(main_module.shutil, 'which',
                        lambda name, *a, **k: '/usr/bin/pacman')
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


# ---------------------------------- 1.2-A: --quickstart (onboarding) --------

def test_cli_quickstart_exits_zero_and_tours_ten_entries(capsys):
    """--quickstart muestra las 10 entradas con atajo, nombre y descripción."""
    from tui_manager.i18n import t
    from tui_manager.ui.screens import MainMenuScreen

    assert main(['--quickstart', '--lang', 'es']) == 0
    out = capsys.readouterr().out
    assert len(MainMenuScreen.ENTRIES) == 10
    for index, (entry_id, _screen) in enumerate(MainMenuScreen.ENTRIES):
        key = MainMenuScreen.shortcut(index)
        assert f'[{key}]' in out
        assert t(f'menu.{entry_id}') in out
        assert t(f'menu.{entry_id}.desc') in out


def test_cli_quickstart_suggests_doctor(capsys):
    """El recorrido termina sugiriendo `tm --doctor`."""
    assert main(['--quickstart', '--lang', 'es']) == 0
    out = capsys.readouterr().out
    assert 'tm --doctor' in out
    assert out.rstrip().splitlines()[-1].find('tm --doctor') >= 0


def test_cli_quickstart_respects_lang(capsys):
    """--lang en traduce el recorrido sin tocar --version/--doctor."""
    assert main(['--quickstart', '--lang', 'en']) == 0
    out = capsys.readouterr().out
    assert 'Quick tour' in out
    assert 'When you are done' in out
    assert 'tm --doctor' in out


def test_cli_quickstart_runs_no_subprocess(capsys, monkeypatch):
    """Es texto plano: no lanza comandos ni inicia la TUI."""
    def forbidden(*args, **kwargs):
        raise AssertionError('--quickstart no debe ejecutar subprocesos')

    monkeypatch.setattr(main_module.subprocess, 'run', forbidden)
    assert main(['--quickstart', '--lang', 'es']) == 0
    out = capsys.readouterr().out
    assert '\x1b[' not in out  # sin códigos de control ANSI
    assert 'tm --doctor' in out


def test_run_quickstart_matches_screen_helper(monkeypatch):
    """La API de main expone el mismo texto que el helper de screens."""
    from tui_manager import i18n
    from tui_manager.main import run_quickstart
    from tui_manager.ui.screens import quickstart_text

    monkeypatch.setattr(i18n, '_current', 'es')
    assert run_quickstart() == quickstart_text()


def test_quickstart_i18n_keys_in_both_languages():
    """Las claves nuevas existen en es y en, dentro de cada dict."""
    from tui_manager.i18n import STRINGS

    for lang, strings in STRINGS.items():
        for key in ('quickstart.title', 'quickstart.intro',
                    'quickstart.doctor_hint'):
            assert key in strings, f'{key} falta en {lang}'
        assert 'tm --doctor' in strings['quickstart.doctor_hint']

