"""
Adapter experimental para NetBSD/OpenBSD vía pkgsrc (pkgin / pkg_add).

pkgin maneja binarios (recomendado); pkg_add es el instalador base.
Soporte marcado como experimental en el roadmap (post-1.0 para NetBSD/OpenBSD).
"""

import os
import shutil
import logging
from typing import List

from .package_adapter import PackageAdapter, Package, PackageNotFoundError

logger = logging.getLogger(__name__)


class PkgsrcAdapter(PackageAdapter):
    """Gestor de paquetes pkgin (pkgsrc) para NetBSD/OpenBSD."""

    def _needs_sudo(self) -> bool:
        return os.geteuid() != 0 and shutil.which('sudo') is not None

    def get_installed_packages(self) -> List[Package]:
        # pkgin list: "pkg-1.2.3 has been installed"
        returncode, stdout, stderr = self.execute_command(
            ['pkgin', 'list'], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []
        packages = []
        for line in stdout.split('\n'):
            stripped = line.strip()
            if not stripped or '-v' not in stripped and '-' not in stripped:
                continue
            token = stripped.split(' ')[0]
            name, _, version = token.rpartition('-')
            if name:
                packages.append(Package(name=name, version=version, installed=True))
        logger.debug(f"Obtenidos {len(packages)} paquetes instalados (pkgsrc)")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        returncode, stdout, stderr = self.execute_command(
            ['pkgin', 'show-deps', package_name], sudo=self._needs_sudo()
        )
        deps = [l.strip() for l in stdout.split('\n') if l.strip()]
        returncode2, stdout2, _ = self.execute_command(
            ['pkgin', 'search', f'^{package_name}$'], sudo=self._needs_sudo()
        )
        if returncode2 != 0 or not stdout2.strip():
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")
        token = stdout2.strip().split(' ')[0]
        name, _, version = token.rpartition('-')
        return Package(
            name=name or package_name, version=version,
            description='', installed=True, dependencies=deps,
        )

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        if confirm and not self._confirm(f"¿Instalar '{package_name}'?"):
            return False
        returncode, _, stderr = self.execute_command(
            ['pkgin', '-y', 'install', package_name], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al instalar {package_name}: {stderr}")
            return False
        logger.info(f"Paquete '{package_name}' instalado")
        return True

    def remove_package(self, package_name: str, confirm: bool = True) -> bool:
        if confirm and not self._confirm(f"¿Desinstalar '{package_name}'?"):
            return False
        returncode, _, stderr = self.execute_command(
            ['pkgin', '-y', 'remove', package_name], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False
        logger.info(f"Paquete '{package_name}' desinstalado")
        return True

    def search_packages(self, query: str) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['pkgin', 'search', query], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []
        packages = []
        for line in stdout.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            token = stripped.split(' ')[0]
            name, _, version = token.rpartition('-')
            if name and version:
                packages.append(Package(
                    name=name, version=version,
                    description=stripped[len(token):].strip(), installed=False,
                ))
        return packages

    def update_cache(self) -> bool:
        returncode, _, stderr = self.execute_command(
            ['pkgin', 'update'], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False
        return True

    def get_updates_available(self) -> List[Package]:
        # pkgin -n install: dry-run con lo que actualizaría
        returncode, stdout, stderr = self.execute_command(
            ['pkgin', '-n', 'install'], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []
        packages = []
        for line in stdout.split('\n'):
            token = line.strip().split(' ')[0]
            name, _, version = token.rpartition('-')
            if name and version and version[0].isdigit():
                packages.append(Package(name=name, version=version, installed=True))
        return packages

    def get_dependencies(self, package_name: str) -> List[str]:
        try:
            return self.get_package_info(package_name).dependencies
        except PackageNotFoundError:
            return []

    @staticmethod
    def _confirm(message: str) -> bool:
        answer = input(f"\n{message} (S/n) > ").strip().lower()
        return answer in ('', 's', 'si', 'sí', 'y')
