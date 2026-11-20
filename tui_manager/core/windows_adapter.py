"""
Adapter para Windows con detección automática del gestor instalado.

Se comprueba ``shutil.which`` en orden de preferencia: winget, scoop, choco.
Todo corre sin elevación (los gestores de usuario no usan sudo):

* winget: ``list / search / show / install / uninstall / upgrade``
* scoop:  ``list / search / info / install / uninstall / update``
* choco:  ``list / search / info / install / uninstall / upgrade``

Los parseadores son tolerantes a tablas alineadas (columnas separadas por 2+
espacios), a filas ``nombre version`` y a la salida pipeada de ``choco``.
"""

import logging
import re
import shutil
from typing import List

from .package_adapter import PackageAdapter, Package, PackageNotFoundError

logger = logging.getLogger(__name__)

MANAGERS = ('winget', 'scoop', 'choco')

_VERSION_RE = re.compile(r'^\d+(?:[.\-_]\w+)*$')
_KEY_RE = re.compile(r'^\s*([^:]+?)\s*:\s*(.*)$')

_NAME_KEYS = {'name', 'package name'}
_ID_KEYS = {'id', 'package id'}
_VERSION_KEYS = {
    'version', 'available', 'latest', 'installed version', 'current version',
}
_DESC_KEYS = {'description', 'summary', 'desc'}
_DEP_KEYS = {'dependencies', 'depends on', 'requires', 'dependency'}


def _norm_key(key: str) -> str:
    return ' '.join(key.strip().lower().split())


