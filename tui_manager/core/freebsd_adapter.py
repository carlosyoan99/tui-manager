"""
Adapter para FreeBSD usando pkg.

- `pkg` normalmente corre como root; si no somos root y existe sudo, se antepone.
- Formatos de salida tomados de pkg(8) (`pkg info -a`, `pkg search`, `pkg upgrade -n`).
"""

import os
import re
import shutil
import logging
from typing import List

from .package_adapter import PackageAdapter, Package, PackageNotFoundError

logger = logging.getLogger(__name__)


class FreeBSDAdapter(PackageAdapter):
    """Gestor de paquetes pkg de FreeBSD."""

    def _elevator(self):
        """None (root/sin elevación), 'sudo' o 'doas' [BSD: criterio 4]."""
        if os.geteuid() == 0:
            return None
        if shutil.which('sudo'):
            return 'sudo'
        if shutil.which('doas'):
            return 'doas'
        return None

    def _needs_sudo(self) -> bool:
        return self._elevator() is not None

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        if not sudo:
            return super().execute_command(command, sudo=False)
        elevator = self._elevator()
        if elevator == 'doas':
            return super().execute_command(['doas'] + command, sudo=False)
        return super().execute_command(command, sudo=elevator == 'sudo')

    def get_installed_packages(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['pkg', 'info', '-a'], sudo=False
        )
        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        # Formato: name-version    description
        pattern = re.compile(r'^(\S+?)-(\d\S*)\s{2,}(.*)$')
        for line in stdout.split('\n'):
            line = line.rstrip()
            if not line:
                continue
            match = pattern.match(line)
            if match:
                name, version, description = match.groups()
                packages.append(Package(
                    name=name, version=version,
                    description=description.strip(), installed=True,
                ))
        logger.debug(f"Obtenidos {len(packages)} paquetes instalados (FreeBSD)")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        returncode, stdout, stderr = self.execute_command(
            ['pkg', 'info', package_name], sudo=False
        )
        if returncode != 0:
            raise PackageNotFoundError(f"Paquete '{package_name}' no encontrado")

        info = Package(name=package_name, installed=True)
        capture_deps = False
        for line in stdout.split('\n'):
            stripped = line.strip()
            if line.startswith('\t') and capture_deps:
                if stripped:
                    info.dependencies.append(stripped)
            elif stripped.startswith('Version'):
                info.version = stripped.split(':', 1)[1].strip() if ':' in stripped else stripped
            elif stripped.startswith('Description'):
                info.description = stripped.split(':', 1)[1].strip() if ':' in stripped else stripped
            elif stripped.startswith('Depends on:'):
                capture_deps = True
        return info

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        if confirm and not self._confirm(f"¿Instalar '{package_name}'?"):
            return False
        returncode, _, stderr = self.execute_command(
            ['pkg', 'install', '-y', package_name], sudo=self._needs_sudo()
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
            ['pkg', 'remove', '-y', package_name], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False
        logger.info(f"Paquete '{package_name}' desinstalado")
        return True

    def search_packages(self, query: str) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['pkg', 'search', query], sudo=False
        )
        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []
        packages = []
        pattern = re.compile(r'^(\S+?)-(\d\S*)\s+(.*)$')
        for line in stdout.split('\n'):
            match = pattern.match(line.strip())
            if match:
                name, version, description = match.groups()
                packages.append(Package(
                    name=name, version=version,
                    description=description.strip(), installed=False,
                ))
        return packages

    def update_cache(self) -> bool:
        returncode, _, stderr = self.execute_command(
            ['pkg', 'update'], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False
        return True

    def get_updates_available(self) -> List[Package]:
        """Actualizables: pkg upgrade -n → líneas "	name: oldver -> newver"."""
        returncode, stdout, stderr = self.execute_command(
            ['pkg', 'upgrade', '-n'], sudo=False
        )
        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []
        packages = []
        pattern = re.compile(r'^\s+(\S+?):\s+(\S+)\s*->\s*(\S+)')
        for line in stdout.split('\n'):
            match = pattern.match(line)
            if match:
                packages.append(Package(
                    name=match.group(1), version=match.group(3), installed=True))
        return packages

    def remove_orphans(self) -> bool:
        """pkg autoremove -y (huérfanos)."""
        returncode, _, stderr = self.execute_command(
            ['pkg', 'autoremove', '-y'], sudo=self._needs_sudo()
        )
        if returncode != 0:
            logger.error(f"Error en autoremove: {stderr}")
            return False
        return True

    def get_dependencies(self, package_name: str) -> List[str]:
        try:
            return self.get_package_info(package_name).dependencies
        except PackageNotFoundError:
            return []

    @staticmethod
    def _confirm(message: str) -> bool:
        answer = input(f"\n{message} (S/n) > ").strip().lower()
        return answer in ('', 's', 'si', 'sí', 'y')

    # --- Huérfanos (pkg autoremove) ---

    def get_orphans(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['pkg', 'autoremove', '-n'], sudo=self._needs_sudo())
        if returncode != 0:
            logger.error(f"Error al listar huérfanos: {stderr}")
            return []
        orphans = []
        pattern = re.compile(r'^(\S+?)-(\d\S*)$')
        for line in stdout.split('\n'):
            match = pattern.match(line.strip())
            if match:
                orphans.append(Package(name=match.group(1),
                                       version=match.group(2)))
        return orphans

    def clean_orphans(self, confirm: bool = True) -> bool:
        returncode, _, stderr = self.execute_command(
            ['pkg', 'autoremove', '-y'], sudo=self._needs_sudo())
        if returncode != 0:
            logger.error(f"Error al limpiar huérfanos: {stderr}")
            return False
        return True
