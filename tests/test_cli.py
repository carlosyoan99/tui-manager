"""
Tests de la CLI (main.py): --version y --doctor.

El doctor usa las detecciones reales del entorno de test (Termux u otro);
se verifica estructura del informe, no valores concretos del SO anfitrión.
"""

import pytest

from tui_manager import __version__
from tui_manager.main import main, run_doctor


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