class WindowsAdapter(PackageAdapter):
    """Gestor de paquetes de Windows (winget / scoop / choco), sin sudo."""

    def __init__(self, manager: str = None, elevator=None):
        super().__init__(elevator)
        self.manager = manager or self.detect_manager()
        if self.manager not in MANAGERS:
            raise ValueError(f"Gestor de Windows no soportado: {self.manager}")

    @staticmethod
    def detect_manager() -> str:
        """Primer gestor disponible en PATH; winget por defecto."""
        for manager in MANAGERS:
            if shutil.which(manager):
                return manager
        return MANAGERS[0]

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        """Los gestores de Windows no usan elevación: se ignora ``sudo``."""
        return super().execute_command(list(command), sudo=False)

    def _cmd(self, winget: List[str], scoop: List[str], choco: List[str]) -> List[str]:
        """Selecciona el comando según el gestor detectado."""
        return {'winget': winget, 'scoop': scoop, 'choco': choco}[self.manager]

    # --- Parseadores comunes -------------------------------------------------

    @staticmethod
    def _looks_like_version(value: str) -> bool:
        value = value.strip()
        return bool(_VERSION_RE.match(value)) and any(c.isdigit() for c in value)

    @staticmethod
    def _cells(line: str) -> List[str]:
        """Divide una fila en celdas (tabla alineada, pipe o espacios)."""
        if '|' in line:
            return [c.strip() for c in line.split('|') if c.strip()]
        cells = [c.strip() for c in re.split(r'\s{2,}', line.strip()) if c.strip()]
        return cells if len(cells) > 1 else line.split()

    @classmethod
    def _is_noise(cls, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return True
        if all(c in '-= ' for c in stripped):
            return True
        low = stripped.lower()
        if low.startswith((
            'chocolatey v', 'no packages', 'no available', 'no new version',
            'found 0', 'found package', 'searching', 'scanning',
            'the following', 'outdated', 'name  ',
        )):
            return True
        if ' packages installed' in low or ' packages found' in low:
            return True
        cells = [c.lower() for c in cls._cells(stripped)]
        if 'name' in cells and any(
                k in cells for k in ('id', 'version', 'available', 'source',
                                     'latest', 'installed')):
            return True
        return False

    @classmethod
    def _parse_rows(cls, stdout: str, with_description: bool = False,
                    prefer_last_version: bool = False) -> List[Package]:
        packages = []
        for line in stdout.splitlines():
            if cls._is_noise(line):
                continue
            cells = cls._cells(line)
            if not cells:
                continue
            name = cells[0]
            version = ''
            rest = []
            for cell in cells[1:]:
                if cls._looks_like_version(cell):
                    if prefer_last_version or not version:
                        version = cell
                else:
                    rest.append(cell)
            if not name:
                continue
            packages.append(Package(
                name=name,
                version=version,
                description=' '.join(rest) if with_description else '',
                installed=not with_description,
            ))
        return packages

    # --- Listados ------------------------------------------------------------

    def get_installed_packages(self) -> List[Package]:
        cmd = self._cmd(
            ['winget', 'list'],
            ['scoop', 'list'],
            ['choco', 'list', '--local-only'],
        )
        returncode, stdout, stderr = self.execute_command(cmd)
        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []
        packages = self._parse_rows(stdout)
        logger.debug(f"Obtenidos {len(packages)} paquetes instalados ({self.manager})")
        return packages

    def search_packages(self, query: str) -> List[Package]:
        cmd = self._cmd(
            ['winget', 'search', query],
            ['scoop', 'search', query],
            ['choco', 'search', query],
        )
        returncode, stdout, stderr = self.execute_command(cmd)
        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []
        return self._parse_rows(stdout, with_description=True)

    def get_updates_available(self) -> List[Package]:
        cmd = self._cmd(
            ['winget', 'upgrade'],
            ['scoop', 'status'],
            ['choco', 'outdated'],
        )
        returncode, stdout, stderr = self.execute_command(cmd)
        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []
        return self._parse_rows(stdout, prefer_last_version=True)

    # --- Detalle -------------------------------------------------------------

    def get_package_info(self, package_name: str) -> Package:
        cmd = self._cmd(
            ['winget', 'show', package_name],
            ['scoop', 'info', package_name],
            ['choco', 'info', package_name],
        )
        returncode, stdout, stderr = self.execute_command(cmd)
        if returncode != 0:
            raise PackageNotFoundError(
                f"Paquete '{package_name}' no encontrado"
            )

        info = Package(name=package_name, installed=True)
        lines = stdout.splitlines()
        for line in lines:
            match = _KEY_RE.match(line)
            if not match:
                continue
            key = _norm_key(match.group(1))
            value = match.group(2).strip()
            if not value:
                continue
            if key in _NAME_KEYS:
                info.name = value
            elif key in _ID_KEYS:
                if info.name == package_name:
                    info.name = value
            elif key in _VERSION_KEYS and not info.version:
                info.version = value
            elif key in _DESC_KEYS and not info.description:
                info.description = value
            elif key in _DEP_KEYS:
                for dep in value.split(','):
                    dep = dep.strip()
                    if dep and dep not in info.dependencies:
                        info.dependencies.append(dep)

        # choco info imprime "nombre version" como primera línea.
        if not info.version and lines:
            first = lines[0].split()
            if len(first) >= 2 and self._looks_like_version(first[1]):
                info.version = first[1]
        return info

    def get_dependencies(self, package_name: str) -> List[str]:
        try:
            return self.get_package_info(package_name).dependencies
        except PackageNotFoundError:
            return []

    # --- Mutación ------------------------------------------------------------

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        if confirm and not self._confirm(f"¿Instalar '{package_name}'?"):
            return False
        cmd = self._cmd(
            ['winget', 'install', '--id', package_name, '-e',
             '--accept-package-agreements', '--accept-source-agreements'],
            ['scoop', 'install', package_name],
            ['choco', 'install', package_name, '-y'],
        )
        returncode, _, stderr = self.execute_command(cmd)
        if returncode != 0:
            logger.error(f"Error al instalar {package_name}: {stderr}")
            return False
        logger.info(f"Paquete '{package_name}' instalado")
        return True

    def remove_package(self, package_name: str, confirm: bool = True) -> bool:
        if confirm and not self._confirm(f"¿Desinstalar '{package_name}'?"):
            return False
        cmd = self._cmd(
            ['winget', 'uninstall', '--id', package_name],
            ['scoop', 'uninstall', package_name],
            ['choco', 'uninstall', package_name, '-y'],
        )
        returncode, _, stderr = self.execute_command(cmd)
        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False
        logger.info(f"Paquete '{package_name}' desinstalado")
        return True

    def update_cache(self) -> bool:
        cmd = self._cmd(
            ['winget', 'source', 'update'],
            ['scoop', 'update'],
            ['choco', 'update'],
        )
        returncode, _, stderr = self.execute_command(cmd)
        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False
        return True

    def upgrade_all(self) -> bool:
        cmd = self._cmd(
            ['winget', 'upgrade', '--all',
             '--accept-package-agreements', '--accept-source-agreements'],
            ['scoop', 'update', '*'],
            ['choco', 'upgrade', 'all', '-y'],
        )
        returncode, _, stderr = self.execute_command(cmd)
        if returncode != 0:
            logger.error(f"Error al actualizar paquetes: {stderr}")
            return False
        return True

    @staticmethod
    def _confirm(message: str) -> bool:
        answer = input(f"\n{message} (S/n) > ").strip().lower()
        return answer in ('', 's', 'si', 'sí', 'y')
