"""
Catálogo de aplicaciones recomendadas y sus categorías.

Centraliza las aplicaciones recomendadas con metadatos ricos para que la TUI
pueda mostrarlas, filtrarlas y ofrecer distintas fuentes de instalación.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AppEntry:
    """Entrada de una aplicación recomendada"""
    name: str
    description: str
    category: str
    # Fuentes disponibles: 'repo', 'github', 'flatpak', 'snap', 'appimage'
    sources: List[str] = field(default_factory=lambda: ['repo'])
    # Identificadores por fuente (ej. {'github': 'Owner/Repo', 'flatpak': 'com.x.App'})
    identifiers: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


# Categorías disponibles (id -> etiqueta en español)
CATEGORIES: Dict[str, str] = {
    'all': 'Todas',
    'development': 'Desarrollo',
    'web': 'Navegadores y Web',
    'system': 'Sistema',
    'multimedia': 'Multimedia',
    'audio': 'Audio',
    'video': 'Vídeo',
    'graphics': 'Gráficos y Diseño',
    'network': 'Red',
    'games': 'Juegos',
    'office': 'Oficina',
    'utilities': 'Utilidades',
    'security': 'Seguridad',
    'database': 'Bases de datos',
    'terminal': 'Terminal',
    'productivity': 'Productividad',
    'communication': 'Comunicación',
    'science': 'Ciencia',
    'education': 'Educación',
    'fonts': 'Fuentes',
    'themes': 'Temas e iconos',
    'virtualization': 'Virtualización',
    'ai': 'Inteligencia Artificial',
    'other': 'Otros',
}


# Catálogo de aplicaciones recomendadas
# Cada app define sus fuentes. Aquellas con fuentes alternativas NOTIFICARÁN al
# usuario y pedirán confirmación antes de instalar (ver alternative_sources.py).
APPS: List[AppEntry] = [
    # --- Navegadores y Web ---
    AppEntry('firefox', 'Navegador web libre y de código abierto', 'web',
             ['repo', 'flatpak', 'snap'], {'github': 'mozilla/firefox', 'flatpak': 'org.mozilla.firefox'}),
    AppEntry('chromium', 'Navegador web basado en Chromium', 'web',
             ['repo', 'flatpak'], {'flatpak': 'org.chromium.Chromium'}),
    AppEntry('google-chrome', 'Navegador web de Google', 'web',
             ['repo', 'appimage'], {'github': 'GoogleChrome/chrome-launcher'}),
    AppEntry('brave-browser', 'Navegador web privado y rápido', 'web',
             ['repo', 'flatpak', 'appimage'], {'github': 'brave/brave-browser', 'flatpak': 'com.brave.Browser'}),
    AppEntry('vivaldi', 'Navegador web avec características avanzadas', 'web',
             ['repo', 'appimage']),
    AppEntry('librewolf', 'Navegador Firefox con privacidad reforzada', 'web',
             ['repo', 'flatpak', 'appimage'], {'github': 'LibreWolf/librewolf', 'flatpak': 'io.gitlab.librewolf-community'}),

    # --- Desarrollo ---
    AppEntry('code', 'Visual Studio Code, editor de código', 'development',
             ['repo', 'flatpak', 'snap', 'appimage'], {'github': 'microsoft/vscode', 'flatpak': 'com.visualstudio.code'}),
    AppEntry('code-oss', 'Visual Studio Code (build comunitario)', 'development',
             ['repo', 'flatpak'], {'flatpak': 'com.visualstudio.code.oss'}),
    AppEntry('cursor', 'Editor de código con IA integrada', 'development',
             ['appimage'], {'github': 'getcursor/cursor'}),
    AppEntry('neovim', 'Editor de texto Vim moderno', 'development',
             ['repo', 'appimage'], {'github': 'neovim/neovim'}),
    AppEntry('git', 'Sistema de control de versiones', 'development', ['repo']),
    AppEntry('gh', 'CLI de GitHub', 'development', ['repo'], {'github': 'cli/cli'}),
    AppEntry('docker', 'Plataforma de contenedores', 'virtualization',
             ['repo', 'appimage'], {'github': 'docker/cli'}),
    AppEntry('docker-compose', 'Definición de aplicaciones multi-contenedor', 'virtualization', ['repo']),
    AppEntry('podman', 'Gestor de contenedores sin daemon', 'virtualization', ['repo']),
    AppEntry('go', 'Lenguaje de programación Go', 'development', ['repo']),
    AppEntry('rustup', 'Instalador del toolchain de Rust', 'development',
             ['repo', 'github'], {'github': 'rust-lang/rustup'}),
    AppEntry('nodejs', 'Entorno de ejecución JavaScript', 'development', ['repo']),
    AppEntry('python3', 'Lenguaje de programación Python', 'development', ['repo']),
    AppEntry('postman', 'Plataforma de desarrollo de APIs', 'development',
             ['repo', 'snap', 'appimage'], {'github': 'postmanlabs/postman-app-support'}),

    # --- Terminal ---
    AppEntry('htop', 'Monitor de procesos interactivo', 'terminal', ['repo']),
    AppEntry('btop', 'Monitor de recursos moderno', 'terminal', ['repo', 'github'], {'github': 'aristocratos/btop'}),
    AppEntry('bottom', 'Monitor de procesos escrito en Rust', 'terminal', ['repo', 'github'], {'github': 'ClementTsang/bottom'}),
    AppEntry('tmux', ' multiplexor de terminal', 'terminal', ['repo']),
    AppEntry('zellij', 'Multiplexor de terminal moderno', 'terminal', ['repo', 'github'], {'github': 'zellij-org/zellij'}),
    AppEntry('fzf', 'Buscador difuso para la terminal', 'terminal', ['repo', 'github'], {'github': 'junegunn/fzf'}),
    AppEntry('ripgrep', 'Búsqueda de texto rápida', 'terminal', ['repo', 'github'], {'github': 'BurntSushi/ripgrep'}),
    AppEntry('bat', 'Reemplazo de cat con resaltado', 'terminal', ['repo', 'github'], {'github': 'sharkdp/bat'}),
    AppEntry('lazygit', 'Interfaz TUI para git', 'terminal', ['repo', 'github'], {'github': 'jesseduffield/lazygit'}),
    AppEntry('lazydocker', 'Interfaz TUI para Docker', 'terminal', ['repo', 'github'], {'github': 'jesseduffield/lazydocker'}),
    AppEntry('yazi', 'Gestor de archivos TUI', 'terminal', ['repo', 'github'], {'github': 'sxyazi/yazi'}),
    AppEntry('starship', 'Prompt de terminal minimalista', 'terminal', ['repo', 'github'], {'github': 'starship/starship'}),

    # --- Multimedia ---
    AppEntry('vlc', 'Reproductor multimedia', 'video', ['repo', 'flatpak', 'snap'], {'flatpak': 'org.videolan.VLC'}),
    AppEntry('mpv', 'Reproductor de vídeo ligero', 'video', ['repo', 'flatpak'], {'github': 'mpv-player/mpv'}),
    AppEntry('obs-studio', 'Grabación y streaming', 'video', ['repo', 'flatpak'], {'github': 'obsproject/obs-studio', 'flatpak': 'com.obsproject.Studio'}),
    AppEntry('kdenlive', 'Editor de vídeo', 'video', ['repo', 'flatpak'], {'flatpak': 'org.kde.kdenlive'}),
    AppEntry('ffmpeg', 'Framework multimedia', 'video', ['repo']),
    AppEntry('spotify', 'Cliente de música en streaming', 'audio',
             ['repo', 'flatpak', 'snap'], {'flatpak': 'com.spotify.Client'}),
    AppEntry('audacity', 'Editor de audio', 'audio', ['repo', 'flatpak'], {'flatpak': 'org.audacityteam.Audacity'}),
    AppEntry('pulseaudio', 'Servidor de sonido', 'audio', ['repo']),
    AppEntry('pipewire', 'Servidor multimedia', 'audio', ['repo']),

    # --- Gráficos y diseño ---
    AppEntry('gimp', 'Editor de imágenes', 'graphics', ['repo', 'flatpak'], {'flatpak': 'org.gimp.GIMP'}),
    AppEntry('inkscape', 'Editor de gráficos vectoriales', 'graphics', ['repo', 'flatpak'], {'flatpak': 'org.inkscape.Inkscape'}),
    AppEntry('krita', 'Editor de pintura digital', 'graphics', ['repo', 'flatpak'], {'flatpak': 'org.kde.krita'}),
    AppEntry('blender', 'Suite de modelado 3D', 'graphics', ['repo', 'flatpak', 'appimage'], {'github': 'blender/blender', 'flatpak': 'org.blender.Blender'}),

    # --- Oficina y productividad ---
    AppEntry('libreoffice', 'Suite ofimática', 'office', ['repo', 'flatpak'], {'flatpak': 'org.libreoffice.LibreOffice'}),
    AppEntry('onlyoffice-desktopeditors', 'Editores de documentos', 'office', ['repo', 'flatpak'], {'flatpak': 'org.onlyoffice.desktopeditors'}),
    AppEntry('thunderbird', 'Cliente de correo', 'communication', ['repo', 'flatpak', 'snap'], {'github': 'mozilla/releases-comm-central', 'flatpak': 'org.mozilla.Thunderbird'}),
    AppEntry('obsidian', 'Gestor de notas Markdown', 'productivity',
             ['repo', 'flatpak', 'snap', 'appimage'], {'github': 'obsidianmd/obsidian-releases', 'flatpak': 'md.obsidian.Obsidian'}),
    AppEntry('joplin', 'Gestor de notas', 'productivity', ['repo', 'flatpak', 'appimage'], {'github': 'laurent22/joplin'}),
    AppEntry('zotero', 'Gestor de referencias bibliográficas', 'science', ['repo', 'flatpak'], {'github': 'zotero/zotero'}),

    # --- Comunicación ---
    AppEntry('discord', 'Chat de voz y texto', 'communication',
             ['repo', 'flatpak', 'snap', 'appimage'], {'flatpak': 'com.discordapp.Discord'}),
    AppEntry('telegram-desktop', 'Mensajería instantánea', 'communication',
             ['repo', 'flatpak', 'snap'], {'github': 'telegramdesktop/tdesktop', 'flatpak': 'org.telegram.desktop'}),
    AppEntry('signal-desktop', 'Mensajería cifrada', 'communication',
             ['repo', 'flatpak'], {'github': 'signalapp/Signal-Desktop'}),
    AppEntry('slack', 'Colaboración en equipo', 'communication',
             ['repo', 'snap', 'appimage'], {'flatpak': 'com.slack.Slack'}),
    AppEntry('zoom', 'Videoconferencias', 'communication',
             ['repo', 'appimage'], {'github': 'zoom/dts'}),

    # --- Juegos ---
    AppEntry('steam', 'Plataforma de juegos', 'games', ['repo', 'flatpak'], {'flatpak': 'com.valvesoftware.Steam'}),
    AppEntry('lutris', 'Gestor de juegos', 'games', ['repo', 'flatpak'], {'github': 'lutris/lutris'}),
    AppEntry('heroic-games-launcher', 'Lanzador de juegos', 'games',
             ['repo', 'flatpak', 'appimage'], {'github': 'HeroicGamesLauncher/HeroicGamesLauncher'}),
    AppEntry('wine', 'Compatibilidad con Windows', 'games', ['repo']),
    AppEntry('retroarch', 'Emulador de consolas', 'games', ['repo', 'flatpak'], {'flatpak': 'org.libretro.RetroArch'}),

    # --- Seguridad ---
    AppEntry('ufw', 'Cortafuegos sencillo', 'security', ['repo']),
    AppEntry('firewalld', 'Cortafuegos dinámico', 'security', ['repo']),
    AppEntry('fail2ban', 'Protección contra intrusiones', 'security', ['repo']),
    AppEntry('clamav', 'Antivirus', 'security', ['repo']),
    AppEntry('keepassxc', 'Gestor de contraseñas', 'security', ['repo', 'flatpak', 'appimage'], {'github': 'keepassxreboot/keepassxc', 'flatpak': 'org.keepassxc.KeePassXC'}),
    AppEntry('bitwarden', 'Gestor de contraseñas', 'security', ['repo', 'flatpak', 'snap', 'appimage'], {'github': 'bitwarden/clients', 'flatpak': 'com.bitwarden.desktop'}),
    AppEntry('veracrypt', 'Cifrado de discos', 'security', ['repo', 'github'], {'github': 'veracrypt/VeraCrypt'}),

    # --- Bases de datos ---
    AppEntry('postgresql', 'Sistema de base de datos', 'database', ['repo']),
    AppEntry('mysql', 'Sistema de base de datos', 'database', ['repo']),
    AppEntry('sqlite3', 'Base de datos embebida', 'database', ['repo']),
    AppEntry('redis', 'Almacén de datos en memoria', 'database', ['repo']),
    AppEntry('mongodb', 'Base de datos NoSQL', 'database', ['repo']),
    AppEntry('dbeaver', 'Cliente de bases de datos', 'database', ['repo', 'flatpak', 'appimage'], {'github': 'dbeaver/dbeaver'}),

    # --- Virtualización ---
    AppEntry('virtualbox', 'Máquinas virtuales', 'virtualization', ['repo']),
    AppEntry('virt-manager', 'Gestor de máquinas virtuales', 'virtualization', ['repo', 'flatpak'], {'flatpak': 'org.virt_manager.virt-manager'}),
    AppEntry('qemu', 'Emulador de hardware', 'virtualization', ['repo']),

    # --- IA ---
    AppEntry('ollama', 'Ejecuta modelos de lenguaje localmente', 'ai', ['repo', 'github'], {'github': 'ollama/ollama'}),
    AppEntry('lmstudio', 'Interfaz para modelos locales', 'ai', ['appimage'], {'github': 'lmstudio-ai/lmstudio'}),

    # --- Sistema y utilidades ---
    AppEntry('networkmanager', 'Gestor de conexiones de red', 'system', ['repo']),
    AppEntry('openssh', 'Cliente y servidor SSH', 'system', ['repo']),
    AppEntry('grub2', 'Gestor de arranque', 'system', ['repo']),
    AppEntry('timeshift', 'Copias de seguridad del sistema', 'system', ['repo']),
    AppEntry('grub-customizer', 'Personalizador de GRUB', 'system', ['repo']),
    AppEntry('curl', 'Herramienta de transferencia de datos', 'utilities', ['repo']),
    AppEntry('wget', 'Descargador de archivos', 'utilities', ['repo']),
    AppEntry('rsync', 'Sincronización de archivos', 'utilities', ['repo']),
    AppEntry('fd', 'Buscador de archivos rápido', 'utilities', ['repo', 'github'], {'github': 'sharkdp/fd'}),
    AppEntry('exa', 'Reemplazo moderno de ls', 'utilities', ['repo', 'github'], {'github': 'ogham/exa'}),
    AppEntry('jq', 'Procesador de JSON', 'utilities', ['repo', 'github'], {'github': 'jqlang/jq'}),

    # --- Fuentes y temas ---
    AppEntry('font-jetbrains-mono', 'Fuente monoespaciada para programación', 'fonts', ['github'], {'github': 'JetBrains/JetBrainsMono'}),
    AppEntry('font-fira-code', 'Fuente con ligaduras para código', 'fonts', ['github'], {'github': 'tonsky/fira'}),
    AppEntry('font-hack', 'Fuente monoespaciada', 'fonts', ['github'], {'github': 'sourcefoundry/hack-fonts'}),
    AppEntry('nord-theme', 'Tema Nord', 'themes', ['github'], {'github': 'nordtheme/nord'}),
    AppEntry('dracula-theme', 'Tema Dracula', 'themes', ['github'], {'github': 'dracula-theme/theme-install'}),

    # --- Educación ---
    AppEntry('anki', 'Tarjetas de memorización', 'education', ['repo', 'flatpak', 'appimage'], {'github': 'ankitects/anki'}),
    AppEntry('khan-academy', 'Plataforma educativa', 'education', ['github'], {'github': 'KhanAcademy/khan-academy'}),
]


def get_app_by_name(name: str) -> AppEntry:
    """Busca una aplicación por nombre (exacto o parcial)"""
    for app in APPS:
        if app.name == name:
            return app
    return None


def search_apps(query: str) -> List[AppEntry]:
    """Busca aplicaciones por nombre o descripción"""
    query = query.lower()
    return [app for app in APPS
            if query in app.name.lower() or query in app.description.lower()]


def get_apps_by_category(category: str) -> List[AppEntry]:
    """Obtiene aplicaciones por categoría"""
    if category == 'all':
        return APPS
    return [app for app in APPS if app.category == category]


def get_all_categories() -> Dict[str, str]:
    """Obtiene todas las categorías"""
    return CATEGORIES.copy()
