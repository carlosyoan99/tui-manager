"""
Módulo de detección de distribución Linux
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)


class DistributionError(Exception):
    """Excepción para errores de detección de distribución"""

    pass


class DistributionDetector:
    """Detector de distribución Linux"""

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
    ]

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
        Detecta la distribución del sistema

        Returns:
            Nombre de la distribución (lowercase, sin espacios)

        Raises:
            DistributionError: Si no se puede detectar la distribución
        """
        # Termux/Android primero: no hay /etc/*-release estándar [TERMUX]
        if DistributionDetector.is_termux():
            return 'termux'

        # Detectar por archivos específicos de distribución
        if os.path.exists('/etc/debian_version'):
            # Debian o Ubuntu
            if os.path.exists('/etc/arch-release'):
                return 'arch'
            elif os.path.exists('/etc/fedora-release'):
                return 'fedora'
            else:
                return 'debian'

        elif os.path.exists('/etc/void-release'):
            return 'void'

        elif os.path.exists('/etc/gentoo-release'):
            return 'gentoo'

        elif os.path.exists('/etc/suse-release'):
            return 'opensuse'

        elif os.path.exists('/etc/alpine-release'):
            return 'alpine'

        # Intentar leer /etc/os-release
        for release_file in ['/etc/os-release', '/etc/lsb-release']:
            if os.path.exists(release_file):
                try:
                    with open(release_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('ID='):
                                distro = line.split('=')[1].strip('"')
                                # Limpiar el nombre (remover espacios, etc.)
                                distro = distro.replace(' ', '').lower()
                                return distro
                except Exception as e:
                    logger.warning(f"Error al leer {release_file}: {e}")

        # Intentar usar lsb_release
        try:
            result = subprocess.run(
                ['lsb_release', '-si'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                distro = result.stdout.strip().lower()
                return distro
        except Exception as e:
            logger.debug(f"lsb_release no disponible: {e}")

        # Fallback por kernel (BSD sin os-release)
        import platform
        system = platform.system()
        if system in ('FreeBSD', 'NetBSD', 'OpenBSD', 'DragonFly'):
            return system.lower() if system != 'DragonFly' else 'dragonfly'

        # No se pudo detectar
        logger.error("No se pudo detectar la distribución")
        raise DistributionError("No se pudo detectar la distribución Linux")

    @staticmethod
    def get_distro_name() -> str:
        """
        Obtiene el nombre completo de la distribución

        Returns:
            Nombre de la distribución
        """
        try:
            result = subprocess.run(
                ['lsb_release', '-ds'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Intentar leer /etc/os-release
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('PRETTY_NAME='):
                        return line.split('=')[1].strip('"')
        except Exception:
            pass

        return DistributionDetector.detect()

    @staticmethod
    def get_distro_version() -> str:
        """
        Obtiene la versión de la distribución

        Returns:
            Versión de la distribución
        """
        try:
            result = subprocess.run(
                ['lsb_release', '-rs'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Intentar leer /etc/os-release
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('VERSION_ID='):
                        return line.split('=')[1].strip('"')
        except Exception:
            pass

        return 'unknown'

    @staticmethod
    def get_package_manager() -> str:
        """
        Obtiene el gestor de paquetes por defecto

        Returns:
            Nombre del gestor de paquetes
        """
        distribution = DistributionDetector.detect()

        package_managers = {
            'debian': 'apt',
            'ubuntu': 'apt',
            'linuxmint': 'apt',
            'kali': 'apt',
            'mx': 'apt',
            'arch': 'pacman',
            'manjaro': 'pacman',
            'endeavouros': 'pacman',
            'garuda': 'pacman',
            'artix': 'pacman',
            'fedora': 'dnf',
            'rhel': 'dnf',
            'centos': 'dnf',
            'rocky': 'dnf',
            'almalinux': 'dnf',
            'void': 'xbps',
            'gentoo': 'emerge',
            'opensuse': 'zypper',
            'alpine': 'apk'
        }

        return package_managers.get(distribution, 'unknown')

    @staticmethod
    def is_supported() -> bool:
        """
        Verifica si la distribución es soportada

        Returns:
            True si la distribución es soportada
        """
        try:
            distro = DistributionDetector.detect()
            return distro in DistributionDetector.SUPPORTED_DISTRIBUTIONS
        except Exception:
            return False

    @staticmethod
    def get_supported_distributions() -> list:
        """
        Obtiene lista de distribuciones soportadas

        Returns:
            Lista de nombres de distribuciones soportadas
        """
        return DistributionDetector.SUPPORTED_DISTRIBUTIONS

    @staticmethod
    def get_distro_info() -> dict:
        """
        Obtiene información completa de la distribución

        Returns:
            Diccionario con información de la distribución
        """
        return {
            'name': DistributionDetector.get_distro_name(),
            'version': DistributionDetector.get_distro_version(),
            'distribution': DistributionDetector.detect(),
            'package_manager': DistributionDetector.get_package_manager(),
            'supported': DistributionDetector.is_supported()
        }
