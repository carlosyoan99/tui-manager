"""
Control del sistema: acciones con capacidades por presencia de binarios.

Cada acción devuelve (ok, mensaje). Ninguna acción asume systemctl: si el
binario no existe, la acción reporta no-soportado (degradación elegante).
"""

import os
import platform
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
        system = platform.system()
        if system == 'Darwin' and self._which('pmset'):
            return _run(['pmset', 'displaysleepnow'])[0] == 0, ''
        if system == 'Windows' and self._which('rundll32'):
            return _run(['rundll32', 'user32.dll,LockWorkStation'])[0] == 0, ''
        return False, 'lock_screen no soportado'

    def logout(self):
        system = platform.system()
        if system == 'Darwin' and self._which('osascript'):
            script = 'tell application "System Events" to log out'
            return _run(['osascript', '-e', script])[0] == 0, ''
        if system == 'Windows' and self._which('shutdown'):
            return _run(['shutdown', '/l'])[0] == 0, ''
        if self._which('loginctl'):
            code, _, _ = _run(['loginctl', 'terminate-session',
                               os.environ.get('XDG_SESSION_ID', 'self')])
            return code == 0, ''
        return False, 'loginctl no disponible'

    def reboot(self):
        system = platform.system()
        if system == 'Darwin' and self._which('shutdown'):
            return _run(['shutdown', '-r', 'now'])[0] == 0, ''
        if system == 'Windows' and self._which('shutdown'):
            return _run(['shutdown', '/r', '/t', '0'])[0] == 0, ''
        if self._which('systemctl'):
            return _run(['systemctl', 'reboot'])[0] == 0, ''
        if self._which('shutdown'):  # BSD y otros sin systemd
            return _run(['shutdown', '-r', 'now'])[0] == 0, ''
        return False, 'systemctl/shutdown no disponible'

    def shutdown(self):
        system = platform.system()
        if system == 'Darwin' and self._which('shutdown'):
            return _run(['shutdown', '-h', 'now'])[0] == 0, ''
        if system == 'Windows' and self._which('shutdown'):
            return _run(['shutdown', '/s', '/t', '0'])[0] == 0, ''
        if self._which('systemctl'):
            return _run(['systemctl', 'poweroff'])[0] == 0, ''
        if self._which('shutdown'):  # BSD: shutdown -p apaga
            return _run(['shutdown', '-p', 'now'])[0] == 0, ''
        return False, 'systemctl/shutdown no disponible'

    def suspend(self):
        system = platform.system()
        if system == 'Darwin' and self._which('pmset'):
            return _run(['pmset', 'sleepnow'])[0] == 0, ''
        if system == 'Windows' and self._which('rundll32'):
            cmd = ['rundll32', 'powrprof.dll,SetSuspendState', '0,1,0']
            return _run(cmd)[0] == 0, ''
        if self._which('systemctl'):
            return _run(['systemctl', 'suspend'])[0] == 0, ''
        if self._which('zzz'):  # FreeBSD suspend-to-RAM
            return _run(['zzz'])[0] == 0, ''
        return False, 'systemctl/zzz no disponible'

    # --- Brillo ---
    def brightness_step(self, direction: int):
        system = platform.system()
        if system == 'Darwin' and self._which('brightness'):
            delta = '0.1' if direction > 0 else '-0.1'
            return _run(['brightness', delta])[0] == 0, ''
        if system == 'Windows' and self._which('powershell'):
            amount = '10' if direction > 0 else '-10'
            ps = (
                '$b=(Get-WmiObject -Namespace root/wmi -Class '
                'WmiMonitorBrightness).CurrentBrightness;'
                '(Get-WmiObject -Namespace root/wmi -Class '
                'WmiMonitorBrightnessMethods).WmiSetBrightness('
                f'1,[Math]::Min(100,[Math]::Max(0,$b+{amount})))'
            )
            return _run(['powershell', '-NoProfile', '-Command', ps])[0] == 0, ''
        tool = self._which('brightnessctl')
        if tool:
            sign = '+' if direction > 0 else f'-'
            code, _, _ = _run([tool, 'set', f'{sign}5%'])
            return code == 0, ''
        return False, 'brightnessctl no disponible'

    # --- Perfiles de energía ---
    def power_profiles(self):
        system = platform.system()
        if system == 'Darwin' and self._which('pmset'):
            code, out, _ = _run(['pmset', '-g'])
            if code == 0:
                return True, out.strip()
            return False, 'pmset -g falló'
        if system == 'Windows' and self._which('powercfg'):
            code, out, _ = _run(['powercfg', '/list'])
            if code == 0:
                return True, out.strip()
            return False, 'powercfg /list falló'
        if self._which('powerprofilesctl'):
            code, out, _ = _run(['powerprofilesctl', 'list'])
            if code == 0:
                return True, out.strip()
        return False, 'powerprofilesctl no disponible'

    def set_power_profile(self, profile: str):
        system = platform.system()
        if system == 'Windows' and self._which('powercfg'):
            code, _, _ = _run(['powercfg', '/setactive', profile])
            return code == 0, ''
        if self._which('powerprofilesctl'):
            code, _, _ = _run(['powerprofilesctl', 'set', profile])
            return code == 0, ''
        return False, 'powerprofilesctl no disponible'

    # --- Zona horaria ---
    def set_timezone(self, tz: str):
        system = platform.system()
        if system == 'Darwin' and self._which('systemsetup'):
            code, _, err = _run(['systemsetup', '-settimezone', tz])
            return code == 0, err
        if system == 'Windows' and self._which('tzutil'):
            code, _, err = _run(['tzutil', '/s', tz])
            return code == 0, err
        if self._which('timedatectl'):
            code, _, err = _run(['timedatectl', 'set-timezone', tz])
            return code == 0, err
        return False, 'timedatectl no disponible'

    def list_timezones(self):
        system = platform.system()
        if system == 'Darwin' and self._which('systemsetup'):
            code, out, _ = _run(['systemsetup', '-listtimezones'])
            if code == 0:
                return True, out.splitlines()
            return False, 'systemsetup -listtimezones falló'
        if system == 'Windows' and self._which('tzutil'):
            code, out, _ = _run(['tzutil', '/l'])
            if code == 0:
                return True, [z.strip() for z in out.splitlines() if z.strip()]
            return False, 'tzutil /l falló'
        if self._which('timedatectl'):
            code, out, _ = _run(['timedatectl', 'list-timezones'], timeout=30)
            if code == 0:
                return True, out.split('\n')
        return False, 'timedatectl no disponible'

    # --- Modo oscuro (GNOME / macOS / Windows) ---
    def set_dark_mode(self, dark: bool):
        system = platform.system()
        if system == 'Darwin' and self._which('defaults'):
            cmd = (['defaults', 'write', '-g', 'AppleInterfaceStyle',
                    '-string', 'Dark'] if dark
                   else ['defaults', 'delete', '-g', 'AppleInterfaceStyle'])
            return _run(cmd)[0] == 0, ''
        if system == 'Windows' and self._which('reg'):
            value = '0' if dark else '1'
            key = (r'HKCU\Software\Microsoft\Windows\CurrentVersion'
                   r'\Themes\Personalize')
            code, _, err = _run(['reg', 'add', key, '/v', 'AppsUseLightTheme',
                                 '/t', 'REG_DWORD', '/d', value, '/f'])
            return code == 0, err
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

        system = platform.system()
        if system == 'Darwin':
            return {
                'lock': None if (env_cap(Capability.LOCK_SCREEN)
                                 or self._which('pmset'))
                        else 'pmset/lock_screen (entorno)',
                'logout': None if self._which('osascript') else 'osascript',
                'reboot': None if self._which('shutdown') else 'shutdown',
                'shutdown': None if self._which('shutdown') else 'shutdown',
                'suspend': None if self._which('pmset') else 'pmset',
                'brightness': None if self._which('brightness') else 'brightness',
                'power_profiles': None if self._which('pmset') else 'pmset',
                'timezone': None if self._which('systemsetup') else 'systemsetup',
                'launch': None if env_cap(Capability.LAUNCH_APP)
                          else 'launch_app (entorno)',
            }
        if system == 'Windows':
            return {
                'lock': None if (env_cap(Capability.LOCK_SCREEN)
                                 or self._which('rundll32'))
                        else 'rundll32/lock_screen (entorno)',
                'logout': None if self._which('shutdown') else 'shutdown',
                'reboot': None if self._which('shutdown') else 'shutdown',
                'shutdown': None if self._which('shutdown') else 'shutdown',
                'suspend': None if self._which('rundll32') else 'rundll32',
                'brightness': None if self._which('powershell') else 'powershell',
                'power_profiles': None if self._which('powercfg') else 'powercfg',
                'timezone': None if self._which('tzutil') else 'tzutil',
                'launch': None if env_cap(Capability.LAUNCH_APP)
                          else 'launch_app (entorno)',
            }

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
