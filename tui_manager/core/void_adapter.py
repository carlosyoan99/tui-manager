"""
Adapter para Void Linux usando xbps. Formatos reales verificados:
- xbps-query -l:   "ii bash-5.2.26_1   The GNU Bourne Again shell"
- xbps-query -Rs:  "[*] curl-8.5.0_2   description" (instalado) / "[-] pkg-ver desc"
- xbps-query -S:   campos "Description: ..." / "Version: ..." / "Depends: ..."
- xbps-install -n: dry-run, lista "pkg-ver update to ..." o pkg-ver (actualizables)
"""

import re
import unicodedata
import logging
from typing import List
from .package_adapter import PackageAdapter, Package, PackageNotFoundError
from .categories import CATEGORIES as _BASE_CATEGORIES, get_category as _shared_category

logger = logging.getLogger(__name__)

RE_PKGVER = re.compile(r'^(?P<name>.+?)-(?P<version>[0-9][^\s]*)$')


def _norm_key(key: str) -> str:
    """Normaliza una cabecera de `xbps-query -S` a ASCII minúsculo (inglés/español)."""
    ascii_key = unicodedata.normalize('NFKD', key).encode('ascii', 'ignore').decode()
    return ' '.join(ascii_key.strip().lower().split())


# Aliases de campos de `xbps-query -S` en inglés y español.
_KEY_ALIASES = {
    'architecture': 'architecture', 'arquitectura': 'architecture',
    'version': 'version',
    'description': 'description', 'descripcion': 'description',
    'short_desc': 'description', 'short description': 'description',
    'depends': 'depends', 'depends_on': 'depends',
    'dependencias': 'depends', 'depende de': 'depends',
    'installed-size': 'size', 'tamano instalado': 'size',
}


def _field(key: str) -> str:
    return _KEY_ALIASES.get(_norm_key(key), '')


def split_pkgver(token: str):
    """'bash-5.2.26_1' → ('bash', '5.2.26_1'); None si no coincide."""
    match = RE_PKGVER.match(token)
    if match:
        return match.group('name'), match.group('version')
    return None, None


class VoidAdapter(PackageAdapter):
    """Gestor para Void Linux usando xbps"""

    # xbps-query nunca necesita sudo; install/remove sí, salvo dry-run (-n).
    _READONLY_PREFIX = 'xbps-query'

    CATEGORIES = _BASE_CATEGORIES

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        if sudo and command:
            if command[0] == self._READONLY_PREFIX:
                sudo = False
            elif command[0] in ('xbps-install', 'xbps-remove') and '-n' in command:
                sudo = False
        return super().execute_command(command, sudo=sudo)

    def get_installed_packages(self) -> List[Package]:
        """Obtiene la lista de paquetes instalados (descripción incluida en la línea)."""
        returncode, stdout, stderr = self.execute_command(['xbps-query', '-l'])

        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            name, version = split_pkgver(parts[1])
            if not name:
                continue
            description = parts[2].strip() if len(parts) > 2 else self._get_category(name)
            packages.append(Package(
                name=name,
                version=version,
                description=description,
                installed=True,
            ))
        logger.debug(f"Obtenidos {len(packages)} paquetes instalados")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        """Obtiene información detallada de un paquete"""
        returncode, stdout, stderr = self.execute_command(['xbps-query', '-S', package_name])

        if returncode != 0:
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")

        info = Package(name=package_name, installed=False)
        for line in stdout.split('\n'):
            stripped = line.strip()
            if ':' not in stripped:
                continue
            key, _, value = stripped.partition(':')
            field, value = _field(key), value.strip()
            if field == 'description':
                info.description = value
            elif field == 'version':
                info.version = value
            elif field == 'depends' and value:
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

        returncode, stdout, stderr = self.execute_command(['xbps-install', '-y', package_name])

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

        returncode, stdout, stderr = self.execute_command(['xbps-remove', '-y', package_name])

        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False

        logger.info(f"Paquete '{package_name}' desinstalado exitosamente")
        return True

    def search_packages(self, query: str) -> List[Package]:
        """Busca en repos: xbps-query -Rs → '[*] curl-8.5.0_2 desc' / '[-] ...'"""
        returncode, stdout, stderr = self.execute_command(['xbps-query', '-Rs', query])

        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if not line or not line.startswith('['):
                continue
            parts = line.split(None, 2)
            status = parts[0]           # [*] instalado, [-] no instalado
            name, version = split_pkgver(parts[1]) if len(parts) > 1 else (None, None)
            if not name:
                continue
            description = parts[2].strip() if len(parts) > 2 else ''
            packages.append(Package(
                name=name,
                version=version,
                description=description,
                installed=status == '[*]',
            ))
        return packages

    def update_cache(self) -> bool:
        """Actualiza la caché de repos"""
        print("\nActualizando caché de paquetes...")
        returncode, stdout, stderr = self.execute_command(['xbps-install', '-S'])

        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False

        logger.info("Caché actualizada exitosamente")
        return True

    def get_updates_available(self) -> List[Package]:
        """Actualizables: xbps-install -n (dry-run). Cada línea incluye pkg-version."""
        returncode, stdout, stderr = self.execute_command(['xbps-install', '-n'])

        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue
            name, version = split_pkgver(line.split()[0])
            if not name:
                continue
            packages.append(Package(name=name, version=version, installed=True))
        return packages

    def remove_orphans(self) -> bool:
        """Elimina huérfanos: xbps-remove -o."""
        returncode, stdout, stderr = self.execute_command(['xbps-remove', '-y', '-o'])
        if returncode != 0:
            logger.error(f"Error al remover huérfanos: {stderr}")
            return False
        return True

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

    # --- Huérfanos (xbps-remove -o) ---

    def get_orphans(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['xbps-remove', '-o', '-n'])
        if returncode != 0:
            logger.error(f"Error al listar huérfanos: {stderr}")
            return []
        orphans = []
        for line in stdout.split('\n'):
            name, version = split_pkgver(line.strip())
            if name:
                orphans.append(Package(name=name, version=version or ''))
        return orphans

    def clean_orphans(self, confirm: bool = True) -> bool:
        returncode, _, stderr = self.execute_command(
            ['xbps-remove', '-o', '-y'])
        if returncode != 0:
            logger.error(f"Error al limpiar huérfanos: {stderr}")
            return False
        return True
