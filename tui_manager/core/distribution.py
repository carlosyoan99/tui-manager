"""
Módulo de detección de distribución / sistema operativo.

Soporta Linux (Debian, Arch, Fedora, Void, etc.), Termux/Android, BSD
(FreeBSD, NetBSD, OpenBSD, DragonFly), macOS (Homebrew) y Windows
(winget/scoop/choco). La detección prioriza /etc/os-release para obtener el
ID real (evita devolver 'debian' en Ubuntu/Mint).
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)


class DistributionError(Exception):
    """Excepción para errores de detección de distribución"""
    pass


class DistributionDetector:
    """Detector de distribución Linux / sistema operativo"""

    SUPPORTED_DISTRIBUTIONS = [
        'debian', 'ubuntu', 'linuxmint', 'kali', 'mx',
        'arch', 'manjaro', 'endeavouros', 'garuda', 'artix', 'cachyos',
        'fedora', 'rhel', 'centos', 'rocky', 'almalinux',
        'void', 'gentoo',
        'opensuse', 'suse',
        'alpine',
        'termux',
        'freebsd', 'dragonfly',
        'netbsd', 'openbsd',  # experimentales (pkgsrc)
        'darwin', 'macos',  # macOS (Homebrew)
        'windows',         # Windows (winget/scoop/choco)
    ]

    # Archivos de release específicos -> ID. Cada distro se comprueba por SU
    # archivo; las ramas de arch/fedora NUNCA van dentro de debian_version.
    _SPECIFIC_RELEASES = {
        '/etc/arch-release': 'arch',
        '/etc/fedora-release': 'fedora',
        '/etc/void-release': 'void',
        '/etc/gentoo-release': 'gentoo',
        '/etc/suse-release': 'opensuse',
        '/etc/alpine-release': 'alpine',
    }

    _PACKAGE_MANAGERS = {
        'debian': 'apt', 'ubuntu': 'apt', 'linuxmint': 'apt',
        'kali': 'apt', 'mx': 'apt',
        'arch': 'pacman', 'manjaro': 'pacman', 'endeavouros': 'pacman',
        'garuda': 'pacman', 'artix': 'pacman', 'cachyos': 'pacman',
        'fedora': 'dnf', 'rhel': 'dnf', 'centos': 'dnf',
        'rocky': 'dnf', 'almalinux': 'dnf',
        'void': 'xbps', 'gentoo': 'emerge',
        'opensuse': 'zypper', 'suse': 'zypper', 'alpine': 'apk',
        'termux': 'pkg', 'freebsd': 'pkg', 'dragonfly': 'pkg',
        'netbsd': 'pkgin', 'openbsd': 'pkg_add',
        'darwin': 'brew', 'macos': 'brew',
        'windows': 'winget',
    }

    @staticmethod
    def is_termux() -> bool:
        """Detecta Termux/Android vía variables de entorno [TERMUX]."""
        return (
            bool(os.environ.get('TERMUX_VERSION'))
            or 'com.termux' in os.environ.get('PREFIX', '')
        )

    @staticmethod
    def detect() -> str:
        """
        Detecta la distribución del sistema.

        Returns:
            Nombre de la distribución (lowercase, sin espacios)

        Raises:
            DistributionError: Si no se puede detectar el sistema
        """
        # Termux/Android primero: no hay /etc/*-release estándar [TERMUX]
        if DistributionDetector.is_termux():
            return 'termux'

        # 1) os-release / lsb-release PRIMERO: dan el ID real y hacen el
        #    resultado independiente del orden de los chequeos.
        for release_file in ('/etc/os-release', '/etc/lsb-release'):
            if os.path.exists(release_file):
                try:
                    with open(release_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('ID='):
                                distro = line.split('=', 1)[1].strip('"').strip("'")
                                distro = distro.replace(' ', '').lower()
                                if distro:
                                    return distro
                except OSError as e:
                    logger.warning("Error al leer %s: %s", release_file, e)

        # 2) Archivos de release específicos (fallback sin os-release)
        for release_file, distro in DistributionDetector._SPECIFIC_RELEASES.items():
            if os.path.exists(release_file):
                return distro

        # debian_version al final: solo identifica Debian puro. Si fuera
        # Ubuntu/Mint, el paso 1 ya habría devuelto su ID real.
        if os.path.exists('/etc/debian_version'):
            return 'debian'

        # 3) lsb_release como último recurso Linux
        try:
            result = subprocess.run(
                ['lsb_release', '-si'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().lower()
        except (FileNotFoundError, OSError) as e:
            logger.debug("lsb_release no disponible: %s", e)

        # 4) Fallback por kernel (BSD/macOS/Windows sin os-release)
        import platform
        system = platform.system()
        if system == 'DragonFly':
            return 'dragonfly'
        if system in ('FreeBSD', 'NetBSD', 'OpenBSD'):
            return system.lower()
        # macOS y Windows no tienen /etc/*-release ni lsb_release.
        if system == 'Darwin':
            return 'darwin'
        if system == 'Windows':
            return 'windows'

        logger.error("No se pudo detectar la distribución")
        raise DistributionError("No se pudo detectar el sistema operativo")

    @staticmethod
    def get_distro_name() -> str:
        """Obtiene el nombre completo de la distribución."""
        try:
            result = subprocess.run(
                ['lsb_release', '-ds'], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, OSError):
            pass

        try:
            with open('/etc/os-release', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass

        return DistributionDetector.detect()

    @staticmethod
    def get_distro_version() -> str:
        """Obtiene la versión de la distribución."""
        try:
            result = subprocess.run(
                ['lsb_release', '-rs'], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, OSError):
            pass

        try:
            with open('/etc/os-release', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('VERSION_ID='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass

        return 'unknown'

    @staticmethod
    def get_package_manager() -> str:
        """Obtiene el gestor de paquetes por defecto."""
        return DistributionDetector._PACKAGE_MANAGERS.get(
            DistributionDetector.detect(), 'unknown'
        )

    @staticmethod
    def is_supported() -> bool:
        """Verifica si la distribución es soportada."""
        try:
            return DistributionDetector.detect() in DistributionDetector.SUPPORTED_DISTRIBUTIONS
        except DistributionError:
            return False

    @staticmethod
    def get_supported_distributions() -> list:
        """Obtiene lista de distribuciones soportadas."""
        return DistributionDetector.SUPPORTED_DISTRIBUTIONS.copy()

    @staticmethod
    def get_distro_info() -> dict:
        """Obtiene información completa del sistema."""
        return {
            'name': DistributionDetector.get_distro_name(),
            'version': DistributionDetector.get_distro_version(),
            'distribution': DistributionDetector.detect(),
            'package_manager': DistributionDetector.get_package_manager(),
            'supported': DistributionDetector.is_supported(),
        }
