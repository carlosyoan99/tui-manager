"""
Adapter para Arch Linux usando pacman
"""

import re
import logging
from typing import List
from .package_adapter import PackageAdapter, Package, PackageNotFoundError

logger = logging.getLogger(__name__)


class ArchAdapter(PackageAdapter):
    """Gestor para Arch Linux usando pacman"""

    CATEGORIES = {
        'development': ['base-devel', 'gcc', 'g++', 'make', 'cmake', 'git', 'python'],
        'system': ['systemd', 'grub', 'linux', 'init', 'cronie'],
        'multimedia': ['vlc', 'mpv', 'ffmpeg', 'gst-plugins-good', 'gst-plugins-bad'],
        'network': ['networkmanager', 'openssh', 'curl', 'wget', 'git'],
        'games': ['steam', 'lutris', 'wine', 'gamescope'],
        'office': ['libreoffice-fresh', 'thunderbird', 'evince', 'gimp'],
        'utilities': ['vim', 'neovim', 'htop', 'tmux', 'bat', 'ripgrep', 'fzf'],
        'security': ['ufw', 'fail2ban', 'openssh', 'firewalld'],
        'database': ['postgresql', 'mysql', 'sqlite'],
        'other': []
    }

    def get_installed_packages(self) -> List[Package]:
        """Obtiene la lista de paquetes instalados"""
        returncode, stdout, stderr = self.execute_command(['pacman', '-Q', '--info'])

        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        current_package = None

        for line in stdout.split('\n'):
            if line.startswith('Package '):
                if current_package:
                    packages.append(current_package)
                current_package = Package(name=line.split()[1])
            elif current_package and line.startswith('Version '):
                current_package.version = line.split()[1]
            elif current_package and line.startswith('Description '):
                current_package.description = line[12:].strip()
            elif current_package and line.startswith('Depends On '):
                deps = line[11:].strip()
                if deps:
                    current_package.dependencies = [d.strip() for d in deps.split(',')]

        if current_package:
            packages.append(current_package)

        logger.debug(f"Obtenidos {len(packages)} paquetes instalados")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        """Obtiene información detallada de un paquete"""
        returncode, stdout, stderr = self.execute_command(['pacman', '-Si', package_name])

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
            elif line.startswith('Depends On'):
                deps = line.split(':', 1)[1].strip()
                if deps:
                    dependencies = [d.strip() for d in deps.split(',')]

        return Package(
            name=package_name,
            version=version,
            description=description,
            installed=False,  # En pacman -Si no muestra si está instalado
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

        returncode, stdout, stderr = self.execute_command(['pacman', '-S', '--noconfirm', package_name])

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

        returncode, stdout, stderr = self.execute_command(['pacman', '-R', '--noconfirm', package_name])

        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False

        logger.info(f"Paquete '{package_name}' desinstalado exitosamente")
        return True

    def search_packages(self, query: str) -> List[Package]:
        """Busca paquetes por nombre o descripción"""
        returncode, stdout, stderr = self.execute_command(['pacman', '-Ss', query])

        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []

        packages = []
        current_package = None

        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Formato: [nombre] descripción
            if line.startswith('['):
                if current_package:
                    packages.append(current_package)
                name_end = line.find(']')
                if name_end != -1:
                    current_package = Package(name=line[1:name_end])
            elif current_package and not line.startswith(' '):
                # Es parte de la descripción
                current_package.description = line
            elif current_package:
                current_package.description += ' ' + line

        if current_package:
            packages.append(current_package)

        return packages

    def update_cache(self) -> bool:
        """Actualiza la caché de paquetes"""
        print("\nActualizando caché de paquetes...")
        returncode, stdout, stderr = self.execute_command(['pacman', '-Sy'])

        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False

        logger.info("Caché actualizada exitosamente")
        return True

    def get_updates_available(self) -> List[Package]:
        """Obtiene la lista de paquetes que pueden ser actualizados"""
        returncode, stdout, stderr = self.execute_command(['pacman', '-Qu'])

        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            if line.strip():
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

    def _get_category(self, package_name: str) -> str:
        """Obtiene la categoría de un paquete"""
        for category, packages in self.CATEGORIES.items():
            if package_name in packages:
                return category
        return 'other'
