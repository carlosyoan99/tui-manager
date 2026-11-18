"""
Adapter para Arch Linux (y derivados: Manjaro, CachyOS, EndeavourOS…)
Formatos reales verificados:
- pacman -Qi:    bloques "Name            : pkg" / "Version : x" / "Description : y"
- pacman -Ss q:  "repo/name 1.0-1 [installed]" + descripción indentada
- pacman -Qu:    "pkg old-version new-version"
"""

import logging
from typing import List
from .package_adapter import PackageAdapter, Package, PackageNotFoundError
from .categories import CATEGORIES as _BASE_CATEGORIES, get_category as _shared_category

logger = logging.getLogger(__name__)


class ArchAdapter(PackageAdapter):
    """Gestor para Arch Linux usando pacman"""

    # pacman -Q*/-Ss son de lectura; -S/-R requieren root.
    _READONLY = {('pacman', '-Qi'), ('pacman', '-Si'),
                 ('pacman', '-Ss'), ('pacman', '-Qu'),
                 ('pacman', '-Qtdq')}

    CATEGORIES = _BASE_CATEGORIES

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        if sudo and len(command) > 1 and (command[0], command[1]) in self._READONLY:
            sudo = False
        return super().execute_command(command, sudo=sudo)

    def get_installed_packages(self) -> List[Package]:
        """Lista instalada vía pacman -Qi (un subproceso, formatos reales)."""
        returncode, stdout, stderr = self.execute_command(['pacman', '-Qi'])

        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        current = None
        for line in stdout.split('\n'):
            if not line.strip():
                # línea en blanco separa bloques: guardar el bloque actual
                if current:
                    packages.append(current)
                    current = None
                continue
            if ':' not in line:
                continue
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            if key == 'Name':
                if current:
                    packages.append(current)
                current = Package(name=value, installed=True)
            elif current is not None:
                if key == 'Version':
                    current.version = value
                elif key == 'Description':
                    current.description = value
                elif key == 'Depends On':
                    if value:
                        current.dependencies = [d.strip() for d in value.split(',')]

        if current:
            packages.append(current)

        logger.debug(f"Obtenidos {len(packages)} paquetes instalados")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        """Obtiene información detallada de un paquete"""
        returncode, stdout, stderr = self.execute_command(['pacman', '-Si', package_name])

        if returncode != 0:
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")

        info = Package(name=package_name, installed=False)
        for line in stdout.split('\n'):
            if ':' not in line:
                continue
            key, _, value = line.partition(':')
            key, value = key.strip(), value.strip()
            if key == 'Description':
                info.description = value
            elif key == 'Version':
                info.version = value
            elif key == 'Depends On':
                if value:
                    info.dependencies = [d.strip() for d in value.split(',')]
        return info

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        """Instala un paquete"""
        if confirm:
            print(f"\n¿Deseas instalar el paquete '{package_name}'? (S/n)")
            user_input = input("> ").strip().lower()
            if user_input != 's':
                print("Instalación cancelada")
                return False

        returncode, stdout, stderr = self.execute_command(
            ['pacman', '-S', '--noconfirm', package_name])

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

        returncode, stdout, stderr = self.execute_command(
            ['pacman', '-R', '--noconfirm', package_name])

        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False

        logger.info(f"Paquete '{package_name}' desinstalado exitosamente")
        return True

    def search_packages(self, query: str) -> List[Package]:
        """Busca paquetes por nombre o descripción (formato repo/name)."""
        returncode, stdout, stderr = self.execute_command(['pacman', '-Ss', query])

        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []

        packages = []
        current = None
        for line in stdout.split('\n'):
            if not line.strip():
                continue
            if not line.startswith((' ', '\t')):
                if current:
                    packages.append(current)
                tokens = line.split()
                full = tokens[0]  # repo/name
                name = full.split('/', 1)[1] if '/' in full else full
                version = tokens[1] if len(tokens) > 1 else ''
                installed = '[installed]' in line
                current = Package(name=name, version=version, installed=installed)
            elif current:
                current.description = (current.description + ' ' + line.strip()).strip()

        if current:
            packages.append(current)
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
            parts = line.split()
            if len(parts) >= 3:
                packages.append(Package(
                    name=parts[0], version=parts[2], installed=True))
        return packages

    def get_dependencies(self, package_name: str) -> List[str]:
        """Obtiene las dependencias de un paquete"""
        try:
            return self.get_package_info(package_name).dependencies
        except PackageNotFoundError:
            return []

    def _get_category(self, package_name: str) -> str:
        """Categoría desde el dict compartido (sin subprocesos por paquete)."""
        category = _shared_category(package_name)
        return f"[{category}]" if category != 'other' else ""

    # --- Huérfanos (pacman -Qtdq / -Rns) ---

    def get_orphans(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(['pacman', '-Qtdq'])
        if returncode != 0:  # rc 1 = no hay huérfanos
            return []
        return [Package(name=line.strip())
                for line in stdout.split('\n') if line.strip()]

    def clean_orphans(self, confirm: bool = True) -> bool:
        orphans = self.get_orphans()
        if not orphans:
            return True
        returncode, _, stderr = self.execute_command(
            ['pacman', '-Rns', '--noconfirm'] + [p.name for p in orphans])
        if returncode != 0:
            logger.error(f"Error al limpiar huérfanos: {stderr}")
            return False
        return True
