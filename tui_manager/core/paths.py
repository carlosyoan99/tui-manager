"""
Rutas de datos de TUI Manager (XDG Base Directory Specification).

Antes se usaba `~/.tui-manager/`, que ensuciaba el directorio del usuario.
Ahora:
  - configuración → $XDG_CONFIG_HOME/tui-manager/ (o ~/.config/tui-manager/)
  - logs/estado   → $XDG_STATE_HOME/tui-manager/ (o ~/.local/state/tui-manager/)
  - snapshots     → $XDG_DATA_HOME/tui-manager/ (o ~/.local/share/tui-manager/)

Compatibilidad: si existe la ruta antigua `~/.tui-manager/`, se usa como
fallback de LECTURA para no perder la configuración del usuario. Las
escrituras siempre van a la ruta XDG nueva.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = 'tui-manager'
def legacy_home() -> Path:
    """Ruta legacy calculada en cada llamada (respeta HOME mockeado en tests)."""
    return Path.home() / '.tui-manager'


def config_home() -> Path:
    """Directorio de configuración (XDG_CONFIG_HOME)."""
    base = os.environ.get('XDG_CONFIG_HOME')
    path = Path(base).expanduser() if base else Path.home() / '.config'
    return path / APP_NAME


def state_home() -> Path:
    """Directorio de estado/logs (XDG_STATE_HOME)."""
    base = os.environ.get('XDG_STATE_HOME')
    path = Path(base).expanduser() if base else Path.home() / '.local' / 'state'
    return path / APP_NAME


def data_home() -> Path:
    """Directorio de datos/snapshots (XDG_DATA_HOME)."""
    base = os.environ.get('XDG_DATA_HOME')
    path = Path(base).expanduser() if base else Path.home() / '.local' / 'share'
    return path / APP_NAME


def config_file() -> Path:
    """Ruta del archivo de configuración, con fallback de lectura legacy."""
    new = config_home() / 'config.yaml'
    old = legacy_home() / 'config.yaml'
    # Si el usuario ya tiene configuración en la ruta antigua y la nueva no
    # existe, devolver la antigua para no perder sus ajustes.
    if old.exists() and not new.exists():
        return old
    return new


def log_file() -> Path:
    """Ruta del log, con fallback de lectura legacy."""
    new = state_home() / 'logs' / 'app.log'
    old = legacy_home() / 'logs' / 'app.log'
    if old.exists() and not new.exists():
        return old
    return new


def snapshot_dir() -> Path:
    """Ruta de snapshots, con fallback de lectura legacy."""
    new = data_home() / 'snapshots'
    old = legacy_home() / 'snapshots'
    if old.exists() and not new.exists():
        return old
    return new
