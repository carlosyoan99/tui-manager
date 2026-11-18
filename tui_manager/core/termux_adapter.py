"""
Adapter para Termux/Android (apt del prefix, sin elevación de privilegios).

Soporte limitado por diseño [TERMUX]:
- No hay sudo/doas: todo corre como usuario del prefix.
- `pkg` es un envoltorio de apt con repos propios de Termux.
- `dpkg -l` trae nombre+versión+descripción corta en un solo subproceso
  (a diferencia del adapter de Debian, que hace un subproceso por paquete).
"""

import logging
from typing import List

from .debian_adapter import DebianAdapter
from .package_adapter import Package, PackageNotFoundError

logger = logging.getLogger(__name__)


class TermuxAdapter(DebianAdapter):
    """apt del prefix de Termux, sin sudo."""

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        # En Termux nunca hay elevación: ignoramos el parámetro sudo.
        return super().execute_command(command, sudo=False)

    def get_installed_packages(self) -> List[Package]:
        """Lista instalada vía dpkg (rápido, un solo subproceso)."""
        returncode, stdout, stderr = self.execute_command(
            ['dpkg-query', '-W', '-f=${Package}\\t${Version}\\t${Status}\\n']
        )
        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            name, version, status = parts[0], parts[1], parts[2]
            # 'install ok installed' = instalado de verdad
            if 'ok installed' not in status:
                continue
            packages.append(Package(
                name=name,
                version=version,
                description=self._get_category_description(name),
                installed=True,
            ))
        logger.debug(f"Obtenidos {len(packages)} paquetes instalados (Termux)")
        return packages

    def search_packages(self, query: str) -> List[Package]:
        """Busca en los repos de Termux vía pkg (envoltorio de apt)."""
        returncode, stdout, stderr = self.execute_command(['pkg', 'search', query])
        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.split('\n'):
            line = line.strip()
            if not line or line.lower().startswith(('listing', 'sorting', 'full text')):
                continue
            # Formato: name/description
            if '/' in line:
                name, _, description = line.partition('/')
                packages.append(Package(
                    name=name.strip(),
                    description=description.strip(),
                    installed=False,
                ))
        return packages

    def get_updates_available(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(['apt', 'list', '--upgradable'])
        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []
        packages = []
        for line in stdout.split('\n')[1:]:  # saltear header "Listing..."
            if not line.strip():
                continue
            parts = line.split('/')
            if parts:
                packages.append(Package(name=parts[0].strip(), installed=True))
        return packages

    def _get_category_description(self, name: str) -> str:
        """Descripción corta por categoría conocida (sin subproceso extra)."""
        for category, pkgs in self.CATEGORIES.items():
            if name in pkgs:
                return f"[{category}]"
        return ""
