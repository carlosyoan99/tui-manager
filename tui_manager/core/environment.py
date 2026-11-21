"""
Plano de entorno: detección DE/WM y EnvironmentAdapter con modelo de capacidades.

Spec: docs/TECHNICAL_SPECS.md §10.2. Reglas:
1. Degradación elegante: la UI consulta supports() antes de todo; una capacidad
   ausente deshabilita la entrada de menú, nunca lanza error en uso.
2. El plano SO y el plano entorno no se conocen entre sí.
3. Backup (.bak-tm) antes de escribir configs de terceros (ver backup_file()).
"""

import os
import platform
import shutil
import subprocess
import logging
from enum import Enum, auto
from typing import List, Optional

logger = logging.getLogger(__name__)


class Capability(Enum):
    RELOAD_CONFIG = auto()       # recargar config del WM
    SET_GAPS = auto()            # gaps (hyprctl, bspc)
    SET_WALLPAPER = auto()       # swww/swaybg/feh/hsetroot/xfconf
    SET_DARK_MODE = auto()       # gsettings color-scheme (GNOME y compatibles)
    TOGGLE_BAR = auto()          # waybar kill/launch
    LOCK_SCREEN = auto()
    LIST_WINDOWS = auto()
    LAUNCH_APP = auto()          # dispatch exec del WM o fallback universal


def backup_file(path: str) -> Optional[str]:
    """Crea path.bak-tm (una sola vez) antes de modificar; devuelve ruta backup."""
    if os.path.exists(path):
        backup = path + '.bak-tm'
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
            logger.info(f"Backup creado: {backup}")
        return backup
    return None


class EnvironmentAdapter:
    """Base de adapters por DE/WM. Declarar capacidades es obligatorio."""

    name: str = 'unknown'

    def capabilities(self) -> set:
        return set()

    def supports(self, cap: Capability) -> bool:
        return cap in self.capabilities()

    # --- Métodos por capacidad (solo llamar tras supports()) ---
    def reload_config(self) -> bool:
        raise NotImplementedError

    def set_gaps(self, enable: bool) -> bool:
        raise NotImplementedError

    def set_wallpaper(self, path: str) -> bool:
        raise NotImplementedError

    def set_dark_mode(self, dark: bool) -> bool:
        raise NotImplementedError

    def toggle_bar(self, show: bool) -> bool:
        raise NotImplementedError

    def lock_screen(self) -> bool:
        raise NotImplementedError

    def list_windows(self) -> List[dict]:
        raise NotImplementedError

    def launch_app(self, command: str) -> bool:
        raise NotImplementedError

    def focus_window(self, title: str, cls: str = None) -> bool:
        """Foco sobre una ventana por título/clase; False si no aplica."""
        return False


def launch_or_focus(env: EnvironmentAdapter, command: str) -> dict:
    """A · Launch-or-focus [OM].

    Si ya hay una ventana cuya clase/título contiene el primer token del
    comando, se le da foco (capability LIST_WINDOWS + focus_window); si no,
    se lanza (LAUNCH_APP o fallback universal del adapter).

    Devuelve {'action': 'focused'|'launched'|'failed', ...}.
    """
    first = command.split()[0] if command.strip() else ''
    if first and env.supports(Capability.LIST_WINDOWS):
        try:
            windows = env.list_windows() or []
        except NotImplementedError:
            windows = []
        for win in windows:
            hay = f"{win.get('class') or ''} {win.get('title') or ''}".lower()
            if first.lower() in hay:
                title = win.get('title') or first
                if env.focus_window(title, cls=win.get('class')):
                    return {'action': 'focused', 'window': win}
    if env.launch_app(command):
        return {'action': 'launched'}
    return {'action': 'failed'}


def _run(cmd: List[str], timeout: int = 10) -> tuple:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def _has(*tools: str) -> Optional[str]:
    """Devuelve el primer binario presente de la lista."""
    for tool in tools:
        if shutil.which(tool):
            return tool
    return None


