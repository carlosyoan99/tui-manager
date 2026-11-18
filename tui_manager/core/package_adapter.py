"""
Base PackageAdapter para diferentes gestores de paquetes
"""

import subprocess
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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

    def execute_command(self, command: List[str], sudo: bool = True) -> tuple:
        """
        Ejecuta un comando del sistema

        Args:
            command: Lista de comandos
            sudo: Si es True, ejecuta con sudo

        Returns:
            (returncode, stdout, stderr)
        """
        full_command = command.copy()
        if sudo:
            full_command.insert(0, 'sudo')

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Comando excedió el tiempo de espera: {' '.join(command)}")
            return -1, "", "Timeout"
        except Exception as e:
            logger.error(f"Error al ejecutar comando: {e}")
            return -1, "", str(e)
