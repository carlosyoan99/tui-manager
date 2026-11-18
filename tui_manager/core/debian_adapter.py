"""
Adapter para Debian y Ubuntu usando apt
"""

import re
import logging
from typing import List, Optional
from .package_adapter import PackageAdapter, Package, PackageNotFoundError

logger = logging.getLogger(__name__)


class DebianAdapter(PackageAdapter):
    """Gestor para Debian y Ubuntu usando apt"""

    CATEGORIES = {
        'development': ['build-essential', 'gcc', 'g++', 'make', 'cmake', 'git', 'python3-dev'],
        'system': ['systemd', 'grub', 'kernel', 'init', 'cron'],
        'multimedia': ['vlc', 'mpv', 'ffmpeg', 'gstreamer'],
        'network': ['network-manager', 'openssh', 'curl', 'wget', 'git'],
        'games': ['steam', 'lutris', 'wine', 'gamescope'],
        'office': ['libreoffice', 'thunderbird', 'evince', 'gimp'],
        'utilities': ['vim', 'neovim', 'htop', 'tmux', 'bat', 'ripgrep'],
        'security': ['ufw', 'fail2ban', 'clamav', 'openssh-server'],
        'database': ['postgresql', 'mysql', 'sqlite3'],
        'other': []
    }

    def get_installed_packages(self) -> List[Package]:
        """Obtiene la lista de paquetes instalados"""
        returncode, stdout, stderr = self.execute_command(['apt', 'list', '--installed'])

        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        lines = stdout.split('\n')[1:]  # Skip header

        for line in lines:
            if not line.strip():
                continue

            # Formato: package/version/arch
            parts = line.split('/')
            if len(parts) >= 2:
                package_name = parts[0].strip()
                version = parts[1].split('[')[0].strip()

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
        returncode, stdout, stderr = self.execute_command(['apt', 'show', package_name])

        if returncode != 0:
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")

        description = ""
        version = ""
        size = ""
        dependencies = []

        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('Description:'):
                description = line.split(':', 1)[1].strip()
            elif line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
            elif line.startswith('Size:'):
                size = line.split(':', 1)[1].strip()
            elif line.startswith('Depends:'):
                deps = line.split(':', 1)[1].strip()
                dependencies.extend([d.strip() for d in deps.split(',')])

        return Package(
            name=package_name,
            version=version,
            description=description,
            installed=True,
            size=size,
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

        returncode, stdout, stderr = self.execute_command(['apt', 'install', '-y', package_name])

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

        returncode, stdout, stderr = self.execute_command(['apt', 'remove', '-y', package_name])

        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False

        logger.info(f"Paquete '{package_name}' desinstalado exitosamente")
        return True

    def search_packages(self, query: str) -> List[Package]:
        """Busca paquetes por nombre o descripción"""
        returncode, stdout, stderr = self.execute_command(['apt', 'search', query])

        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []

        packages = []
        current_package = None

        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Formato: package/version
            if line.startswith('N:'):
                if current_package:
                    packages.append(current_package)
                current_package = Package(name=line[2:].strip(), installed=False)
            elif current_package and line.startswith('Description:'):
                current_package.description = line[12:].strip()
            elif current_package and line.startswith('Current version:'):
                current_package.version = line[16:].strip()
                current_package.installed = True

        if current_package:
            packages.append(current_package)

        return packages

    def update_cache(self) -> bool:
        """Actualiza la caché de paquetes"""
        print("\nActualizando caché de paquetes...")
        returncode, stdout, stderr = self.execute_command(['apt', 'update'])

        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False

        logger.info("Caché actualizada exitosamente")
        return True

    def get_updates_available(self) -> List[Package]:
        """Obtiene la lista de paquetes que pueden ser actualizados"""
        returncode, stdout, stderr = self.execute_command(['apt', 'list', '--upgradable'])

        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []

        packages = []
        lines = stdout.split('\n')[1:]  # Skip header

        for line in lines:
            if not line.strip():
                continue

            # Formato: package/oldversion/newversion/arch
            parts = line.split('/')
            if len(parts) >= 3:
                package_name = parts[0].strip()
                old_version = parts[1].strip()
                new_version = parts[2].split('[')[0].strip()

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