class HyprlandAdapter(EnvironmentAdapter):
    name = 'hyprland'

    def capabilities(self) -> set:
        caps = {Capability.RELOAD_CONFIG, Capability.LAUNCH_APP,
                Capability.LIST_WINDOWS, Capability.SET_GAPS}
        if _has('swww', 'swaybg', 'hyprpaper'):
            caps.add(Capability.SET_WALLPAPER)
        if _has('waybar'):
            caps.add(Capability.TOGGLE_BAR)
        if _has('hyprlock'):
            caps.add(Capability.LOCK_SCREEN)
        return caps

    def reload_config(self) -> bool:
        code, _, err = _run(['hyprctl', 'reload'])
        if code != 0:
            logger.error(f"hyprctl reload: {err}")
        return code == 0

    def set_gaps(self, enable: bool) -> bool:
        mode = '1' if enable else '0'
        code, _, err = _run(['hyprctl', 'hyprpaper', 'unload', '.*'])
        # gapsIn/gapsOut a 1/0 según toggle
        code2, _, err2 = _run(['hyprctl', 'keyword', 'general:gaps_in', mode])
        code3, _, err3 = _run(['hyprctl', 'keyword', 'general:gaps_out', mode])
        return code2 == 0 and code3 == 0

    def set_wallpaper(self, path: str) -> bool:
        tool = _has('swww', 'swaybg', 'hyprpaper')
        if tool == 'swww':
            code, _, err = _run(['swww-daemon', '--init', 'none'])
            code, _, err = _run(['swww', 'img', path])
        elif tool == 'swaybg':
            code, _, err = _run(['swaybg', '-i', path, '-m', 'fill'])
        else:  # hyprpaper
            code, _, err = _run(['hyprctl', 'hyprpaper', 'preload', path])
            if code == 0:
                code, _, err = _run(['hyprctl', 'hyprpaper', 'wallpaper', f',/,{path}'.replace('/,', ',')])
        if code != 0:
            logger.error(f"wallpaper ({tool}): {err}")
        return code == 0

    def toggle_bar(self, show: bool) -> bool:
        if show:
            code, _, err = _run(['waybar', '&'])
            return code == 0
        code, _, err = _run(['pkill', 'waybar'])
        return code == 0

    def lock_screen(self) -> bool:
        code, _, err = _run(['hyprlock'])
        return code == 0

    def list_windows(self) -> List[dict]:
        code, out, err = _run(['hyprctl', '-j', 'clients'])
        if code != 0:
            return []
        try:
            import json
            clients = json.loads(out)
            return [{'pid': c.get('pid'), 'class': c.get('class'),
                     'title': c.get('title')} for c in clients]
        except Exception as e:
            logger.error(f"parse clients: {e}")
            return []

    def launch_app(self, command: str) -> bool:
        code, _, err = _run(['hyprctl', 'dispatch', 'exec', command])
        return code == 0

    def focus_window(self, title: str, cls: str = None) -> bool:
        target = f'class:{cls}' if cls else f'title:{title}'
        return _run(['hyprctl', 'dispatch', 'focuswindow', target])[0] == 0


