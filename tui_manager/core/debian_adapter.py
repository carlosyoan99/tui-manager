"""
Adapter para Debian y Ubuntu usando apt (formatos reales verificados):
- apt list --installed:  "curl/stable,now 8.5.0-2 amd64 [installed]"
- apt search:            "curl/stable,now ... [installed]" + desc. indentada
- apt list --upgradable: idem installed, con [upgradable from: ...]
"""

import re
import logging
from typing import List
from .package_adapter import PackageAdapter, Package, PackageNotFoundError
from .categories import CATEGORIES as _BASE_CATEGORIES, get_category as _shared_category

logger = logging.getLogger(__name__)

RE_PKG_LINE = re.compile(r'^(\S+)/(\S+),now\s+([^\s]+)\s+([^\s]+)\s+\[(installed|upgradable)')


class DebianAdapter(PackageAdapter):
    """Gestor para Debian y Ubuntu usando apt"""

    # Solo lectura no necesita sudo (apt list/search/show); escrituras sí.
    _READONLY = {('apt', 'list'), ('apt', 'search'), ('apt', 'show')}

    CATEGORIES = _BASE_CATEGORIES

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        if sudo and len(command) > 1 and (command[0], command[1]) in self._READONLY:
            sudo = False
        return super().execute_command(command, sudo=sudo)

    def get_installed_packages(self) -> List[Package]:
        """Obtiene la lista de paquetes instalados"""
        returncode, stdout, stderr = self.execute_command(['apt', 'list', '--installed'])

        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            match = RE_PKG_LINE.match(line.strip())
            if not match:
                continue
            name, _, version = match.group(1), match.group(2), match.group(3)
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
        returncode, stdout, stderr = self.execute_command(['apt', 'show', package_name])

        if returncode != 0:
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")

        info = Package(name=package_name, installed=True)
        capture_deps = False
        for line in stdout.split('\n'):
            stripped = line.strip()
            if line.startswith((' ', '\t')) and capture_deps:
                if stripped:
                    info.dependencies.extend([d.strip() for d in stripped.split(',')])
            elif stripped.startswith(('Depends:', 'Depends ')):
                value = stripped.split(':', 1)[1].strip() if ':' in stripped else stripped
                info.dependencies.extend([d.strip() for d in value.split(',') if d.strip()])
            elif stripped.startswith('Description'):
                info.description = stripped.split(':', 1)[1].strip() if ':' in stripped else stripped
            elif stripped.startswith('Version'):
                info.version = stripped.split(':', 1)[1].strip() if ':' in stripped else stripped
            elif stripped.startswith('Installed-Size'):
                info.size = stripped.split(':', 1)[1].strip() if ':' in stripped else stripped
        return info

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
        current = None
        for line in stdout.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            first = line.split(None, 1)[0]
            if not line.startswith((' ', '\t')) and '/' in first:
                # Línea de paquete: "curl/stable,now 8.5.0-2 amd64 [...]"
                if current:
                    packages.append(current)
                    current = None
                name = first.split('/', 1)[0]
                installed = '[installed' in line
                version = ''
                tokens = line.split()
                if 'now' in tokens:
                    idx = tokens.index('now')
                    if idx + 1 < len(tokens):
                        version = tokens[idx + 1]
                elif len(tokens) > 1:
                    version = tokens[1]
                current = Package(name=name, version=version, installed=installed)
            elif current:
                current.description = (current.description + ' ' + stripped).strip()

        if current:
            packages.append(current)
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
        for line in stdout.split('\n'):
            match = RE_PKG_LINE.match(line.strip())
            if not match:
                continue
            packages.append(Package(
                name=match.group(1), version=match.group(3), installed=True))
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
