"""
Adapter para Fedora usando dnf. Formatos reales verificados:
- dnf list installed:  "curl.x86_64      8.5.0-2.el9      @fedora"
- dnf search:          "===== Name Matched ====" + "Name : x" / "Summary : y"
- dnf check-update:    lista rpm; rc=100 cuando HAY actualizaciones (no es error)
- dnf repoquery --requires: dependencias
"""

import re
import logging
from typing import List
from .package_adapter import PackageAdapter, Package, PackageNotFoundError
from .categories import CATEGORIES as _BASE_CATEGORIES, get_category as _shared_category

logger = logging.getLogger(__name__)

RE_INFO_FIELD = re.compile(r'^(Name|Version|Summary)\s*:\s*(.*)$')


class FedoraAdapter(PackageAdapter):
    """Gestor para Fedora usando dnf"""

    # dnf list/search/info/check-update/repoquery son de lectura.
    _READONLY = {('dnf', 'list'), ('dnf', 'search'), ('dnf', 'info'),
                 ('dnf', 'check-update'), ('dnf', 'repoquery')}

    CATEGORIES = _BASE_CATEGORIES

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        if sudo and len(command) > 1 and (command[0], command[1]) in self._READONLY:
            sudo = False
        return super().execute_command(command, sudo=sudo)

    @staticmethod
    def _split_rpm_name(col: str):
        """'curl.x86_64' → ('curl', 'x86_64'); nombres con punto sin arch no existen en rpm."""
        if '.' in col and col.rsplit('.', 1)[1] in (
                'i686', 'x86_64', 'aarch64', 'noarch', 'armv7hl', 'ppc64le', 's390x'):
            name, arch = col.rsplit('.', 1)
            return name, arch
        return col, ''

    def get_installed_packages(self) -> List[Package]:
        """Obtiene la lista de paquetes instalados (un subproceso, sin desc. por paquete)."""
        returncode, stdout, stderr = self.execute_command(['dnf', 'list', 'installed'])

        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if not line or line.startswith('Paquetes instalados') or line.startswith('Installed Packages') \
                    or line.startswith('Last metadata') or line.startswith('Package') and 'Arch' in line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name, _arch = self._split_rpm_name(parts[0])
            version = parts[1]
            packages.append(Package(
                name=name,
                version=version,
                description=self._get_category(name),
                installed=True,
            ))
        logger.debug(f"Obtenidos {len(packages)} paquetes instalados")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        """Obtiene información detallada de un paquete"""
        returncode, stdout, stderr = self.execute_command(['dnf', 'info', package_name])

        if returncode != 0:
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")

        info = Package(name=package_name, installed=True)
        for line in stdout.split('\n'):
            match = RE_INFO_FIELD.match(line.strip())
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            if key == 'Version':
                info.version = value
            elif key == 'Summary':
                info.description = value
        info.dependencies = self.get_dependencies(package_name)
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
            ['dnf', 'install', '-y', package_name])

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
            ['dnf', 'remove', '-y', package_name])

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
        for line in stdout.split('\n'):
            match = RE_INFO_FIELD.match(line.strip())
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            if key == 'Name':
                packages.append(Package(name=value, installed=False))
            elif packages:
                if key == 'Summary':
                    packages[-1].description = value
                elif key == 'Version' and not packages[-1].version:
                    packages[-1].version = value
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
        """Obtiene la lista de paquetes actualizables.

        dnf check-update retorna 100 cuando hay actualizaciones: no es error.
        """
        returncode, stdout, stderr = self.execute_command(['dnf', 'check-update'])

        if returncode not in (0, 100):
            logger.error(f"Error al obtener actualizaciones (rc={returncode}): {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if not line or line.startswith('Last metadata') or line.endswith(':'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name, _arch = self._split_rpm_name(parts[0])
            if not name:
                continue
            packages.append(Package(name=name, version=parts[1], installed=True))
        return packages

    def get_dependencies(self, package_name: str) -> List[str]:
        """Dependencias vía dnf repoquery --requires --resolve."""
        returncode, stdout, stderr = self.execute_command(
            ['dnf', 'repoquery', '--requires', '--resolve', '--qf', '%{name}', package_name])
        if returncode != 0:
            return []
        return [line.strip() for line in stdout.split('\n') if line.strip()]

    def _get_category(self, package_name: str) -> str:
        """Categoría desde el dict compartido (sin subprocesos por paquete)."""
        category = _shared_category(package_name)
        return f"[{category}]" if category != 'other' else ""