class SwayAdapter(EnvironmentAdapter):
    name = 'sway'

    def capabilities(self) -> set:
        caps = {Capability.RELOAD_CONFIG, Capability.LAUNCH_APP,
                Capability.LIST_WINDOWS}
        if _has('swaybg', 'swww'):
            caps.add(Capability.SET_WALLPAPER)
        if _has('waybar'):
            caps.add(Capability.TOGGLE_BAR)
        if _has('swaylock', 'swaylock-effects'):
            caps.add(Capability.LOCK_SCREEN)
        return caps

    def reload_config(self) -> bool:
        code, _, err = _run(['swaymsg', 'reload'])
        return code == 0

    def set_wallpaper(self, path: str) -> bool:
        tool = _has('swaybg', 'swww')
        if tool == 'swaybg':
            code, _, err = _run(['swaybg', '-i', path, '-m', 'fill'])
        else:
            code, _, err = _run(['swww', 'img', path])
        return code == 0

    def toggle_bar(self, show: bool) -> bool:
        return _run(['pkill', 'waybar' if not show else 'waybar'])[0] == 0

    def lock_screen(self) -> bool:
        return _run(['swaylock', '-f'])[0] == 0

    def list_windows(self) -> List[dict]:
        code, out, err = _run(['swaymsg', '-t', 'get_tree', '-r'])
        if code != 0:
            return []
        windows = []

        def walk(node):
            if isinstance(node, dict):
                if node.get('type') == 'con' and node.get('name') and not node.get('app_id') == '__focused__':
                    windows.append({'pid': node.get('pid'),
                                    'class': node.get('app_id') or node.get('window_properties', {}).get('class', ''),
                                    'title': node.get('name')})
                for child in node.get('nodes', []) + node.get('floating_nodes', []):
                    walk(child)

        try:
            import json
            walk(json.loads(out))
        except Exception as e:
            logger.error(f"parse tree: {e}")
        return windows

    def launch_app(self, command: str) -> bool:
        code, _, err = _run(['swaymsg', 'exec', '--', command])
        return code == 0

    def focus_window(self, title: str, cls: str = None) -> bool:
        selector = (f'class="{cls}"' if cls else f'title="{title}"')
        return _run(['swaymsg', f'[{selector}]', 'focus'])[0] == 0


class I3Adapter(EnvironmentAdapter):
    name = 'i3'

    def capabilities(self) -> set:
        caps = {Capability.RELOAD_CONFIG, Capability.LAUNCH_APP, Capability.LIST_WINDOWS}
        if _has('feh'):
            caps.add(Capability.SET_WALLPAPER)
        return caps

    def reload_config(self) -> bool:
        return _run(['i3-msg', 'reload'])[0] == 0

    def set_wallpaper(self, path: str) -> bool:
        return _run(['feh', '--bg-fill', path])[0] == 0

    def list_windows(self) -> List[dict]:
        code, out, err = _run(['i3-msg', '-t', 'get_tree'])
        if code != 0:
            return []
        windows = []

        def walk(node):
            if isinstance(node, dict):
                if node.get('type') == 'con' and node.get('name'):
                    windows.append({'pid': node.get('pid'),
                                    'class': node.get('window_properties', {}).get('class', ''),
                                    'title': node.get('name')})
                for child in node.get('nodes', []) + node.get('floating_nodes', []):
                    walk(child)

        try:
            import json
            walk(json.loads(out))
        except Exception as e:
            logger.error(f"parse tree: {e}")
        return windows

    def launch_app(self, command: str) -> bool:
        return _run(['i3-msg', 'exec', command])[0] == 0

    def focus_window(self, title: str, cls: str = None) -> bool:
        selector = (f'class="{cls}"' if cls else f'title="{title}"')
        return _run(['i3-msg', f'[{selector}]', 'focus'])[0] == 0


class BspwmAdapter(EnvironmentAdapter):
    name = 'bspwm'

    def capabilities(self) -> set:
        caps = {Capability.RELOAD_CONFIG, Capability.LAUNCH_APP, Capability.SET_GAPS}
        if _has('feh'):
            caps.add(Capability.SET_WALLPAPER)
        return caps

    def reload_config(self) -> bool:
        return _run(['bspc', 'wm', '-r'])[0] == 0

    def set_gaps(self, enable: bool) -> bool:
        gap = '14' if enable else '0'
        return _run(['bspc', 'config', 'window_gap', gap])[0] == 0

    def set_wallpaper(self, path: str) -> bool:
        return _run(['feh', '--bg-fill', path])[0] == 0

    def list_windows(self) -> List[dict]:
        code, out, err = _run(['bspc', 'query', '-N', '-T'])
        if code != 0:
            return []
        try:
            import json
            nodes = json.loads(out)
            return [{'pid': n.get('client', {}).get('pid'),
                     'class': n.get('client', {}).get('className', ''),
                     'title': n.get('client', {}).get('title', '')} for n in nodes]
        except Exception as e:
            logger.error(f"parse bspc: {e}")
            return []

    def launch_app(self, command: str) -> bool:
        # bspwm no lanza procesos: fallback universal (setsid)
        return _run(['setsid', '-f', command])[0] == 0

    def focus_window(self, title: str, cls: str = None) -> bool:
        target = f'class={cls}' if cls else f'title={title}'
        return _run(['bspc', 'node', '-f', target])[0] == 0


