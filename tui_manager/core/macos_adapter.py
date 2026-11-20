"""
Adapter para macOS usando Homebrew (brew), sin elevación de privilegios.

Homebrew corre como usuario normal: nunca se anteponen ``sudo``/``doas``.
Los comandos y formatos de salida son los de brew(1):

* ``brew list --formula --versions`` -> ``nombre version`` por línea.
* ``brew search <q>``                -> cabeceras ``==> ...`` + nombres.
* ``brew info <name>``              -> ``name: stable X.Y.Z (...)`` y la
  sección ``==> Dependencies`` (``Required:`` / ``Build:``).
* ``brew outdated``                -> ``name (old) < new``.
* ``brew autoremove --dry-run``     -> ``Would uninstall:`` + nombres.

Extras: ``brew upgrade`` (subir todo), ``brew services list`` (servicios) y
``brew cleanup`` (limpiar versiones antiguas).
"""

import logging
import re
from typing import List

from .package_adapter import PackageAdapter, Package, PackageNotFoundError

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r'\d+(?:\.\d+)*(?:[-_][\w.]+)?')
_OUTDATED_RE = re.compile(
    r'^\s*(\S+)\s+(?:\(([^)]*)\)\s*)?(?:<|->)\s*(\S+)'
)


class MacOSAdapter(PackageAdapter):
    """Gestor de paquetes Homebrew para macOS (sin sudo)."""

    # --- Ejecución: Homebrew nunca se ejecuta con privilegios ---

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        """Ignora ``sudo``: brew trabaja en el prefix del usuario."""
        return super().execute_command(list(command), sudo=False)

    # --- Listados ---

    def get_installed_packages(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['brew', 'list', '--formula', '--versions']
        )
        if returncode != 0:
            logger.error(f"Error al obtener paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.splitlines():
            tokens = line.split()
            if not tokens:
                continue
            name = tokens[0]
            # `brew list --formula` sin --versions da sólo el nombre; con
            # --versions añade la versión como segundo token.
            version = tokens[1] if len(tokens) > 1 else ''
            packages.append(Package(name=name, version=version, installed=True))
        logger.debug(f"Obtenidos {len(packages)} paquetes instalados (brew)")
        return packages

    def search_packages(self, query: str) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['brew', 'search', query]
        )
        if returncode != 0:
            logger.error(f"Error al buscar paquetes: {stderr}")
            return []

        packages = []
        for line in stdout.splitlines():
            name = line.strip()
            if not name or name.startswith('==>') or ':' in name:
                continue
            # brew search imprime un nombre por línea (fórmulas y casks).
            packages.append(Package(name=name.split()[0], installed=False))
        return packages

    def get_updates_available(self) -> List[Package]:
        """`brew outdated`: ``curl (8.4.0) < 8.5.0``."""
        returncode, stdout, stderr = self.execute_command(['brew', 'outdated'])
        if returncode != 0:
            logger.error(f"Error al obtener actualizaciones: {stderr}")
            return []

        packages = []
        for line in stdout.splitlines():
            match = _OUTDATED_RE.match(line)
            if match:
                name, _old, new = match.groups()
                packages.append(Package(
                    name=name, version=new.strip('<>'), installed=True))
            elif line.strip() and not line.startswith('==>'):
                # Variante antigua: una sola columna con el nombre.
                packages.append(Package(
                    name=line.split()[0].strip('()'), installed=True))
        return packages

    # --- Detalle ---

    def get_package_info(self, package_name: str) -> Package:
        returncode, stdout, stderr = self.execute_command(
            ['brew', 'info', package_name]
        )
        if returncode != 0:
            raise PackageNotFoundError(
                f"Paquete '{package_name}' no encontrado"
            )

        info = Package(name=package_name, installed=True)
        lines = stdout.splitlines()
        if lines:
            header = lines[0]
            if ':' in header:
                info.name = header.split(':', 1)[0].strip()
                rest = header.split(':', 1)[1]
                match = _VERSION_RE.search(rest)
                if match:
                    info.version = match.group(0)
            if len(lines) > 1 and lines[1].strip():
                info.description = lines[1].strip()

        capture_deps = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('==>'):
                capture_deps = stripped.lower().startswith('==> dependencies')
                continue
            if not capture_deps or ':' not in stripped:
                continue
            key, value = stripped.split(':', 1)
            if key.strip().lower() in ('required', 'build', 'recommended',
                                       'optional'):
                for dep in value.split(','):
                    dep = re.sub(r'\s+[✔✓]\s*$', '', dep).strip()
                    if dep and dep not in info.dependencies:
                        info.dependencies.append(dep)
        return info

    def get_dependencies(self, package_name: str) -> List[str]:
        try:
            return self.get_package_info(package_name).dependencies
        except PackageNotFoundError:
            return []

    # --- Mutación ---

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        if confirm and not self._confirm(f"¿Instalar '{package_name}'?"):
            return False
        returncode, _, stderr = self.execute_command(
            ['brew', 'install', package_name]
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
            ['brew', 'uninstall', package_name]
        )
        if returncode != 0:
            logger.error(f"Error al desinstalar {package_name}: {stderr}")
            return False
        logger.info(f"Paquete '{package_name}' desinstalado")
        return True

    def update_cache(self) -> bool:
        returncode, _, stderr = self.execute_command(['brew', 'update'])
        if returncode != 0:
            logger.error(f"Error al actualizar caché: {stderr}")
            return False
        return True

    def upgrade_all(self) -> bool:
        """`brew upgrade`: actualiza todas las fórmulas."""
        returncode, _, stderr = self.execute_command(['brew', 'upgrade'])
        if returncode != 0:
            logger.error(f"Error al actualizar paquetes: {stderr}")
            return False
        return True

    # --- Huérfanos / limpieza (brew autoremove) ---

    def get_orphans(self) -> List[Package]:
        returncode, stdout, stderr = self.execute_command(
            ['brew', 'autoremove', '--dry-run']
        )
        if returncode != 0:
            logger.error(f"Error al listar huérfanos: {stderr}")
            return []
        orphans = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if (not stripped or stripped.startswith('==>')
                    or stripped.endswith(':') or stripped.startswith('Would')):
                continue
            orphans.append(Package(name=stripped.split()[0]))
        return orphans

    def clean_orphans(self, confirm: bool = True) -> bool:
        if confirm and not self._confirm('¿Eliminar dependencias huérfanas?'):
            return False
        returncode, _, stderr = self.execute_command(['brew', 'autoremove'])
        if returncode != 0:
            logger.error(f"Error al limpiar huérfanos: {stderr}")
            return False
        return True

    # --- Extras opcionales ---

    def get_services(self) -> List[Package]:
        """`brew services list`: nombre y estado de los servicios."""
        returncode, stdout, stderr = self.execute_command(
            ['brew', 'services', 'list']
        )
        if returncode != 0:
            logger.error(f"Error al listar servicios: {stderr}")
            return []
        services = []
        for line in stdout.splitlines():
            parts = line.split()
            if parts and not parts[0].lower().startswith('name'):
                services.append(Package(name=parts[0],
                                        description=parts[1] if len(parts) > 1 else ''))
        return services

    def cleanup(self) -> bool:
        """`brew cleanup`: borra versiones descargadas antiguas."""
        returncode, _, stderr = self.execute_command(['brew', 'cleanup'])
        if returncode != 0:
            logger.error(f"Error en cleanup: {stderr}")
            return False
        return True

    @staticmethod
    def _confirm(message: str) -> bool:
        answer = input(f"\n{message} (S/n) > ").strip().lower()
        return answer in ('', 's', 'si', 'sí', 'y')
