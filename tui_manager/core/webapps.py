"""
Webapps ligeras: catálogo de sitios y generación de accesos directos.

Función G del roadmap post-1.0. El módulo es deliberadamente pasivo:
compone texto de accesos directos y lo escribe **solo** en el directorio
que el llamador inyecta (``base_dir``). Nunca ejecuta comandos, no abre
el navegador y no consulta la red; las URLs del catálogo son conocidas y
no se verifican aquí.

Plataformas soportadas (según ``platform.system()``):

* Linux / FreeBSD / otro POSIX → ``.desktop`` (``Exec=... <url>``)
* Windows → ``.url`` (InternetShortcut)
* macOS → ``.applescript`` que usa ``open -a`` (sin ejecutarlo)
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebApp:
    """Sitio web ligero que puede convertirse en acceso directo."""

    name: str
    url: str
    category: str = 'general'
    icon_hint: str = 'WEB'


# Catálogo inicial: 12 sitios conocidos, URLs reales (sin verificar red).
WEBAPPS: tuple[WebApp, ...] = (
    WebApp('GitHub', 'https://github.com', 'development', 'GH'),
    WebApp('Gmail', 'https://mail.google.com', 'productivity', 'GM'),
    WebApp('YouTube', 'https://www.youtube.com', 'multimedia', 'YT'),
    WebApp('Wikipedia', 'https://en.wikipedia.org', 'education', 'WP'),
    WebApp('Reddit', 'https://www.reddit.com', 'community', 'RD'),
    WebApp('Spotify Web', 'https://open.spotify.com', 'audio', 'SP'),
    WebApp('Notion', 'https://www.notion.so', 'productivity', 'NT'),
    WebApp('X', 'https://x.com', 'community', 'X'),
    WebApp('LinkedIn', 'https://www.linkedin.com', 'productivity', 'IN'),
    WebApp('Stack Overflow', 'https://stackoverflow.com', 'development', 'SO'),
    WebApp('Google Drive', 'https://drive.google.com', 'office', 'GD'),
    WebApp('Figma', 'https://www.figma.com', 'graphics', 'FG'),
)


# Un nombre de archivo seguro: Unicode permitido, sin caracteres de control
# ni separadores de ruta. ``..`` se rechaza explícitamente (path-traversal).
_NAME_RE = re.compile(r'^[\w][\w .+&_-]{0,79}$', re.UNICODE)
_INVALID_NAME_CHARS = frozenset('/\\:*?"<>|\x00')
_HOST_RE = re.compile(
    r'^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?'
    r'(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$'
)


def _validate_name(name: str) -> str:
    """Valida un nombre usado como base del archivo (anti path-traversal)."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Invalid webapp name: empty')
    if name != name.strip() or '..' in name:
        raise ValueError('Invalid webapp name: path traversal')
    if any(ch in _INVALID_NAME_CHARS or ord(ch) < 32 or ord(ch) == 127
           for ch in name):
        raise ValueError('Invalid webapp name: unsafe characters')
    if not _NAME_RE.fullmatch(name):
        raise ValueError('Invalid webapp name: unsupported characters')
    return name


def _validate_url(url: str) -> str:
    """Acepta exclusivamente URLs ``https://`` con host seguro."""
    if not isinstance(url, str) or not url or not url.lower().startswith('https://'):
        raise ValueError('Invalid webapp URL: only https:// is allowed')
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 or ch in '"\\'
           for ch in url):
        raise ValueError('Invalid webapp URL: unsafe characters')
    parsed = urlparse(url)
    if parsed.scheme.lower() != 'https' or not parsed.netloc or '@' in parsed.netloc:
        raise ValueError('Invalid webapp URL: malformed https URL')
    host = parsed.hostname or ''
    if not _HOST_RE.fullmatch(host):
        raise ValueError('Invalid webapp URL: invalid host')
    return url


def _validate_browser(browser: str | None) -> str:
    """Comprueba que el navegador no inyecte argumentos ni saltos de línea."""
    if browser is None:
        return ''
    if not isinstance(browser, str) or not browser.strip():
        raise ValueError('Invalid browser: empty')
    if any(ord(ch) < 32 or ord(ch) == 127 or ch in '"\\' for ch in browser):
        raise ValueError('Invalid browser: unsafe characters')
    return browser.strip()