class GenericDEAdapter(EnvironmentAdapter):
    """KDE/GNOME/XFCE/MATE/Cinnamon/LXQt y WMs apilables: superficie parcial."""

    name = 'generic-de'

    def __init__(self, desktop: str):
        self.desktop = desktop

    def capabilities(self) -> set:
        caps = {Capability.LAUNCH_APP, Capability.LIST_WINDOWS}
        if _has('gsettings'):
            caps.add(Capability.SET_DARK_MODE)
            if _has('gsettings') and self.desktop in ('gnome',):
                pass
        if _has('wmctrl', 'xdotool'):
            caps.add(Capability.LIST_WINDOWS)
        if self.desktop == 'xfce' and _has('xfconf-query'):
            caps.add(Capability.SET_WALLPAPER)
        if _has('xdg-desktop-portal-gtk', 'gnome-screensaver-command') or self.desktop == 'gnome':
            caps.add(Capability.LOCK_SCREEN)
        return caps

    def set_dark_mode(self, dark: bool) -> bool:
        scheme = 'prefer-dark' if dark else 'prefer-light'
        code, _, err = _run(['gsettings', 'set',
                             'org.gnome.desktop.interface', 'color-scheme', scheme])
        if code != 0:
            logger.error(f"gsettings: {err}")
        return code == 0

    def set_wallpaper(self, path: str) -> bool:
        if self.desktop == 'xfce':
            code, out, _ = _run(['xfconf-query', '-c', 'xfce4-desktop',
                                 '-p', '/backdrop/screen0/monitorWorkspaceImage'])
            if code == 0:
                code, _, err = _run(['xfconf-query', '-c', 'xfce4-desktop',
                                     '-p', '/backdrop/screen0/monitorWorkspaceImage',
                                     '-s', path])
                return code == 0
        return _run(['gsettings', 'set', 'org.gnome.desktop.background',
                     'picture-uri', f'file://{path}'])[0] == 0

    def lock_screen(self) -> bool:
        for cmd in (['gnome-screensaver-command', '-l'], ['xdg-screensaver', 'lock'], ['loginctl', 'lock-session']):
            if _has(cmd[0]):
                return _run(cmd)[0] == 0
        return False

    def list_windows(self) -> List[dict]:
        if _has('wmctrl'):
            code, out, err = _run(['wmctrl', '-l'])
            if code == 0:
                windows = []
                for line in out.split('\n'):
                    parts = line.split(None, 3)
                    if len(parts) == 4:
                        windows.append({'pid': int(parts[2]) if parts[2].isdigit() else 0,
                                        'class': '', 'title': parts[3]})
                return windows
        return []

    def launch_app(self, command: str) -> bool:
        # Fallback universal: setsid desacopla del ciclo de la TUI
        return _run(['setsid', '-f', command])[0] == 0

    def focus_window(self, title: str, cls: str = None) -> bool:
        # wmctrl -a busca subcadena en el título (X11)
        if _has('wmctrl'):
            return _run(['wmctrl', '-a', title])[0] == 0
        return False


class TTYAdapter(EnvironmentAdapter):
    """TTY / sin entorno: solo la TUI misma y lo portable del core."""

    name = 'tty'

    def capabilities(self) -> set:
        return {Capability.LAUNCH_APP}

    def launch_app(self, command: str) -> bool:
        return _run(['setsid', '-f', command])[0] == 0


class TermuxEnvironmentAdapter(EnvironmentAdapter):
    """Termux/Android: paquetes del prefix, procesos propios; sin WM."""

    name = 'termux'

    def capabilities(self) -> set:
        return {Capability.LAUNCH_APP}

    def launch_app(self, command: str) -> bool:
        # En Termux: setsid desacopla del ciclo de la TUI (sin AM GUI desde TUI)
        return _run(['setsid', '-f', command])[0] == 0


