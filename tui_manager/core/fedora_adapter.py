"""
Adapter para Fedora usando dnf
"""

import logging
from typing import List
from .package_adapter import PackageAdapter, Package, PackageNotFoundError

logger = logging.getLogger(__name__)


class FedoraAdapter(PackageAdapter):
    """Gestor para Fedora usando dnf"""

    CATEGORIES = {
        'development': ['gcc', 'gcc-c++', 'make', 'cmake', 'git', 'python3-devel'],
        'system': ['systemd', 'grub2', 'kernel', 'cronie'],
        'multimedia': ['vlc', 'mpv', 'ffmpeg', 'gstreamer1-plugins-good'],
        'network': ['NetworkManager', 'openssh', 'curl', 'wget', 'git'],
        'games': ['steam', 'lutris', 'wine', 'gamescope'],
        'office': ['libreoffice', 'thunderbird', 'evince', 'gimp'],
        'utilities': ['vim', 'neovim', 'htop', 'tmux', 'bat', 'ripgrep'],
        'security': ['ufw', 'fail2ban', 'openssh-server', 'firewalld'],
        'database': ['postgresql', 'mysql', 'mariadb', 'sqlite'],
        'other': []
    }

    def get_installed_packages(self) -> List[Package]:
        """Obtiene la lista de paquetes instalados"""
        returncode, stdout, stderr = self.execute_command(['dnf', 'list', 'installed'])

        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        lines = stdout.split('\n')[1:]  # Skip header

        for line in lines:
            if not line.strip():
                continue

            # Formato: package.version.arch
            parts = line.split('.')
            if len(parts) >= 2:
                package_name = parts[0]
                version = parts[1].split('[')[0]

                # Obtener descripción
                description = self._get_description(package_name)

                # Obtener categoría
                category = self._get_category(package_name)

                package = Package(
                    name=package_name,
                    version=version,
                    description=description,
                    installed=True
                )
                packages.append(package)

        logger.debug(f"Obtenidos {len(packages)} paquetes instalados")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        """Obtiene información detallada de un paquete"""
        returncode, stdout, stderr = self.execute_command(['dnf', 'info', package_name])

        if returncode != 0:
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")

        description = ""
        version = ""
        dependencies = []

        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('Description'):
                description = line.split(':', 1)[1].strip()
            elif line.startswith('Version'):
                version = line.split(':', 1)[1].strip()
            elif line.startswith('Dependencies'):
                deps = line.split(':', 1)[1].strip()
                if deps:
                    dependencies = [d.strip() for d in deps.split(',')]

        return Package(
            name=package_name,
            version=version,
            description=description,
            installed=True,
            dependencies=dependencies
        )

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        """Instala un paquete"""
        if confirm:
            print(f"\n¿Deseas instalar el paquete '{package_name}'? (S/n)")
            user_input = input("> ").strip().lower()
            if user_input != 's':
                print("Instalación cancelada")
                return False

        returncode, stdout, stderr = self.execute_command(['dnf', 'install', '-y', package_name])

        if returncode != 0:
            logger.error(f"Error al instalar {package_name}: {stderr}")
            return False

        logger.info(f"Paquete '{package_name}' instalado exitosamente")
        return True

    def remove_package(self, package_name: str, confirm: bool = True) -> bool:
        """Desinstala un paquete"""
        if confirm:
            print(f"\n¿Deseas desinstalar el paquete '{package_name}'? (S/n)")
            user_input = input("> ").strip().lower()
            if user_input != 's':
                print("Desinstalación cancelada")
                return False

        returncode, stdout, stderr = self.execute_command(['dnf', 'remove', '-y', package_name])

        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False

        logger.info(f"Paquete '{package_name}' desinstalado exitosamente")
        return True

    def search_packages(self, query: str) -> List[Package]:
        """Busca paquetes por nombre o descripción"""
        returncode, stdout, stderr = self.execute_command(['dnf', 'search', query])

        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []

        packages = []
        current_package = None

        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('Name :'):
                if current_package:
                    packages.append(current_package)
                current_package = Package(name=line[7:].strip())
            elif current_package and line.startswith('Summary :'):
                current_package.description = line[10:].strip()
            elif current_package and line.startswith('Version :'):
                current_package.version = line[10:].strip()

        if current_package:
            packages.append(current_package)

        return packages

    def update_cache(self) -> bool:
        """Actualiza la caché de paquetes"""
        print("\nActualizando caché de paquetes...")
        returncode, stdout, stderr = self.execute_command(['dnf', 'makecache'])

        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False

        logger.info("Caché actualizada exitosamente")
        return True

    def get_updates_available(self) -> List[Package]:
        """Obtiene la lista de paquetes que pueden ser actualizados"""
        returncode, stdout, stderr = self.execute_command(['dnf', 'check-update'])

        if returncode != 0:
            # check-update puede retornar 100 si hay actualizaciones
            if returncode == 100:
                return []
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if line and not line.startswith('Last metadata'):
                # Formato: package oldversion newversion
                parts = line.split()
                if len(parts) >= 3:
                    package_name = parts[0]
                    new_version = parts[2]

                    package = Package(
                        name=package_name,
                        version=new_version,
                        installed=True
                    )
                    packages.append(package)

        return packages

    def get_dependencies(self, package_name: str) -> List[str]:
        """Obtiene las dependencias de un paquete"""
        try:
            package = self.get_package_info(package_name)
            return package.dependencies
        except PackageNotFoundError:
            return []

    def _get_description(self, package_name: str) -> str:
        """Obtiene la descripción de un paquete"""
        try:
            package = self.get_package_info(package_name)
            return package.description
        except PackageNotFoundError:
            return ""

    def _get_category(self, package_name: str) -> str:
        """Obtiene la categoría de un paquete"""
        for category, packages in self.CATEGORIES.items():
            if package_name in packages:
                return category
        return 'other'
