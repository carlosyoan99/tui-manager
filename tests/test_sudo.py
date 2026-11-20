"""
Tests simulados del flujo de elevación (2.0-A3).

NINGÚN test ejecuta sudo/doas real: se interceptan `os.geteuid`,
`shutil.which` y `subprocess.run` del módulo `package_adapter`.
"""

import subprocess

import pytest

from tui_manager.core import package_adapter as pa
from tui_manager.core.package_adapter import (
    PackageAdapter,
    SUDO_PASSWORD_REQUIRED,
)


def make_runner(monkeypatch, responses):
    """Instala un `subprocess.run` falso.

    `responses` puede ser un dict ``tuple(cmd) -> (rc, stdout, stderr)`` o un
    callable ``(cmd, numero_de_llamada) -> (rc, stdout, stderr)``.
    Devuelve la lista de comandos ejecutados.
    """
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if callable(responses):
            rc, out, err = responses(list(cmd), len(calls))
        else:
            rc, out, err = responses.get(tuple(cmd), (0, '', ''))
        return subprocess.CompletedProcess(cmd, rc, out, err)

    monkeypatch.setattr(pa.subprocess, 'run', fake_run)
    return calls


@pytest.fixture(autouse=True)
def non_root_with_sudo(monkeypatch):
    """Escenario base: usuario normal con sudo y doas disponibles."""
    monkeypatch.setattr(pa.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(
        pa.shutil, 'which',
        lambda tool, *a, **k: f'/usr/bin/{tool}'
        if tool in ('sudo', 'doas') else None,
    )


# ------------------------------------------------------------------ root ----

def test_root_runs_without_sudo(monkeypatch):
    """Si somos root no se anteponer sudo ni se hace sondeo alguno."""
    monkeypatch.setattr(pa.os, 'geteuid', lambda: 0)
    calls = make_runner(monkeypatch, {})

    assert PackageAdapter().execute_command(['apt', 'update']) == (0, '', '')
    assert calls == [['apt', 'update']]


# -------------------------------------------------------------- cacheado ----

def test_cached_credentials_use_sudo_n(monkeypatch):
    """Con credenciales cacheadas: sondeo `sudo -n true` y ejecución `-n`."""
    calls = make_runner(monkeypatch, {
        ('sudo', '-n', 'true'): (0, '', ''),
        ('sudo', '-n', 'apt', 'install', '-y', 'curl'): (0, 'ok', ''),
    })

    result = PackageAdapter().execute_command(
        ['apt', 'install', '-y', 'curl'])

    assert result == (0, 'ok', '')
    assert calls == [
        ['sudo', '-n', 'true'],
        ['sudo', '-n', 'apt', 'install', '-y', 'curl'],
    ]


# --------------------------------------------------------------- elevator ----

def test_elevator_called_when_no_cache(monkeypatch):
    """Sin caché se llama al hook; tras él se reintenta y se ejecuta."""
    state = {'cached': False}

    def responses(cmd, call_number):
        if cmd == ['sudo', '-n', 'true']:
            return (0, '', '') if state['cached'] else (1, '', 'requiere pass')
        if cmd == ['sudo', '-n', 'apt', 'update']:
            return (0, 'actualizado', '')
        return (0, '', '')

    calls = make_runner(monkeypatch, responses)
    hook_calls = []

    def elevator():
        hook_calls.append(True)
        state['cached'] = True  # simula `sudo -v` en el TTY real
        return True

    result = PackageAdapter(elevator=elevator).execute_command(['apt', 'update'])

    assert result == (0, 'actualizado', '')
    assert hook_calls == [True]
    assert calls.count(['sudo', '-n', 'true']) == 2
    assert calls[-1] == ['sudo', '-n', 'apt', 'update']


def test_elevator_exception_is_swallowed(monkeypatch):
    """Un hook que lanza excepción no propaga traceback ni credenciales."""
    calls = make_runner(monkeypatch, {
        ('sudo', '-n', 'true'): (1, '', 'requiere pass'),
    })

    def elevator():
        raise RuntimeError('la TUI no pudo suspenderse')

    result = PackageAdapter(elevator=elevator).execute_command(['apt', 'update'])

    assert result == (-1, '', SUDO_PASSWORD_REQUIRED)
    assert calls == [['sudo', '-n', 'true'], ['sudo', '-n', 'true']]


# ----------------------------------------------------------------- fallo ----

def test_no_credentials_fails_gracefully(monkeypatch):
    """Sin caché y con elevación cancelada: mensaje accionable, sin trace."""
    calls = make_runner(monkeypatch, {
        ('sudo', '-n', 'true'): (1, '', 'a password is required'),
    })
    hook_calls = []

    def elevator():
        hook_calls.append(True)
        return False  # usuario canceló

    result = PackageAdapter(elevator=elevator).execute_command(['apt', 'update'])

    assert result == (-1, '', SUDO_PASSWORD_REQUIRED)
    assert len(hook_calls) == 1
    # Dos sondeos: antes y después del hook; nunca se ejecutó el comando.
    assert calls == [['sudo', '-n', 'true'], ['sudo', '-n', 'true']]


def test_no_privilege_tool_degrades(monkeypatch):
    """Sin sudo ni doas se degrada con el mismo mensaje accionable."""
    monkeypatch.setattr(pa.shutil, 'which', lambda tool, *a, **k: None)
    calls = make_runner(monkeypatch, {})

    result = PackageAdapter().execute_command(['apt', 'update'])

    assert result == (-1, '', SUDO_PASSWORD_REQUIRED)
    assert calls == []


# --------------------------------------------------------------- BSD/doas ----

def test_doas_on_bsd(monkeypatch):
    """En BSD sin sudo se usa `doas -n` con el mismo patrón."""
    monkeypatch.setattr(
        pa.shutil, 'which',
        lambda tool, *a, **k: '/usr/bin/doas' if tool == 'doas' else None,
    )
    calls = make_runner(monkeypatch, {
        ('doas', '-n', 'true'): (0, '', ''),
        ('doas', '-n', 'pkg', 'install', 'curl'): (0, 'ok', ''),
    })

    result = PackageAdapter().execute_command(['pkg', 'install', 'curl'])

    assert result == (0, 'ok', '')
    assert calls == [
        ['doas', '-n', 'true'],
        ['doas', '-n', 'pkg', 'install', 'curl'],
    ]


def test_bsd_adapter_legacy_command_preserved(fake_runner, monkeypatch):
    """Los adapters BSD sin hook conservan su prefijo histórico (`sudo`)."""
    from tui_manager.core.pkgsrc_adapter import PkgsrcAdapter

    monkeypatch.setattr(pa.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(
        pa.shutil, 'which',
        lambda tool, *a, **k: '/usr/bin/sudo' if tool == 'sudo' else None,
    )
    fake_runner.expect(['sudo', 'pkgin', '-y', 'install', 'curl'], rc=0)

    assert PkgsrcAdapter().install_package('curl', confirm=False) is True


# --------------------------------------------------------------- CLI/UI ------

def test_cli_never_uses_elevator(monkeypatch):
    """La ruta CLI deja los adapters sin hook: nunca pide contraseña."""
    from tui_manager import main as main_module

    class FakeAdapter:
        elevator = object()  # como si la UI lo hubiera inyectado

    class FakeManager:
        adapter = FakeAdapter()

    manager = FakeManager()
    main_module.configure_non_interactive(manager)

    assert manager.adapter.elevator is None


def _make_app():
    """TuiManagerApp con un PackageManager falso (sin subprocesos reales)."""
    from unittest.mock import MagicMock

    from tui_manager.core.theme_manager import ThemeManager
    from tui_manager.ui.app import Services, TuiManagerApp

    manager = MagicMock()
    services = Services(package_manager=manager,
                        theme_manager=ThemeManager('dark'))
    return TuiManagerApp(services), manager


def test_app_injects_elevator_into_adapter():
    """La UI conecta su `elevate` con el adapter del PackageManager."""
    app, manager = _make_app()
    assert manager.adapter.elevator == app.elevate


def test_app_elevate_suspends_tui_and_uses_real_tty(monkeypatch):
    """`elevate` suspende la TUI y ejecuta `sudo -v` en el TTY real."""
    from contextlib import contextmanager

    from tui_manager.ui import app as app_module

    app, _ = _make_app()
    events = []

    @contextmanager
    def fake_suspend():
        events.append('suspend-enter')
        yield
        events.append('suspend-exit')

    monkeypatch.setattr(app, 'suspend', fake_suspend)
    monkeypatch.setattr(
        app_module.subprocess, 'run',
        lambda cmd, **kwargs: (
            events.append(('run', tuple(cmd))) or
            subprocess.CompletedProcess(cmd, 0, '', '')),
    )
    monkeypatch.setattr(app, 'notify',
                        lambda title, message, **kwargs:
                        events.append(('notify', title, kwargs)))

    assert app.elevate() is True
    assert events == [
        'suspend-enter',
        ('run', ('sudo', '-v')),
        'suspend-exit',
        ('notify', 'Sesión elevada', {'severity': 'information'}),
    ]


def test_app_elevate_failure_notifies_actionable_message(monkeypatch):
    """Si se cancela `sudo -v`, vuelve la TUI y avisa sin traceback."""
    from contextlib import contextmanager

    from tui_manager.ui import app as app_module

    app, _ = _make_app()

    @contextmanager
    def fake_suspend():
        yield

    monkeypatch.setattr(app, 'suspend', fake_suspend)
    monkeypatch.setattr(
        app_module.subprocess, 'run',
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 1, '', ''),
    )
    notices = []
    monkeypatch.setattr(
        app, 'notify',
        lambda title, message, **kwargs: notices.append((title, message, kwargs)),
    )

    assert app.elevate() is False
    assert len(notices) == 1
    assert notices[0][0] == 'Elevación cancelada'
    assert 'sudo -v' in notices[0][1]
    assert notices[0][2] == {'severity': 'warning'}