class MacOSEnvironmentAdapter(EnvironmentAdapter):
    """macOS: AppleScript / defaults / open. Sin WM ni variables XDG.

    Las capacidades dependen de las herramientas presentes; nunca se asume
    que una acción existe. Todas las llamadas pasan por _run() (simulable).
    """

    name = 'macos'

    def capabilities(self) -> set:
        caps = set()
        if _has('open'):
            caps.add(Capability.LAUNCH_APP)
        if _has('osascript'):
            caps.add(Capability.LIST_WINDOWS)
        if _has('osascript', 'sqlite3'):
            caps.add(Capability.SET_WALLPAPER)
        if _has('defaults'):
            caps.add(Capability.SET_DARK_MODE)
        if _has('pmset'):
            caps.add(Capability.LOCK_SCREEN)
        return caps

    def set_wallpaper(self, path: str) -> bool:
        tool = _has('osascript', 'sqlite3')
        if tool == 'osascript':
            script = (f'tell application "System Events" to set picture '
                      f'of every desktop to "{path}"')
            code, _, err = _run(['osascript', '-e', script])
        elif tool == 'sqlite3':
            db = os.path.expanduser(
                '~/Library/Application Support/Dock/desktoppicture.db')
            code, _, err = _run(['sqlite3', db,
                                 f"UPDATE data SET value='{path}';"])
            if code == 0:
                _run(['killall', 'Dock'])  # recarga el Dock para aplicar
        else:
            return False
        if code != 0:
            logger.error(f"wallpaper ({tool}): {err}")
        return code == 0

    def set_dark_mode(self, dark: bool) -> bool:
        """AppleInterfaceStyle = Dark, o borrar la clave para modo claro."""
        cmd = (['defaults', 'write', '-g', 'AppleInterfaceStyle',
                '-string', 'Dark'] if dark
               else ['defaults', 'delete', '-g', 'AppleInterfaceStyle'])
        code, _, err = _run(cmd)
        if code != 0:
            logger.error(f"defaults dark mode: {err}")
        return code == 0

    def launch_app(self, command: str) -> bool:
        app = command.strip().split()[0].strip('"\'') if command.strip() else ''
        if not app:
            return False
        return _run(['open', '-a', app])[0] == 0

    def list_windows(self) -> List[dict]:
        script = ('tell application "System Events" to get name '
                  'of every process whose visible is true')
        code, out, err = _run(['osascript', '-e', script])
        if code != 0:
            return []
        return [{'pid': 0, 'class': name.strip(), 'title': name.strip()}
                for name in out.split(',') if name.strip()]

    def focus_window(self, title: str, cls: str = None) -> bool:
        target = cls or title
        if not target:
            return False
        return _run(['open', '-a', target])[0] == 0

    def lock_screen(self) -> bool:
        return _run(['pmset', 'displaysleepnow'])[0] == 0


