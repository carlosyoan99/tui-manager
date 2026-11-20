"""
Base PackageAdapter para diferentes gestores de paquetes
"""

import os
import shutil
import subprocess
import logging
from typing import Callable, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: Mensaje accionable cuando no hay credenciales cacheadas y nadie puede
#: pedirlas (CLI no interactiva o hook de elevación ausente/fallido).
SUDO_PASSWORD_REQUIRED = (
    'Se requiere contraseña de sudo; ejecuta sudo -v y reintenta'
)


@dataclass
class Package:
    """Modelo de datos para paquetes"""
    name: str
    version: str = ""
    description: str = ""
    installed: bool = False
    size: str = ""
    dependencies: List[str] = None
    recommends: List[str] = None
    category: str = "other"

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.recommends is None:
            self.recommends = []


class PackageNotFoundError(Exception):
    """Paquete no encontrado"""
    pass


class PackageAdapter:
    """Clase base para adaptadores de paquetes"""

    def __init__(self, elevator: Optional[Callable[[], bool]] = None):
        """Inicializa el adaptador.

        Args:
            elevator: hook opcional sin argumentos que devuelve ``True`` si
                consiguió credenciales elevadas. La UI lo implementa
                suspendiendo la TUI y ejecutando ``sudo -v`` en el TTY real.
                Las subclases no definen ``__init__``, por lo que heredan
                esta firma sin romperse.
        """
        self.elevator = elevator

    def get_installed_packages(self) -> List[Package]:
        """Debe implementar este método"""
        raise NotImplementedError

    def get_package_info(self, package_name: str) -> Package:
        """Debe implementar este método"""
        raise NotImplementedError

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        """Debe implementar este método"""
        raise NotImplementedError

    def remove_package(self, package_name: str, confirm: bool = True) -> bool:
        """Debe implementar este método"""
        raise NotImplementedError

    def search_packages(self, query: str) -> List[Package]:
        """Debe implementar este método"""
        raise NotImplementedError

    def update_cache(self) -> bool:
        """Debe implementar este método"""
        raise NotImplementedError

    def get_updates_available(self) -> List[Package]:
        """Debe implementar este método"""
        raise NotImplementedError

    def get_dependencies(self, package_name: str) -> List[str]:
        """Debe implementar este método"""
        raise NotImplementedError

    def get_orphans(self) -> List[Package]:
        """Paquetes huérfanos (sin dependientes). Base: ninguno."""
        return []

    def clean_orphans(self, confirm: bool = True) -> bool:
        """Elimina huérfanos. Base: no soportado."""
        return False

    def _privilege_tool(self) -> Optional[str]:
        """Devuelve la herramienta de elevación disponible: sudo o doas."""
        if shutil.which('sudo'):
            return 'sudo'
        if shutil.which('doas'):
            return 'doas'
        return None

    def _credentials_cached(self, tool: str) -> bool:
        """Comprueba (sin TTY, sin contraseña) si `tool -n true` funciona."""
        try:
            result = subprocess.run(
                [tool, '-n', 'true'],
                capture_output=True,
                text=True,
                timeout=5,
                stdin=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _run(self, full_command: List[str]) -> tuple:
        """Ejecuta un comando ya resuelto, capturando salida."""
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(
                f"Comando excedió el tiempo de espera: {' '.join(full_command)}")
            return -1, "", "Timeout"
        except Exception as e:
            logger.error(f"Error al ejecutar comando: {e}")
            return -1, "", str(e)

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        """Ejecuta un comando del sistema con elevación segura.

        Nunca guarda ni pasa la contraseña por argumento. Si no somos root:

        1. Comprueba ``sudo -n true`` (o ``doas -n true``) sin TTY.
        2. Con credenciales cacheadas, ejecuta con ``sudo -n`` / ``doas -n``.
        3. Sin caché, llama al hook ``self.elevator`` (la UI suspende la TUI
           y ejecuta ``sudo -v`` en el TTY real) y vuelve a comprobar.
        4. Si sigue sin haber credenciales, devuelve un mensaje accionable.

        Args:
            command: Lista de comandos.
            sudo: Si es True, se requiere elevación.

        Returns:
            (returncode, stdout, stderr)
        """
        # Los adapters BSD gestionan su propia herramienta con `_elevator()`
        # y anteponen el prefijo antes de llegar aquí. Sin hook inyectado se
        # conserva su construcción histórica del comando (compatibilidad).
        if sudo and self.elevator is None and hasattr(self, '_elevator'):
            tool = self._elevator()
            full_command = list(command)
            if tool and (not full_command
                         or full_command[0] not in ('sudo', 'doas')):
                full_command.insert(0, tool)
            return self._run(full_command)

        if not sudo or os.geteuid() == 0:
            return self._run(list(command))

        tool = self._privilege_tool()
        if tool is None:
            return -1, '', SUDO_PASSWORD_REQUIRED

        if self._credentials_cached(tool):
            return self._run([tool, '-n'] + list(command))

        if self.elevator is not None:
            try:
                self.elevator()
            except Exception:
                logger.debug('hook de elevación fallido', exc_info=True)
            if self._credentials_cached(tool):
                return self._run([tool, '-n'] + list(command))

        return -1, '', SUDO_PASSWORD_REQUIRED
