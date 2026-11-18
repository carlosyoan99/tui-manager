"""
Adapter para Termux/Android (apt del prefix, sin elevación de privilegios).

Soporte limitado por diseño [TERMUX]:
- No hay sudo/doas: todo corre como usuario del prefix.
- `pkg` es un envoltorio de apt con repos propios de Termux.
- `dpkg -l` trae nombre+versión+descripción corta en un solo subproceso
  (a diferencia del adapter de Debian, que hace un subproceso por paquete).
"""

import unicodedata
import logging
from typing import List

from .debian_adapter import DebianAdapter
from .package_adapter import Package, PackageNotFoundError

logger = logging.getLogger(__name__)


def _norm_key(key: str) -> str:
    """Normaliza estados/cabeceras a ASCII minúsculo (inglés/español)."""
    ascii_key = unicodedata.normalize('NFKD', key).encode('ascii', 'ignore').decode()
    return ' '.join(ascii_key.strip().lower().split())


# Aliases del campo Status de `dpkg-query -W` (y variantes localizadas).
_KEY_ALIASES = {
    'install ok installed': 'installed',
    'hold ok installed': 'installed',
    'instalar ok instalado': 'installed',
    'deinstall ok config-files': 'config-files',
    'purge ok not-installed': 'not-installed',
}


def _field(key: str) -> str:
    return _KEY_ALIASES.get(_norm_key(key), '')


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
            if len(parts) >= 3:
                # `dpkg-query -W`: 'install ok installed' = instalado de verdad.
                name, version = parts[0], parts[1]
                if _field(parts[2]) != 'installed':
                    continue
            elif '/' in line:
                # Formato real de `pkg list-installed`: "pkg/version".
                name, _, version = line.partition('/')
                name, version = name.strip(), version.split()[0] if version.split() else ''
                if not name or not version:
                    continue
            else:
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
            # Cabeceras: "Listing... Done" / "Listado... Hecho" / "Ordenando...".
            if not line or _norm_key(line).startswith(
                    ('listing', 'sorting', 'full text', 'listado', 'orden', 'busqueda')):
                continue
            # Formato real: name/version, name/suite version o name/description.
            if '/' in line:
                name, _, rest = line.partition('/')
                tokens = rest.split()
                version = ''
                description = rest.strip()
                if tokens and tokens[0][:1].isdigit():
                    version, description = tokens[0], ' '.join(tokens[1:])
                elif len(tokens) > 1 and tokens[1][:1].isdigit():
                    version, description = tokens[1], ' '.join(tokens[2:])
                packages.append(Package(
                    name=name.strip(),
                    version=version,
                    description=description,
                    installed=False,
                ))
        return packages

    def get_updates_available(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(['apt', 'list', '--upgradable'])
        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []
        packages = []
        for line in stdout.split('\n'):
            # Saltea cabeceras ("Listing..." / "Listado...") y líneas vacías.
            if '/' not in line:
                continue
            name = line.split('/', 1)[0].strip()
            if name:
                packages.append(Package(name=name, installed=True))
        return packages

    def _get_category_description(self, name: str) -> str:
        """Descripción corta por categoría conocida (sin subproceso extra)."""
        for category, pkgs in self.CATEGORIES.items():
            if name in pkgs:
                return f"[{category}]"
        return ""
