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
    'backup': 'Copias de seguridad',
    'monitoring': 'Monitorización',
    'finance': 'Finanzas',
    'writing': 'Escritura',
    'accessibility': 'Accesibilidad',
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
             ['repo'], {'github': 'GoogleChrome/chrome-launcher'}),
    AppEntry('brave-browser', 'Navegador web privado y rápido', 'web',
             ['repo', 'flatpak'], {'github': 'brave/brave-browser', 'flatpak': 'com.brave.Browser'}),
    AppEntry('vivaldi', 'Navegador web avec características avanzadas', 'web',
             ['repo']),
    AppEntry('librewolf', 'Navegador Firefox con privacidad reforzada', 'web',
             ['repo', 'flatpak'], {'github': 'LibreWolf/librewolf', 'flatpak': 'io.gitlab.librewolf-community'}),

    # --- Desarrollo ---
    AppEntry('code', 'Visual Studio Code, editor de código', 'development',
             ['repo', 'flatpak', 'snap', 'appimage'], {'github': 'microsoft/vscode', 'flatpak': 'com.visualstudio.code', 'appimage': 'https://github.com/VSCodium/vscodium/releases/download/1.143.17232/VSCodium-1.143.17232-anylinux-x86_64.AppImage'}),
    AppEntry('code-oss', 'Visual Studio Code (build comunitario)', 'development',
             ['repo', 'flatpak'], {'flatpak': 'com.visualstudio.code.oss'}),
        AppEntry('neovim', 'Editor de texto Vim moderno', 'development',
             ['repo'], {'github': 'neovim/neovim'}),
    AppEntry('git', 'Sistema de control de versiones', 'development', ['repo']),
    AppEntry('gh', 'CLI de GitHub', 'development', ['repo'], {'github': 'cli/cli'}),
    AppEntry('docker', 'Plataforma de contenedores', 'virtualization',
             ['repo'], {'github': 'docker/cli'}),
    AppEntry('docker-compose', 'Definición de aplicaciones multi-contenedor', 'virtualization', ['repo']),
    AppEntry('podman', 'Gestor de contenedores sin daemon', 'virtualization', ['repo']),
    AppEntry('go', 'Lenguaje de programación Go', 'development', ['repo']),
    AppEntry('rustup', 'Instalador del toolchain de Rust', 'development',
             ['repo', 'github'], {'github': 'rust-lang/rustup'}),
    AppEntry('nodejs', 'Entorno de ejecución JavaScript', 'development', ['repo']),
    AppEntry('python3', 'Lenguaje de programación Python', 'development', ['repo']),
    AppEntry('postman', 'Plataforma de desarrollo de APIs', 'development',
             ['repo', 'snap'], {'github': 'postmanlabs/postman-app-support'}),

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
    AppEntry('blender', 'Suite de modelado 3D', 'graphics', ['repo', 'flatpak'], {'github': 'blender/blender', 'flatpak': 'org.blender.Blender'}),

    # --- Oficina y productividad ---
    AppEntry('libreoffice', 'Suite ofimática', 'office', ['repo', 'flatpak'], {'flatpak': 'org.libreoffice.LibreOffice'}),
    AppEntry('onlyoffice-desktopeditors', 'Editores de documentos', 'office', ['repo', 'flatpak'], {'flatpak': 'org.onlyoffice.desktopeditors'}),
    AppEntry('thunderbird', 'Cliente de correo', 'communication', ['repo', 'flatpak', 'snap'], {'github': 'mozilla/releases-comm-central', 'flatpak': 'org.mozilla.Thunderbird'}),
    AppEntry('obsidian', 'Gestor de notas Markdown', 'productivity',
             ['repo', 'flatpak', 'snap', 'appimage'], {'github': 'obsidianmd/obsidian-releases', 'flatpak': 'md.obsidian.Obsidian', 'appimage': 'https://github.com/obsidianmd/obsidian-releases/releases/download/v1.15.1/Obsidian-1.15.1.AppImage'}),
    AppEntry('joplin', 'Gestor de notas', 'productivity', ['repo', 'flatpak', 'appimage'], {'github': 'laurent22/joplin', 'appimage': 'https://github.com/laurent22/joplin/releases/download/v3.7.22/Joplin-3.7.22.AppImage'}),
    AppEntry('zotero', 'Gestor de referencias bibliográficas', 'science', ['repo', 'flatpak'], {'github': 'zotero/zotero'}),

    # --- Comunicación ---
    AppEntry('discord', 'Chat de voz y texto', 'communication',
             ['repo', 'flatpak', 'snap'], {'flatpak': 'com.discordapp.Discord'}),
    AppEntry('telegram-desktop', 'Mensajería instantánea', 'communication',
             ['repo', 'flatpak', 'snap'], {'github': 'telegramdesktop/tdesktop', 'flatpak': 'org.telegram.desktop'}),
    AppEntry('signal-desktop', 'Mensajería cifrada', 'communication',
             ['repo', 'flatpak'], {'github': 'signalapp/Signal-Desktop'}),
    AppEntry('slack', 'Colaboración en equipo', 'communication',
             ['repo', 'snap'], {'flatpak': 'com.slack.Slack'}),
    AppEntry('zoom', 'Videoconferencias', 'communication',
             ['repo'], {'github': 'zoom/dts'}),

    # --- Juegos ---
    AppEntry('steam', 'Plataforma de juegos', 'games', ['repo', 'flatpak'], {'flatpak': 'com.valvesoftware.Steam'}),
    AppEntry('lutris', 'Gestor de juegos', 'games', ['repo', 'flatpak'], {'github': 'lutris/lutris'}),
    AppEntry('heroic-games-launcher', 'Lanzador de juegos', 'games',
             ['repo', 'flatpak'], {'github': 'HeroicGamesLauncher/HeroicGamesLauncher'}),
    AppEntry('wine', 'Compatibilidad con Windows', 'games', ['repo']),
    AppEntry('retroarch', 'Emulador de consolas', 'games', ['repo', 'flatpak'], {'flatpak': 'org.libretro.RetroArch'}),

    # --- Seguridad ---
    AppEntry('ufw', 'Cortafuegos sencillo', 'security', ['repo']),
    AppEntry('firewalld', 'Cortafuegos dinámico', 'security', ['repo']),
    AppEntry('fail2ban', 'Protección contra intrusiones', 'security', ['repo']),
    AppEntry('clamav', 'Antivirus', 'security', ['repo']),
    AppEntry('keepassxc', 'Gestor de contraseñas', 'security', ['repo', 'flatpak', 'appimage'], {'github': 'keepassxreboot/keepassxc', 'flatpak': 'org.keepassxc.KeePassXC', 'appimage': 'https://github.com/keepassxreboot/keepassxc/releases/download/2.8.0/KeePassXC-2.8.0-1-x86_64.AppImage'}),
    AppEntry('bitwarden', 'Gestor de contraseñas', 'security', ['repo', 'flatpak', 'snap'], {'github': 'bitwarden/clients', 'flatpak': 'com.bitwarden.desktop'}),
    AppEntry('veracrypt', 'Cifrado de discos', 'security', ['repo', 'github'], {'github': 'veracrypt/VeraCrypt'}),

    # --- Bases de datos ---
    AppEntry('postgresql', 'Sistema de base de datos', 'database', ['repo']),
    AppEntry('mysql', 'Sistema de base de datos', 'database', ['repo']),
    AppEntry('sqlite3', 'Base de datos embebida', 'database', ['repo']),
    AppEntry('redis', 'Almacén de datos en memoria', 'database', ['repo']),
    AppEntry('mongodb', 'Base de datos NoSQL', 'database', ['repo']),
    AppEntry('dbeaver', 'Cliente de bases de datos', 'database', ['repo', 'flatpak'], {'github': 'dbeaver/dbeaver'}),

    # --- Virtualización ---
    AppEntry('virtualbox', 'Máquinas virtuales', 'virtualization', ['repo']),
    AppEntry('virt-manager', 'Gestor de máquinas virtuales', 'virtualization', ['repo', 'flatpak'], {'flatpak': 'org.virt_manager.virt-manager'}),
    AppEntry('qemu', 'Emulador de hardware', 'virtualization', ['repo']),

    # --- IA ---
    AppEntry('ollama', 'Ejecuta modelos de lenguaje localmente', 'ai', ['repo', 'github'], {'github': 'ollama/ollama'}),
    
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
    AppEntry('anki', 'Tarjetas de memorización', 'education', ['repo', 'flatpak'], {'github': 'ankitects/anki'}),
    AppEntry('khan-academy', 'Plataforma educativa', 'education', ['github'], {'github': 'KhanAcademy/khan-academy'}),
    # --- Extensión Beta/estable: más apps y categorías ---
    AppEntry('firefox-developer-edition', 'Firefox Developer Edition', 'web',
             ['repo', 'flatpak'], {'flatpak': 'org.mozilla.firefoxdeveloperedition'}),
    AppEntry('qutebrowser', 'Navegador basado en Qt y Vim', 'web', ['repo']),
    AppEntry('newsboat', 'Lector de noticias RSS de terminal', 'web', ['repo', 'github'], {'github': 'newsboat/newsboat'}),
    AppEntry('liferea', 'Agregador de noticias y podcasts', 'web', ['repo', 'flatpak'], {'flatpak': 'org.liferea.Liferea'}),
    AppEntry('zed', 'Editor de código de alto rendimiento', 'development',
             ['repo', 'github'], {'github': 'zed-industries/zed'}),
    AppEntry('helix', 'Editor modal con LSP nativo', 'development', ['repo', 'github'], {'github': 'helix-editor/helix'}),
    AppEntry('micro', 'Editor de terminal fácil de usar', 'development', ['repo']),
    AppEntry('k9s', 'Terminal UI para Kubernetes', 'development', ['repo', 'github'], {'github': 'derailed/k9s'}),
    AppEntry('terraform', 'Infraestructura como código', 'development', ['repo']),
    AppEntry('ansible', 'Automatización de configuración', 'development', ['repo']),
    AppEntry('direnv', 'Entornos por directorio', 'development', ['repo', 'github'], {'github': 'direnv/direnv'}),
    AppEntry('tokei', 'Contador de líneas de código', 'development', ['repo', 'github'], {'github': 'XAMPPRocky/tokei'}),
    AppEntry('hyperfine', 'Benchmarking de comandos', 'development', ['repo', 'github'], {'github': 'sharkdp/hyperfine'}),
    AppEntry('gdb', 'Depurador GNU', 'development', ['repo']),
    AppEntry('valgrind', 'Detector de fugas de memoria', 'development', ['repo']),
    AppEntry('meson', 'Sistema de compilación', 'development', ['repo']),
    AppEntry('ninja', 'Herramienta de compilación', 'development', ['repo']),
    AppEntry('alacritty', 'Terminal GPU acelerado', 'terminal', ['repo', 'github'], {'github': 'alacritty/alacritty'}),
    AppEntry('kitty', 'Terminal GPU acelerado', 'terminal', ['repo', 'github'], {'github': 'kovidgoyal/kitty'}),
    AppEntry('foot', 'Terminal ligero para Wayland', 'terminal', ['repo', 'github'], {'github': 'dnffi/foot'}),
    AppEntry('wezterm', 'Terminal con multiplexor', 'terminal', ['repo', 'github'], {'github': 'wez/wezterm'}),
    AppEntry('ghostty', 'Terminal nativo rápido', 'terminal', ['repo', 'github'], {'github': 'ghostty-org/ghostty'}),
    AppEntry('fastfetch', 'Información del sistema en terminal', 'terminal', ['repo', 'github'], {'github': 'fastfetch-cli/fastfetch'}),
    AppEntry('celluloid', 'Reproductor de vídeo de GNOME', 'video', ['repo', 'flatpak'], {'flatpak': 'io.github.celluloid_player.Celluloid'}),
    AppEntry('cmus', 'Reproductor de música de terminal', 'audio', ['repo']),
    AppEntry('ncmpcpp', 'Cliente de MPD en terminal', 'audio', ['repo']),
    AppEntry('strawberry', 'Reproductor de música', 'audio', ['repo', 'flatpak'], {'flatpak': 'org.strawberrymusicplayer.Strawberry'}),
    AppEntry('handbrake', 'Transcodificador de vídeo', 'video', ['repo', 'flatpak'], {'flatpak': 'fr.handbrake.ghb'}),
    AppEntry('shotcut', 'Editor de vídeo multiplataforma', 'video', ['repo', 'flatpak'], {'flatpak': 'org.shotcut.Shotcut'}),
    AppEntry('yt-dlp', 'Descargador de vídeo', 'video', ['repo', 'github'], {'github': 'yt-dlp/yt-dlp'}),
    AppEntry('darktable', 'Revelado de fotografía RAW', 'graphics', ['repo', 'flatpak'], {'flatpak': 'org.darktable.Darktable'}),
    AppEntry('rawtherapee', 'Procesador de imágenes RAW', 'graphics', ['repo']),
    AppEntry('scribus', 'Maquetación editorial', 'graphics', ['repo', 'flatpak'], {'flatpak': 'net.scribus.Scribus'}),
    AppEntry('imagemagick', 'Suite de procesamiento de imágenes', 'graphics', ['repo']),
    AppEntry('feh', 'Visor de imágenes ligero', 'graphics', ['repo']),
    AppEntry('swayimg', 'Visor de imágenes para Wayland', 'graphics', ['repo', 'github'], {'github': 'eXeC64/imv'}),
    AppEntry('onlyoffice', 'Suite ofimática', 'office', ['repo', 'flatpak'], {'flatpak': 'org.onlyoffice.desktopeditors'}),
    AppEntry('calligra', 'Suite ofimática de KDE', 'office', ['repo']),
    AppEntry('calibre', 'Gestor de libros electrónicos', 'office', ['repo', 'flatpak'], {'flatpak': 'com.calibre_ebook.calibre'}),
    AppEntry('zathura', 'Visor de PDF minimalista', 'office', ['repo']),
    AppEntry('foliate', 'Lector de libros electrónicos', 'office', ['repo', 'flatpak'], {'flatpak': 'com.github.johnfactotum.Foliate'}),
    AppEntry('logseq', 'Gestor de notas basado en grafo', 'productivity', ['repo', 'github'], {'github': 'logseq/logseq'}),
    AppEntry('standardnotes', 'Notas cifradas de extremo a extremo', 'productivity', ['repo', 'github'], {'github': 'standardnotes/app'}),
    AppEntry('appflowy', 'Alternativa libre a Notion', 'productivity', ['repo', 'github'], {'github': 'AppFlowy-IO/AppFlowy'}),
    AppEntry('trilium', 'Notas con jerarquía y sincronización', 'productivity', ['repo', 'github'], {'github': 'zadam/trilium'}),
    AppEntry('element', 'Cliente de Matrix', 'communication', ['repo', 'flatpak'], {'flatpak': 'im.riot.Riot'}),
    AppEntry('mumble', 'Voz sobre IP', 'communication', ['repo']),
    AppEntry('weechat', 'IRC de terminal', 'communication', ['repo']),
    AppEntry('irssi', 'IRC de terminal', 'communication', ['repo']),
    AppEntry('gajim', 'Cliente de XMPP', 'communication', ['repo', 'flatpak'], {'flatpak': 'org.gajim.Gajim'}),
    AppEntry('bottles', 'Gestor de prefijos Wine', 'games', ['repo', 'flatpak'], {'flatpak': 'com.usebottles.bottles'}),
    AppEntry('mangohud', 'Overlay de rendimiento', 'games', ['repo']),
    AppEntry('gamemode', 'Optimización de juegos', 'games', ['repo']),
    AppEntry('minetest', 'Juego de voxeles libre', 'games', ['repo']),
    AppEntry('supertuxkart', 'Juego de carreras libre', 'games', ['repo']),
    AppEntry('rkhunter', 'Detector de rootkits', 'security', ['repo']),
    AppEntry('lynis', 'Auditoría de seguridad', 'security', ['repo']),
    AppEntry('gnupg', 'Cifrado y firmas digitales', 'security', ['repo']),
    AppEntry('pass', 'Gestor de contraseñas de terminal', 'security', ['repo']),
    AppEntry('yubikey-manager', 'Administración de YubiKey', 'security', ['repo']),
    AppEntry('sqlitebrowser', 'Editor visual de SQLite', 'database', ['repo', 'flatpak'], {'flatpak': 'org.sqlitebrowser.sqlitebrowser'}),
    AppEntry('pgadmin4', 'Administrador de PostgreSQL', 'database', ['repo', 'flatpak'], {'flatpak': 'org.pgadmin.pgadmin4'}),
    AppEntry('influxdb', 'Base de datos de series temporales', 'database', ['repo']),
    AppEntry('duckdb', 'Base de datos analítica embebida', 'database', ['repo']),
    AppEntry('glances', 'Monitor de recursos multiplataforma', 'monitoring', ['repo', 'github'], {'github': 'nicolargo/glances'}),
    AppEntry('iotop', 'Monitor de E/S de disco', 'monitoring', ['repo']),
    AppEntry('nvtop', 'Monitor de GPU', 'monitoring', ['repo', 'github'], {'github': 'Syllo/nvtop'}),
    AppEntry('ncdu', 'Analizador de uso de disco', 'monitoring', ['repo']),
    AppEntry('duf', 'Espacio en disco legible', 'monitoring', ['repo', 'github'], {'github': 'muesli/duf'}),
    AppEntry('lm-sensors', 'Sensores de hardware', 'monitoring', ['repo']),
    AppEntry('restic', 'Copias de seguridad cifradas', 'backup', ['repo', 'github'], {'github': 'restic/restic'}),
    AppEntry('borgbackup', 'Copias de seguridad deduplicadas', 'backup', ['repo']),
    AppEntry('kopia', 'Copias de seguridad multiplataforma', 'backup', ['repo', 'github'], {'github': 'kopia/kopia'}),
    AppEntry('deja-dup', 'Copias de seguridad de GNOME', 'backup', ['repo', 'flatpak'], {'flatpak': 'org.gnome.DejaDup'}),
    AppEntry('grsync', 'Interfaz para rsync', 'backup', ['repo']),
    AppEntry('gnucash', 'Contabilidad personal', 'finance', ['repo', 'flatpak'], {'flatpak': 'org.gnucash.GnuCash'}),
    AppEntry('homebank', 'Gestión de finanzas personales', 'finance', ['repo']),
    AppEntry('skrooge', 'Finanzas personales de KDE', 'finance', ['repo']),
    AppEntry('kmymoney', 'Finanzas personales', 'finance', ['repo']),
    AppEntry('marktext', 'Editor Markdown', 'writing', ['repo', 'github'], {'github': 'marktext/marktext'}),
    AppEntry('zettlr', 'Editor Markdown académico', 'writing', ['repo', 'github'], {'github': 'Zettlr/Zettlr'}),
    AppEntry('focuswriter', 'Editor de escritura sin distracciones', 'writing', ['repo']),
    AppEntry('orca', 'Lector de pantalla', 'accessibility', ['repo']),
    AppEntry('magnus', 'Lupa de pantalla de GNOME', 'accessibility', ['repo']),
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

# ---------------------------------------------------------------- stacks ---
# Stacks por rol: paquetes del propio catálogo que se instalan en lote.
# Los nombres son los usados por los adapters de cada distribución.
STACKS: Dict[str, List[str]] = {
    'dev': [
        'git', 'python3', 'nodejs', 'code', 'neovim',
        'direnv', 'ripgrep', 'gdb', 'postgresql',
    ],
    'terminal': [
        'alacritty', 'tmux', 'zellij', 'fzf', 'ripgrep',
        'bat', 'starship', 'htop', 'lazygit',
    ],
    'web': [
        'firefox', 'chromium', 'brave-browser',
        'qutebrowser', 'newsboat',
    ],
}

def get_stack_roles() -> List[str]:
    """Devuelve los roles de stack disponibles (dev, terminal, web)."""
    return list(STACKS)

def get_stack(role: str) -> List[str]:
    """Devuelve una copia de los paquetes del stack `role`.

    Raises:
        ValueError: si el rol no existe.
    """
    if role not in STACKS:
        raise ValueError(
            f"Stack desconocido {role!r}; roles disponibles: {', '.join(STACKS)}")
    return list(STACKS[role])
