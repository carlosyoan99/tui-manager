"""
Conftest del simulador multi-SO.

FakeRunner reemplaza subprocess.run con salidas REALES (canned) de cada
gestor de paquetes. Cualquier comando inesperado hace fallar el test, así
los adapters no pueden "callar" errores llamando cosas distintas.
"""

import pytest


class Completed:
    """Imita subprocess.CompletedProcess con atributos usados por el core."""

    def __init__(self, rc=0, stdout="", stderr=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    """subprocess.run(cmd, capture_output=True, text=True, ...) → canned."""

    def __init__(self, canned=None, default_rc=0):
        self.canned = canned or {}   # tuple(cmd) → (rc, stdout, stderr)
        self.calls = []

    def __call__(self, cmd, capture_output=True, text=True, timeout=None, **kwargs):
        key = tuple(cmd)
        self.calls.append(key)
        if key not in self.canned:
            raise AssertionError(f"Comando no simulado: {list(cmd)}")
        rc, stdout, stderr = self.canned[key]
        return Completed(rc, stdout, stderr)

    def expect(self, cmd, rc=0, stdout="", stderr=""):
        self.canned[tuple(cmd)] = (rc, stdout, stderr)
        return self


@pytest.fixture
def fake_runner(monkeypatch):
    """Activa el simulador de subprocess para el test actual."""
    runner = FakeRunner()
    import subprocess
    monkeypatch.setattr(subprocess, 'run', runner)
    return runner
