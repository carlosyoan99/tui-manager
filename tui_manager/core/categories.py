"""
Categorías de paquetes compartidas por todos los adapters.

El dict une los nombres de paquete comunes entre distros (apt/pacman/dnf/
xbps/apk/pkg). El matching es exacto por nombre; incluir variantes de
distro en la misma lista es intencional y seguro.

Categoría "other" es el fallback de _get_category().
"""

CATEGORIES = {
    'development': [
        # Build & control de versiones
        'build-essential', 'gcc', 'gcc-c++', 'g++', 'make', 'cmake', 'meson',
        'ninja-build', 'ninja', 'git', 'git-lfs', 'lazygit', 'gh', 'glab',
        'pre-commit', 'diff', 'patch',
        # Lenguajes y runtimes
        'python3', 'python', 'python3-dev', 'python3-pip', 'python-pip',
        'python3-venv', 'python3.12', 'python3.13',
        'nodejs', 'npm', 'yarn', 'pnpm', 'bun',
        'golang', 'go', 'rust', 'rustup', 'cargo',
        'ruby', 'php', 'php-cli', 'openjdk-21-jdk', 'openjdk-17-jdk',
        'default-jdk', 'dotnet-sdk', 'mono', 'lua', 'luajit', 'perl', 'r-base',
        # Herramientas dev
        'gdb', 'lldb', 'strace', 'valgrind', 'clang', 'clangd',
        'mise', 'asdf', 'sdkman', 'direnv', 'tokei', 'hyperfine',
        # DevOps / infra
        'kubectl', 'helm', 'minikube', 'k9s', 'terraform', 'ansible',
        'vagrant', 'hugo', 'mkdocs', 'pandoc', 'latexmk', 'texlive',
        'texlive-base',
    ],
    'editors': [
        'vim', 'gvim', 'neovim', 'emacs', 'emacs-nox', 'nano', 'micro',
        'helix', 'code', 'visual-studio-code', 'vscode', 'codium',
        'vscodium', 'sublime-text', 'zed', 'zed-editor', 'kate', 'gedit',
        'mousepad', 'textadept', 'featherpad', 'leafpad',
    ],
    'browsers': [
        'firefox', 'firefox-esr', 'librewolf', 'waterfox',
        'chromium', 'chromium-browser', 'google-chrome', 'chrome',
        'brave-browser', 'brave', 'vivaldi', 'opera', 'opera-gx',
        'microsoft-edge', 'epiphany', 'falkon', 'konqueror',
        'torbrowser-launcher', 'qutebrowser', 'surf', 'netsurf', 'lynx', 'w3m',
    ],
    'terminals': [
        'alacritty', 'kitty', 'foot', 'wezterm', 'ghostty', 'konsole',
        'gnome-terminal', 'xterm', 'tilix', 'terminator', 'xfce4-terminal',
        'sakura', 'st', 'urxvt', 'rxvt-unicode',
        'tmux', 'screen', 'zellij',
        'bash', 'zsh', 'fish', 'nushell', 'dash', 'tcsh', 'elvish',
        'starship', 'fastfetch', 'neofetch', 'figlet', 'cowsay',
    ],
    'files': [
        # Gestores de archivos
        'nautilus', 'dolphin', 'thunar', 'nemo', 'pcmanfm', 'ranger',
        'nnn', 'lf', 'yazi', 'midnight-commander', 'mc', 'vifm',
        'doublecmd-gtk', 'krusader', 'xplorer',
        # Compresión
        '7zip', '7z', 'p7zip', '7zip-unzip', 'unzip', 'zip', 'tar', 'gzip',
        'bzip2', 'xz', 'zstd', 'lz4', 'unrar', 'rar', 'xarchiver', 'ark',
        'file-roller', 'engrampa', 'peazip',
    ],
    'multimedia': [
        # Reproducción
        'vlc', 'mpv', 'smplayer', 'celluloid', 'audacious', 'rhythmbox',
        'deadbeef', 'strawberry', 'clementine', 'lollypop', 'gmpc',
        'cmus', 'moc', 'ncmpcpp', 'musikcube', 'spotify-player',
        # Producción audio/video
        'obs-studio', 'obs', 'kdenlive', 'shotcut', 'openshot', 'dav1d',
        'audacity', 'ardour', 'lmms', 'easyeffects', 'pulseeffects', 'sox',
        'handbrake', 'mkvtoolnix', 'ffmpeg', 'ffmpegthumbs', 'yt-dlp',
        'youtube-dl', 'ffmpeg-python', 'gstreamer', 'gst-plugins-good',
        'gst-plugins-bad', 'gstreamer1-plugins-good', 'gst-plugins-good',
        'pipewire', 'pipewire-pulse', 'wireplumber',
    ],
    'graphics': [
        'gimp', 'krita', 'inkscape', 'blender', 'darktable', 'rawtherapee',
        'digikam', 'mypaint', 'pinta', 'scribus', 'pixelorama', 'drawing',
        'imagemagick', 'graphicsmagick', 'exiftool', 'feh', 'sxiv', 'nsxiv',
        'imv', 'swayimg', 'eog', 'eye-of-gnome', 'gwenview', 'shotwell',
        'geeqie', 'nomacs', 'xnview',
    ],
    'office': [
        'libreoffice', 'libreoffice-fresh', 'libreoffice-still',
        'libreoffice-still-nogui', 'onlyoffice', 'calligra', 'abiword',
        'gnumeric', 'koffice',
        # Correo
        'thunderbird', 'evolution', 'geary', 'kmail', 'mailspring',
        'betterbird', 'neomutt', 'mutt', 'aerc', 'claws-mail',
        # PDF / lectura
        'zathura', 'evince', 'okular', 'xpdf', 'pdfarranger', 'calibre',
        'foliate', 'koreader', 'sioyek', 'qpdf', 'pdftk',
        # Productividad
        'obsidian', 'joplin', 'logseq', 'nextcloud-client',
        'zotero', 'freeplane', 'xournalpp',
    ],
    'communication': [
        'discord', 'telegram-desktop', 'signal-desktop', 'element',
        'element-desktop', 'schildichat-desktop', 'slack', 'teams',
        'teams-for-linux', 'zoom', 'zoom-client', 'mumble', 'irssi',
        'weechat', 'thunderbird-chat', 'fractal', 'gajim', 'pidgin',
        'wire', 'viber', 'chatsen', 'gauntlet',
    ],
    'games': [
        # Launchers / gestión
        'steam', 'lutris', 'heroic-games-launcher', 'heroic', 'bottles',
        'gamehub', 'playonlinux', 'minigalaxy',
        # Capas de compatibilidad / rendimiento
        'wine', 'wine-staging', 'proton-cachyos', 'protontricks', 'gamescope',
        'mangohud', 'gamemode', 'vkbasalt', 'luxtorpeda',
        # Emulación
        'retroarch', 'duckstation', 'pcsx2', 'rpcs3', 'ppsspp', 'dolphin-emu',
        'melonds', 'mgba', 'visualboyadvance-m', 'yuzu-early-access',
        'ryujinx', 'citra', 'aesir', 'vita3k', 'mupen64plus', 'desmume',
        # Nativos / clásicos
        'minecraft-launcher', 'minetest', 'supertux', 'supertuxkart',
        '0ad', 'openttd', 'freeciv', 'freedroidrpg', 'brogue', 'nethack',
        'cataclysm-dda', 'wesnoth', 'wesnoth-1.16', 'kde-games',
    ],
    'network': [
        # Transferencia
        'curl', 'wget', 'aria2', 'axel', 'httpie', 'transmission-gtk',
        'transmission-qt', 'transmission-cli', 'qbittorrent', 'deluge',
        'ktorrent', 'rtorrent', 'aria2c',
        # Nube / sincronización
        'syncthing', 'nextcloud-client', 'rclone', 'dropbox', 'insync',
        'onedrive', 'google-drive-ocamlfuse', 'megasync',
        # VPN / privacidad
        'tailscale', 'wireguard-tools', 'openvpn', 'nordvpn', 'mullvad-vpn',
        'protonvpn-gui', 'tor', 'proxychains', 'privoxy', 'tor-browser',
        # Red
        'networkmanager', 'network-manager', 'wpa_supplicant', 'iwd',
        'nmap', 'wireshark', 'tcpdump', 'iputils', 'bind-tools', 'whois',
        'traceroute', 'mtr', 'netstat-nat', 'ifconfig',
        'openssh', 'openssh-client', 'openssh-server', 'mosh', 'et',
    ],
    'system': [
        # Monitorización
        'htop', 'btop', 'iotop', 'iftop', 'glances', 'nvtop', 'radeontop',
        's-tui', 'bottom', 'zabbix-agent', 'netdata', 'prometheus-node-exporter',
        # Disco / backup
        'gparted', 'parted', 'fdisk', 'util-linux', 'ncdu', 'duf', 'dust',
        'baobab', 'kdf', 'timeshift', 'rsnapshot', 'rsync', 'restic',
        'borgbackup', 'borg', 'kopia', 'smartmontools', 'lm-sensors',
        'lmsensors', 'nvme-cli', 'hddtemp',
        # Núcleo del sistema
        'systemd', 'systemd-resolved', 'grub', 'grub2', 'kernel', 'linux',
        'linux-lts', 'linux-cachyos', 'linux-zen', 'linux-mainline',
        'cron', 'cronie', 'anacron', 'procps', 'procps-ng', 'psmisc',
        'polkit', 'polkit-gnome', 'udisks2', 'accountsservice',
        'cachyos-packages', 'base-devel',
    ],
    'security': [
        'ufw', 'firewalld', 'fail2ban', 'clamav', 'rkhunter', 'lynis',
        'auditd', 'aide', 'ossec-hids', 'nmap-scripts',
        # Contraseñas / cifrado
        'keepassxc', 'bitwarden-desktop', 'bitwarden', 'pass',
        'password-store', 'gnupg', 'gpg', 'gpg2', 'age', 'sops',
        'yubikey-manager', 'pcsc-tools', 'seahorse', 'kwalletmanager',
    ],
    'databases': [
        'postgresql', 'postgresql-client', 'mysql', 'mariadb', 'sqlite3',
        'sqlite', 'redis', 'valkey', 'mongodb', 'influxdb', 'timescaledb',
        'duckdb', 'diesel-cli', 'psql', 'sqlitebrowser', 'dbeaver',
        'pgadmin4', 'mysql-workbench',
    ],
    'virtualization': [
        'docker', 'docker-compose', 'podman', 'podman-compose', 'buildah',
        'skopeo', 'containerd', 'k3s', 'k3d', 'kind', 'lima', 'colima',
        'virtualbox', 'virtualbox-guest-utils', 'qemu', 'qemu-kvm',
        'qemu-full', 'libvirt', 'virt-manager', 'virsh', 'vagrant',
        'multipass', 'waydroid', 'anbox', 'lxc', 'lxd', 'incus',
        'wine', 'bottles',
    ],
    'other': [],
}

_ALIASES = {
    'utilities': ('files', 'system'),
}


def get_category(package_name: str) -> str:
    """Devuelve la categoría para un nombre de paquete, o 'other'."""
    name = package_name.strip().lower()
    for category, packages in CATEGORIES.items():
        if name in packages:
            return category
    # Coincidencia por prefijo conocida: distros con variantes de versión
    # (p.ej. firefox-esr, libreoffice-fresh, python3.12)
    for category, packages in CATEGORIES.items():
        for pkg in packages:
            if name.startswith(pkg) and len(name) <= len(pkg) + 6:
                return category
    return 'other'


def categories() -> list:
    """Lista de categorías disponibles (sin 'other')."""
    return [c for c in CATEGORIES if c != 'other']