def _system_kind(system: str | None = None) -> str:
    """Normaliza ``platform.system()`` a linux | windows | macos."""
    system = system or platform.system()
    if system == 'Windows':
        return 'windows'
    if system == 'Darwin':
        return 'macos'
    return 'linux'  # Linux, FreeBSD y cualquier POSIX razonable


def _default_base_dir(kind: str) -> Path:
    """Directorio de accesos cuando el llamador no inyecta ``base_dir``."""
    if kind == 'windows':
        appdata = os.environ.get('APPDATA')
        root = Path(appdata) if appdata else Path.home() / 'AppData' / 'Roaming'
        return root / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
    if kind == 'macos':
        return Path.home() / 'Applications'
    data_home = os.environ.get('XDG_DATA_HOME')
    root = Path(data_home) if data_home else Path.home() / '.local' / 'share'
    return root / 'applications'


def _browser_tokens(browser: str, kind: str) -> list[str]:
    """Tokens del comando a ejecutar por el acceso directo."""
    if browser:
        return shlex.split(browser)
    if kind == 'macos':
        return ['Safari']
    if kind == 'windows':
        return []
    return ['xdg-open']


def _desktop_content(name: str, url: str, browser: str) -> str:
    tokens = _browser_tokens(browser, 'linux')
    command = ' '.join(shlex.quote(token) for token in [*tokens, url])
    return (
        '[Desktop Entry]\n'
        'Version=1.0\n'
        'Type=Application\n'
        f'Name={name}\n'
        'Comment=Webapp shortcut created by TUI Manager\n'
        f'Exec={command}\n'
        'Icon=web-browser\n'
        'Terminal=false\n'
        'Categories=Network;WebBrowser;\n'
    )


def _url_content(url: str, browser: str) -> str:
    lines = ['[InternetShortcut]', f'URL={url}']
    if browser:
        lines.append(f'IconFile={browser}')
    lines.append('IconIndex=0')
    return '\n'.join(lines) + '\n'


def _applescript_content(url: str, browser: str) -> str:
    app = _browser_tokens(browser, 'macos')[0]
    return (
        '-- Webapp shortcut created by TUI Manager (macOS)\n'
        f'do shell script "open -a " & quoted form of "{app}" '
        f'& " " & quoted form of "{url}"\n'
    )


def create_webapp_desktop_entry(
    name: str,
    url: str,
    browser: str | None = None,
    base_dir: str | Path | None = None,
) -> Path:
    """Crea un acceso directo para una webapp y devuelve su ``Path``.

    Solo escribe ``base_dir / <nombre>.<extension>``. Ni ejecuta nada ni
    escribe fuera de ese directorio; los datos inválidos se rechazan con
    ``ValueError`` antes de cualquier escritura.

    Args:
        name: nombre visible y base del archivo (sin separadores de ruta).
        url: URL ``https://`` del sitio.
        browser: navegador opcional (``firefox``, ``'/usr/bin/brave'``…).
        base_dir: directorio de salida inyectable (obligatorio en tests).

    Raises:
        ValueError: nombre, URL o navegador inválidos, o ruta resultante
            fuera de ``base_dir``.
        OSError: error de E/S al crear el directorio o el archivo.
    """
    name = _validate_name(name)
    url = _validate_url(url)
    browser = _validate_browser(browser)

    kind = _system_kind()
    suffix, content = {
        'linux': ('.desktop', _desktop_content(name, url, browser)),
        'windows': ('.url', _url_content(url, browser)),
        'macos': ('.applescript', _applescript_content(url, browser)),
    }[kind]

    base = Path(base_dir) if base_dir is not None else _default_base_dir(kind)
    base.mkdir(parents=True, exist_ok=True)
    target = base / f'{name}{suffix}'

    # Segunda barrera: aunque el validador cambiara, la ruta resuelta debe
    # seguir siendo hija directa del directorio inyectado.
    if target.resolve(strict=False).parent != base.resolve(strict=False):
        raise ValueError('Invalid webapp name: path escapes base_dir')

    with target.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(content)
    logger.debug('Acceso webapp creado: %s', target)
    return target
