"""
Tests de notificaciones nativas y reduced-motion (B3-3).

No se ejecuta ``notify-send`` real: un fixture autouse reemplaza
``shutil.which`` (devuelve None) y ``subprocess.run`` (falla si se llama).
Cada test configura explícitamente esos mocks o usa los parámetros
inyectables ``which`` / ``runner`` del módulo.
"""

import os
import shutil
import subprocess

import pytest

from tui_manager.ui.notifications import (
    AnimationDescriptor,
    notify,
    progress_animation,
    reduced_motion_enabled,
)


class Recorder:
    """Stub minimalista que registra llamadas y devuelve un resultado configurable."""

    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result
        self.error = error

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture(autouse=True)
def _sin_notificaciones_reales(monkeypatch):
    """Red de seguridad: ningún test puede ejecutar notify-send de verdad."""
    spy = Recorder(error=AssertionError('subprocess.run real: no permitido'))

    def find_nothing(name):
        return None

    monkeypatch.setattr(shutil, 'which', find_nothing, raising=True)
    monkeypatch.setattr(subprocess, 'run', spy, raising=True)
    return spy


# ---------------- notify: herramienta ausente ----------------

def test_notify_sin_herramienta_no_llama_subprocess(_sin_notificaciones_reales):
    resultado = notify('Título', 'Mensaje')

    assert resultado == 'unavailable'
    assert _sin_notificaciones_reales.calls == []  # 0 subprocess


def test_notify_which_inyectado_ausente_no_llama_runner():
    runner = Recorder()

    resultado = notify('T', 'M', which=lambda name: None, runner=runner)

    assert resultado == 'unavailable'
    assert runner.calls == []


# ---------------- notify: herramienta disponible ----------------

def test_notify_herramienta_disponible_llama_subprocess(monkeypatch):
    runner = Recorder(result=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(subprocess, 'run', runner, raising=True)
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/notify-send', raising=True)

    resultado = notify('Instalación lista', 'curl instalado')

    assert resultado == 'native'
    assert len(runner.calls) == 1
    args, kwargs = runner.calls[0]
    assert args == (['notify-send', 'Instalación lista', 'curl instalado'],)
    assert kwargs['timeout'] == 2
    assert kwargs['check'] is False


def test_notify_inyeccion_runner_y_which_no_toca_globales(_sin_notificaciones_reales):
    runner = Recorder()
    finder = Recorder(result='/usr/bin/notify-send')

    def fake_which(name):
        finder(name)
        return '/usr/bin/notify-send'

    resultado = notify('T', 'M', runner=runner, which=fake_which)

    assert resultado == 'native'
    assert finder.calls[0][0] == ('notify-send',)
    assert runner.calls[0][0] == (['notify-send', 'T', 'M'],)
    assert _sin_notificaciones_reales.calls == []  # no se usó el global


def test_notify_check_false_no_inspecciona_returncode(monkeypatch):
    """Un runner que devuelve un objeto cualquiera cuenta como 'native'."""
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/notify-send', raising=True)
    monkeypatch.setattr(subprocess, 'run', Recorder(result=None), raising=True)

    assert notify('T', 'M') == 'native'


# ---------------- notify: fallos, nunca excepciones ----------------

def test_notify_timeout_devuelve_unavailable(monkeypatch):
    error = subprocess.TimeoutExpired(['notify-send'], 2)
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/notify-send', raising=True)
    monkeypatch.setattr(subprocess, 'run', Recorder(error=error), raising=True)

    assert notify('T', 'M') == 'unavailable'


def test_notify_fallo_which_no_lanza():
    def roto(name):
        raise OSError('falló la búsqueda')

    assert notify('T', 'M', which=roto, runner=Recorder()) == 'unavailable'


def test_notify_fallo_runner_no_lanza():
    runner = Recorder(error=RuntimeError('falló el notify'))

    assert notify('T', 'M', which=lambda name: '/usr/bin/notify-send', runner=runner) == 'unavailable'


def test_notify_acepta_app_reservado():
    class FakeApp:
        pass

    assert notify('T', 'M', app=FakeApp()) == 'unavailable'


# ---------------- reduced motion ----------------

@pytest.mark.parametrize(
    'environ',
    [
        {'PREFERS_REDUCED_MOTION': '1'},
        {'PREFERS_REDUCED_MOTION': 'true'},
        {'PREFERS_REDUCED_MOTION': 'yes'},
        {'NO_COLOR': '1'},
        {'NO_COLOR': ''},
        {'TERM': 'dumb'},
        {'TERM': 'DUMB'},
    ],
)
def test_reduced_motion_enabled_segun_entorno(environ):
    assert reduced_motion_enabled(environ) is True


@pytest.mark.parametrize(
    'environ',
    [
        {},
        {'TERM': 'xterm-256color'},
        {'PREFERS_REDUCED_MOTION': '0'},
        {'PREFERS_REDUCED_MOTION': 'false'},
    ],
)
def test_reduced_motion_desactivado(environ):
    assert reduced_motion_enabled(environ) is False


def test_reduced_motion_lee_os_environ(monkeypatch):
    monkeypatch.delenv('NO_COLOR', raising=False)
    monkeypatch.delenv('PREFERS_REDUCED_MOTION', raising=False)
    monkeypatch.setenv('TERM', 'dumb')

    assert reduced_motion_enabled() is True

    monkeypatch.setenv('TERM', 'xterm')
    assert reduced_motion_enabled() is False


# ---------------- progress_animation ----------------

def test_progress_animation_normal_devuelve_frames_e_intervalo():
    anim = progress_animation('Instalando', environ={})

    assert isinstance(anim, AnimationDescriptor)
    assert anim.label == 'Instalando'
    assert anim.style == 'spinner'
    assert len(anim.frames) > 1
    assert anim.interval > 0
    assert anim.animated is True
    assert anim.reduced_motion is False


@pytest.mark.parametrize(
    'environ',
    [
        {'NO_COLOR': '1'},
        {'TERM': 'dumb'},
        {'PREFERS_REDUCED_MOTION': '1'},
    ],
)
def test_progress_animation_reducido_es_estatico(environ):
    anim = progress_animation('Instalando', environ=environ)

    assert anim.reduced_motion is True
    assert anim.animated is False
    assert anim.frames == (anim.frames[0],)  # un solo frame
    assert anim.interval == 0.0


def test_progress_animation_no_modifica_os_environ(monkeypatch):
    monkeypatch.delenv('NO_COLOR', raising=False)
    monkeypatch.delenv('PREFERS_REDUCED_MOTION', raising=False)
    monkeypatch.setenv('TERM', 'xterm')

    anim = progress_animation('T', environ={'NO_COLOR': '1'})

    assert anim.reduced_motion is True
    assert 'NO_COLOR' not in os.environ


@pytest.mark.parametrize('style', ['spinner', 'dots', 'bar'])
def test_progress_animation_estilos(style):
    anim = progress_animation('T', style=style, environ={})

    assert anim.style == style
    assert len(anim.frames) > 1


def test_progress_animation_estilo_desconocido_degrada_a_spinner():
    anim = progress_animation('T', style='inexistente', environ={})

    assert anim.style == 'spinner'
    assert anim.frames == progress_animation('T', environ={}).frames
