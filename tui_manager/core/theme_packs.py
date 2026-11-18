"""
Packs de tema (estilo Omarchy): fuente única de verdad en YAML.

Un pack define una paleta, un wallpaper opcional y overrides por superficie.
Al aplicar, ThemeManager/apply_pack() delega por superficie según las
capacidades del entorno, con backup .bak-tm antes de tocar configs ajenas.
"""

import os
import shutil
import urllib.request
import logging
from dataclasses import dataclass, field
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

THEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'config', 'themes')


def user_themes_dir() -> str:
    """Directorio de packs del usuario (se recalcula: HOME puede cambiar)."""
    return os.path.expanduser('~/.config/tui-manager/themes')


USER_THEMES_DIR = user_themes_dir()  # compatibilidad; usar user_themes_dir()


@dataclass
class ThemePack:
    name: str
    palette: dict = field(default_factory=dict)
    wallpaper: Optional[str] = None
    surfaces: dict = field(default_factory=dict)
    dark: bool = True
    source: str = ''  # ruta del yaml

    @classmethod
    def from_file(cls, path: str) -> 'ThemePack':
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return cls(
            name=data.get('name', os.path.splitext(os.path.basename(path))[0]),
            palette=data.get('palette', {}) or {},
            wallpaper=data.get('wallpaper'),
            surfaces=data.get('surfaces', {}) or {},
            dark=bool(data.get('dark', True)),
            source=path,
        )

    def to_file(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump({
                'name': self.name,
                'dark': self.dark,
                'palette': self.palette,
                'wallpaper': self.wallpaper,
                'surfaces': self.surfaces,
            }, f, default_flow_style=False, allow_unicode=True)


def list_packs() -> list:
    """Packs en orden: usuario primero, luego los incluidos en config/themes."""
    packs = []
    seen = set()
    for base in (user_themes_dir(), THEMES_DIR):
        if os.path.isdir(base):
            for fname in sorted(os.listdir(base)):
                if fname.endswith(('.yaml', '.yml')):
                    if fname not in seen:
                        seen.add(fname)
                        try:
                            packs.append(ThemePack.from_file(os.path.join(base, fname)))
                        except Exception as e:
                            logger.warning(f"Pack inválido {fname}: {e}")
    return packs


def get_pack(name: str) -> Optional[ThemePack]:
    for pack in list_packs():
        if pack.name == name:
            return pack
    return None


def install_pack_from_url(url: str) -> Optional[ThemePack]:
    """Descarga un pack YAML y lo instala en el directorio de usuario."""
    try:
        os.makedirs(user_themes_dir(), exist_ok=True)
        dest = os.path.join(user_themes_dir(), os.path.basename(url.split('?')[0]))
        if not dest.endswith(('.yaml', '.yml')):
            dest += '.yaml'
        urllib.request.urlretrieve(url, dest)
        pack = ThemePack.from_file(dest)
        return pack
    except Exception as e:
        logger.error(f"install_pack_from_url: {e}")
        return None


def remove_pack(name: str) -> bool:
    """Solo remueve packs del directorio de usuario (los incluidos no)."""
    for fname in os.listdir(user_themes_dir()) if os.path.isdir(user_themes_dir()) else []:
        if fname.endswith(('.yaml', '.yml')):
            pack = ThemePack.from_file(os.path.join(user_themes_dir(), fname))
            if pack.name == name:
                os.remove(os.path.join(user_themes_dir(), fname))
                return True
    return False


# ---------- Aplicación por superficie ----------

def _hex_for(palette: dict, *keys, default='#000000'):
    for key in keys:
        if key in palette:
            return palette[key]
    return default


def apply_pack(pack: ThemePack, environment=None) -> dict:
    """
    Aplica el pack por superficie según capacidades.
    Devuelve resumen: {'applied': [...], 'skipped': [...]}.
    """
    from .environment import backup_file, Capability

    applied, skipped = [], []

    # 1. Wallpaper (capacidad del entorno)
    wallpaper = pack.wallpaper
    if wallpaper and environment and environment.supports(Capability.SET_WALLPAPER):
        wallpaper_path = wallpaper
        if not os.path.isabs(wallpaper_path):
            candidate = os.path.join(os.path.dirname(pack.source), wallpaper_path)
            wallpaper_path = candidate if os.path.exists(candidate) else wallpaper_path
        if environment.set_wallpaper(wallpaper_path):
            applied.append('wallpaper')
        else:
            skipped.append('wallpaper')
    elif wallpaper:
        skipped.append('wallpaper')

    # 2. Modo claro/oscuro vía gsettings
    if environment and environment.supports(Capability.SET_DARK_MODE):
        if environment.set_dark_mode(pack.dark):
            applied.append('dark_mode')

    # 3. Terminal: alacritty / foot / kitty (import/include con backup)
    term_home = os.path.expanduser('~/.config/tui-manager/theme-terminal')
    for term, spec in pack.surfaces.items():
        handled = _apply_surface(term, spec, term_home)
        if handled:
            applied.append(term)
        else:
            skipped.append(term)

    return {'applied': applied, 'skipped': skipped}


def _apply_surface(term: str, spec, term_home: str) -> bool:
    """Genera archivo de tema del terminal y lo conecta con include/import."""
    from .environment import backup_file, _has

    os.makedirs(term_home, exist_ok=True)
    generated = os.path.join(term_home, f'{term}-theme')
    try:
        os.remove(generated)
    except OSError:
        pass

    if isinstance(spec, dict) and 'file' in spec:
        # spec['file'] es un yaml/lista de colores provistos por el pack
        with open(generated, 'w') as f:
            if str(spec['file']).endswith('.toml') or term == 'alacritty':
                f.write(_render_alacritty(spec))
            else:
                f.write(str(spec))
    elif isinstance(spec, dict):
        with open(generated, 'w') as f:
            f.write(_render_alacritty(spec))
    else:
        return False

    # Conectar al config del terminal (include/import en una línea, con backup)
    if term == 'alacritty':
        cfg = os.path.expanduser('~/.config/alacritty/alacritty.toml')
        if _connect_include(cfg, 'import', generated):
            return True
    elif term == 'foot':
        cfg = os.path.expanduser('~/.config/foot/foot.ini')
        if _connect_include(cfg, 'include', generated):
            return True
    elif term == 'kitty':
        cfg = os.path.expanduser('~/.config/kitty/kitty.conf')
        if _connect_include(cfg, 'include', generated):
            return True
    return False


def _render_alacritty(colors: dict) -> str:
    """Render simple TOML de colores de terminal."""
    p = colors.get('palette', colors)
    lines = ['[colors]']
    mapping = {
        'bg': 'primary.background', 'fg': 'primary.foreground',
        'accent': 'primary.bright_foreground',
    }
    for key, path in mapping.items():
        if key in p:
            section = path.split('.')
            lines.append('')
            lines.append(f'[colors.{".".join(section[:-1])}]')
            lines.append(f'{section[-1]} = "{p[key]}"')
    return '\n'.join(lines) + '\n'


def _connect_include(cfg_path: str, directive: str, generated: str) -> bool:
    """Añade `directive = <generated>` al config si no está, con backup."""
    from .environment import backup_file

    try:
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        existing = os.path.exists(cfg_path)
        if existing:
            backup_file(cfg_path)
            with open(cfg_path) as f:
                content = f.read()
            if generated in content:
                return True
        else:
            content = ''
        with open(cfg_path, 'a') as f:
            if existing and not content.endswith('\n'):
                f.write('\n')
            f.write(f'{directive} = "{generated}"\n')
        return True
    except Exception as e:
        logger.error(f"_connect_include({cfg_path}): {e}")
        return False
