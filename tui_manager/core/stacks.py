"""
Stacks por rol e instalación en lote.

`StackInstaller` sólo delega en el gestor/adaptador que se le inyecta: nunca
ejecuta comandos por su cuenta, por lo que funciona igual con un adaptador real
(Debian, Arch, ...) que con un doble de prueba.

También expone `fwupd_available()`, una capacidad opcional: detecta si
`fwupdmgr` está en PATH sin llegar a ejecutarlo nunca.
"""
import shutil
from typing import Dict, List, Mapping, Optional

from .app_catalog import STACKS, get_stack

FWUPD_MANAGER = 'fwupdmgr'


class UnknownStackError(ValueError):
    """El rol de stack solicitado no existe."""


class StackInstallResult(dict):
    """Resultados por paquete de una instalación de stack.

    Se comporta como un ``dict[paquete: bool]`` y añade propiedades cómodas
    para inspeccionar la instalación en lote.
    """

    def __init__(self, role: str, results: Mapping[str, bool]):
        super().__init__(results)
        self.role = role

    @property
    def success(self) -> bool:
        """True sólo si se intentó al menos un paquete y todos OK."""
        return bool(self) and all(self.values())

    @property
    def installed(self) -> List[str]:
        """Paquetes cuyo resultado fue correcto."""
        return [package for package, ok in self.items() if ok]

    @property
    def failed(self) -> List[str]:
        """Paquetes cuyo resultado fue incorrecto o lanzaron excepción."""
        return [package for package, ok in self.items() if not ok]


class StackInstaller:
    """Instala stacks completos a través de un adaptador inyectado."""

    def __init__(self, package_manager=None):
        self.package_manager = package_manager

    def install_stack(self, role: str, package_manager=None,
                      confirm: bool = False) -> StackInstallResult:
        """Instala en lote todos los paquetes del stack `role`.

        Args:
            role: 'dev', 'terminal' o 'web'.
            package_manager: adaptador con ``install_package(name,
                confirm=False)``. Si se omite, se usa el del constructor.
            confirm: se reenvía a ``install_package``; por defecto False para
                que una instalación en lote no pida confirmaciones una a una.

        Returns:
            StackInstallResult: ``{paquete: bool}`` con un resultado por
            paquete. Un fallo (o excepción) no aborta el resto del lote.
        """
        manager = package_manager if package_manager is not None else self.package_manager
        if manager is None:
            raise ValueError(
                'Se requiere un package_manager con install_package()')

        if role not in STACKS:
            raise UnknownStackError(
                f"Stack desconocido {role!r}; roles disponibles: "
                f"{', '.join(STACKS)}")
        packages = get_stack(role)

        results: Dict[str, bool] = {}
        for package in packages:
            try:
                results[package] = bool(
                    manager.install_package(package, confirm=confirm))
            except Exception:
                # Un paquete problemático no debe detener el resto del stack.
                results[package] = False
        return StackInstallResult(role, results)

    def install_all(self, package_manager=None,
                    confirm: bool = False) -> Dict[str, StackInstallResult]:
        """Instala todos los roles y devuelve un resultado por rol."""
        return {
            role: self.install_stack(role, package_manager, confirm)
            for role in STACKS
        }


def fwupd_available() -> bool:
    """True si el gestor de firmware `fwupdmgr` está disponible en PATH.

    Sólo consulta el PATH con ``shutil.which``: **nunca ejecuta fwupdmgr**
    ni inicia actualizaciones de firmware.
    """
    return shutil.which(FWUPD_MANAGER) is not None