class WindowsEnvironmentAdapter(EnvironmentAdapter):
    """Windows: PowerShell / reg / cmd / tasklist. Sin WM X11.

    Las capacidades se declaran solo si la herramienda está en PATH; launch-
    or-focus reutiliza LIST_WINDOWS (tasklist) + focus_window (AppActivate).
    """

    name = 'windows'

    def capabilities(self) -> set:
        caps = set()
        if _has('cmd', 'powershell'):
            caps.add(Capability.LAUNCH_APP)
        if _has('powershell', 'reg'):
            caps.add(Capability.SET_WALLPAPER)
        if _has('reg'):
            caps.add(Capability.SET_DARK_MODE)
        if _has('tasklist'):
            caps.add(Capability.LIST_WINDOWS)
        if _has('rundll32'):
            caps.add(Capability.LOCK_SCREEN)
        return caps

    def set_wallpaper(self, path: str) -> bool:
        """SPI_SETDESKWALLPAPER vía PowerShell; fallback al registro."""
        if _has('powershell'):
            ps = (
                'Add-Type -TypeDefinition "'
                'using System;using System.Runtime.InteropServices;'
                'public class TmWall{'
                '[DllImport(\\"user32.dll\\",CharSet=CharSet.Unicode,SetLastError=true)]'
                'public static extern bool SystemParametersInfo(uint a,uint b,string c,uint d);'
                '}";'
                f'[TmWall]::SystemParametersInfo(20,0,\\"{path}\\",3)'
            )
            code, _, err = _run(['powershell', '-NoProfile', '-Command', ps])
        elif _has('reg'):
            key = r'HKCU\Control Panel\Desktop'
            code, _, err = _run(['reg', 'add', key, '/v', 'Wallpaper',
                                 '/t', 'REG_SZ', '/d', path, '/f'])
            if code == 0:
                _run(['rundll32', 'user32.dll,UpdatePerUserSystemParameters'])
        else:
            return False
        if code != 0:
            logger.error(f"wallpaper (windows): {err}")
        return code == 0

    def set_dark_mode(self, dark: bool) -> bool:
        """AppsUseLightTheme: 0 = oscuro, 1 = claro."""
        value = '0' if dark else '1'
        key = (r'HKCU\Software\Microsoft\Windows\CurrentVersion'
               r'\Themes\Personalize')
        code, _, err = _run(['reg', 'add', key, '/v', 'AppsUseLightTheme',
                             '/t', 'REG_DWORD', '/d', value, '/f'])
        if code != 0:
            logger.error(f"reg dark mode: {err}")
        return code == 0

    def launch_app(self, command: str) -> bool:
        return _run(['cmd', '/c', 'start', '', command])[0] == 0

    def list_windows(self) -> List[dict]:
        code, out, err = _run(['tasklist', '/FO', 'CSV', '/NH'])
        if code != 0:
            return []
        windows = []
        for line in out.splitlines():
            parts = [p.strip().strip('"') for p in line.split(',')]
            if len(parts) >= 2 and parts[1].isdigit():
                windows.append({'pid': int(parts[1]), 'class': parts[0],
                                'title': parts[0]})
        return windows

    def focus_window(self, title: str, cls: str = None) -> bool:
        target = cls or title
        if not target:
            return False
        ps = f'(New-Object -ComObject WScript.Shell).AppActivate(\\"{target}\\")'
        return _run(['powershell', '-NoProfile', '-Command', ps])[0] == 0

    def lock_screen(self) -> bool:
        return _run(['rundll32', 'user32.dll,LockWorkStation'])[0] == 0


class EnvironmentDetector:
    """Detecta el entorno activo por variables de sesión y CLIs [ENV]."""

    @staticmethod
    def detect() -> EnvironmentAdapter:
        from .distribution import DistributionDetector

        if DistributionDetector.is_termux():
            return TermuxEnvironmentAdapter()

        # El SO manda antes que cualquier WM/DE (que son propios de Linux).
        system = platform.system()
        if system == 'Darwin':
            return MacOSEnvironmentAdapter()
        if system == 'Windows':
            return WindowsEnvironmentAdapter()

        # WMs tiling por orden de especificidad
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
            return HyprlandAdapter()
        if os.environ.get('SWAYSOCK'):
            return SwayAdapter()
        if os.environ.get('I3SOCK'):
            return I3Adapter()
        if os.environ.get('BSPWM_SOCKET'):
            return BspwmAdapter()

        # DEs y WMs apilables por XDG_CURRENT_DESKTOP
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        if desktop in ('kde', 'kde-plasma', 'plasma', 'gnome', 'unity', 'xfce',
                       'mate', 'cinnamon', 'lxqt', 'lxde', 'pantheon', 'openbox',
                       'fluxbox', 'icewm', 'enlightenment', 'lxqt-migrated'):
            return GenericDEAdapter(desktop.split(':')[-1])

        # Sesión gráfica genérica (Wayland/X11 sin variables conocidas)
        if os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY'):
            return GenericDEAdapter('unknown')

        return TTYAdapter()

    @staticmethod
    def get_info() -> dict:
        adapter = EnvironmentDetector.detect()
        return {
            'name': adapter.name,
            'desktop': os.environ.get('XDG_CURRENT_DESKTOP', ''),
            'session': os.environ.get('XDG_SESSION_TYPE', ''),
            'capabilities': sorted(c.name for c in adapter.capabilities()),
        }
