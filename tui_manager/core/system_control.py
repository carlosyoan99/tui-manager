"""
Control del sistema: acciones con capacidades por presencia de binarios.

Cada acción devuelve (ok, mensaje). Ninguna acción asume systemctl: si el
binario no existe, la acción reporta no-soportado (degradación elegante).
"""

import os
import shutil
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _run(cmd, timeout=15):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


class SystemControl:
    """Acciones del sistema portátiles (systemd-first, fallbacks honestos)."""

    def __init__(self, environment=None):
        self.environment = environment  # EnvironmentAdapter opcional

    def _which(self, *tools):
        for tool in tools:
            if shutil.which(tool):
                return tool
        return None

    # --- Energía / sesión ---
    def lock(self):
        env = self.environment
        if env:
            from .environment import Capability
            if env.supports(Capability.LOCK_SCREEN):
                try:
                    return env.lock_screen(), ''
                except NotImplementedError:
                    pass
        return False, 'lock_screen no soportado'

    def logout(self):
        if self._which('loginctl'):
            code, _, _ = _run(['loginctl', 'terminate-session',
                               os.environ.get('XDG_SESSION_ID', 'self')])
            return code == 0, ''
        return False, 'loginctl no disponible'

    def reboot(self):
        if self._which('systemctl'):
            return _run(['systemctl', 'reboot'])[0] == 0, ''
        if self._which('shutdown'):  # BSD y otros sin systemd
            return _run(['shutdown', '-r', 'now'])[0] == 0, ''
        return False, 'systemctl/shutdown no disponible'

    def shutdown(self):
        if self._which('systemctl'):
            return _run(['systemctl', 'poweroff'])[0] == 0, ''
        if self._which('shutdown'):  # BSD: shutdown -p apaga
            return _run(['shutdown', '-p', 'now'])[0] == 0, ''
        return False, 'systemctl/shutdown no disponible'

    def suspend(self):
        if self._which('systemctl'):
            return _run(['systemctl', 'suspend'])[0] == 0, ''
        if self._which('zzz'):  # FreeBSD suspend-to-RAM
            return _run(['zzz'])[0] == 0, ''
        return False, 'systemctl/zzz no disponible'

    # --- Brillo ---
    def brightness_step(self, direction: int):
        tool = self._which('brightnessctl')
        if tool:
            sign = '+' if direction > 0 else f'-'
            code, _, _ = _run([tool, 'set', f'{sign}5%'])
            return code == 0, ''
        return False, 'brightnessctl no disponible'

    # --- Perfiles de energía ---
    def power_profiles(self):
        if self._which('powerprofilesctl'):
            code, out, _ = _run(['powerprofilesctl', 'list'])
            if code == 0:
                return True, out.strip()
        return False, 'powerprofilesctl no disponible'

    def set_power_profile(self, profile: str):
        if self._which('powerprofilesctl'):
            code, _, _ = _run(['powerprofilesctl', 'set', profile])
            return code == 0, ''
        return False, 'powerprofilesctl no disponible'

    # --- Zona horaria ---
    def set_timezone(self, tz: str):
        if self._which('timedatectl'):
            code, _, err = _run(['timedatectl', 'set-timezone', tz])
            return code == 0, err
        return False, 'timedatectl no disponible'

    def list_timezones(self):
        if self._which('timedatectl'):
            code, out, _ = _run(['timedatectl', 'list-timezones'], timeout=30)
            if code == 0:
                return True, out.split('\n')
        return False, 'timedatectl no disponible'

    # --- Modo oscuro (GNOME y compatibles vía gsettings) ---
    def set_dark_mode(self, dark: bool):
        if self._which('gsettings'):
            scheme = 'prefer-dark' if dark else 'prefer-light'
            code, _, _ = _run(['gsettings', 'set',
                               'org.gnome.desktop.interface', 'color-scheme', scheme])
            return code == 0, ''
        return False, 'gsettings no disponible'

    # --- Batería (Termux o sysfs) ---
    def battery_status(self) -> Optional[dict]:
        if self._which('termux-battery-status'):
            code, out, _ = _run(['termux-battery-status'], timeout=10)
            if code == 0:
                try:
                    import json
                    data = json.loads(out)
                    return {'percent': data.get('percentage'),
                            'plugged': data.get('plugged'),
                            'status': data.get('status')}
                except Exception:
                    pass
        # sysfs Linux
        base = '/sys/class/power_supply'
        try:
            for bat in os.listdir(base):
                if bat.startswith('BAT') or bat.startswith('battery'):
                    with open(f'{base}/{bat}/capacity') as f:
                        percent = f.read().strip()
                    with open(f'{base}/{bat}/status') as f:
                        status = f.read().strip()
                    return {'percent': percent, 'plugged': None, 'status': status}
        except Exception:
            pass
        return None

    # --- Disponibilidad (para degradación elegante en el menú) ---
    def availability(self) -> dict:
        """id de acción → None si disponible, motivo si no lo está.

        El motivo es el nombre de la herramienta/capacidad que falta.
        """
        from .environment import Capability

        def env_cap(cap):
            try:
                return bool(self.environment and self.environment.supports(cap))
            except Exception:
                return False

        return {
            'lock': None if env_cap(Capability.LOCK_SCREEN)
                    else 'lock_screen (entorno)',
            'logout': None if self._which('loginctl')
                      else 'loginctl',
            'reboot': None if self._which('systemctl', 'shutdown')
                      else 'systemctl/shutdown',
            'shutdown': None if self._which('systemctl', 'shutdown')
                        else 'systemctl/shutdown',
            'suspend': None if self._which('systemctl', 'zzz')
                       else 'systemctl/zzz',
            'brightness': None if self._which('brightnessctl')
                          else 'brightnessctl',
            'power_profiles': None if self._which('powerprofilesctl')
                              else 'powerprofilesctl',
            'timezone': None if self._which('timedatectl')
                        else 'timedatectl',
            'launch': None if env_cap(Capability.LAUNCH_APP)
                      else 'launch_app (entorno)',
        }
