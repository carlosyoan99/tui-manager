"""
Gestor principal de paquetes
"""

import logging
from typing import List, Optional
from .package_adapter import PackageAdapter, Package, PackageNotFoundError
from .debian_adapter import DebianAdapter
from .arch_adapter import ArchAdapter
from .fedora_adapter import FedoraAdapter
from .void_adapter import VoidAdapter
from .termux_adapter import TermuxAdapter
from .freebsd_adapter import FreeBSDAdapter
from .pkgsrc_adapter import PkgsrcAdapter

logger = logging.getLogger(__name__)


class PackageManager:
    """Gestor principal de paquetes"""

    def __init__(self, distribution: str = None):
        """
        Inicializa el gestor de paquetes

        Args:
            distribution: Nombre de la distribución. Si es None, se detecta automáticamente
        """
        self.distribution = distribution or self._detect_distribution()
        self.adapter = self._get_adapter()
        logger.info(f"PackageManager inicializado para distribución: {self.distribution}")

    def _detect_distribution(self) -> str:
        """Detecta la distribución del sistema"""
        from .distribution import DistributionDetector
        return DistributionDetector.detect()

    def _get_adapter(self) -> PackageAdapter:
        """Selecciona el adaptador apropiado para la distribución"""
        adapters = {
            'debian': DebianAdapter,
            'ubuntu': DebianAdapter,
            'linuxmint': DebianAdapter,
            'kali': DebianAdapter,
            'mx': DebianAdapter,
            'arch': ArchAdapter,
            'manjaro': ArchAdapter,
            'endeavouros': ArchAdapter,
            'garuda': ArchAdapter,
            'artix': ArchAdapter,
            'fedora': FedoraAdapter,
            'rhel': FedoraAdapter,
            'centos': FedoraAdapter,
            'rocky': FedoraAdapter,
            'almalinux': FedoraAdapter,
            'void': VoidAdapter,
            'termux': TermuxAdapter,
            'freebsd': FreeBSDAdapter,
            'dragonfly': FreeBSDAdapter,
            'netbsd': PkgsrcAdapter,
            'openbsd': PkgsrcAdapter,
        }

        adapter_class = adapters.get(self.distribution.lower())
        if adapter_class:
            logger.info(f"Usando adaptador: {adapter_class.__name__}")
            return adapter_class()

        # Fallback: usar DebianAdapter
        logger.warning(f"Distribución no soportada, usando DebianAdapter")
        return DebianAdapter()

    def get_installed_packages(self, filters: dict = None) -> List[Package]:
        """
        Obtiene la lista de paquetes instalados

        Args:
            filters: Diccionario con filtros opcionales:
                     - category: Filtrar por categoría
                     - name: Filtrar por nombre
                     - installed: Solo paquetes instalados

        Returns:
            Lista de objetos Package
        """
        packages = self.adapter.get_installed_packages()

        if filters:
            if 'category' in filters and filters['category']:
                packages = [p for p in packages if p.category == filters['category']]

            if 'name' in filters and filters['name']:
                packages = [p for p in packages if filters['name'].lower() in p.name.lower()]

            if 'installed' in filters and filters['installed'] is not None:
                packages = [p for p in packages if p.installed == filters['installed']]

        logger.debug(f"Retornando {len(packages)} paquetes")
        return packages

    def search_package(self, query: str) -> List[Package]:
        """
        Busca paquetes por nombre o descripción

        Args:
            query: Término de búsqueda

        Returns:
            Lista de objetos Package encontrados
        """
        packages = self.adapter.search_packages(query)
        logger.debug(f"Retornando {len(packages)} paquetes encontrados para '{query}'")
        return packages

    def get_package_info(self, package_name: str) -> Package:
        """
        Obtiene información detallada de un paquete

        Args:
            package_name: Nombre del paquete

        Returns:
            Objeto Package con información completa

        Raises:
            PackageNotFoundError: Si el paquete no existe
        """
        return self.adapter.get_package_info(package_name)

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        """
        Instala un paquete

        Args:
            package_name: Nombre del paquete a instalar
            confirm: Si es True, requiere confirmación

        Returns:
            True si la instalación fue exitosa, False en caso contrario
        """
        try:
            return self.adapter.install_package(package_name, confirm)
        except PackageNotFoundError as e:
            logger.error(f"Paquete no encontrado: {e}")
            print(f"\n❌ Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error al instalar {package_name}: {e}")
            print(f"\n❌ Error al instalar: {e}")
            return False

    def remove_package(self, package_name: str, confirm: bool = True) -> bool:
        """
        Desinstala un paquete

        Args:
            package_name: Nombre del paquete a desinstalar
            confirm: Si es True, requiere confirmación

        Returns:
            True si la desinstalación fue exitosa, False en caso contrario
        """
        try:
            return self.adapter.remove_package(package_name, confirm)
        except PackageNotFoundError as e:
            logger.error(f"Paquete no encontrado: {e}")
            print(f"\n❌ Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error al desinstalar {package_name}: {e}")
            print(f"\n❌ Error al desinstalar: {e}")
            return False

    def update_package_cache(self) -> bool:
        """
        Actualiza la caché de paquetes

        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        try:
            return self.adapter.update_cache()
        except Exception as e:
            logger.error(f"Error al actualizar caché: {e}")
            print(f"\n❌ Error al actualizar caché: {e}")
            return False

    def upgrade_system(self, package_names: List[str] = None) -> bool:
        """
        Actualiza el sistema completo o paquetes específicos

        Args:
            package_names: Lista de paquetes a actualizar. Si es None, actualiza todo

        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        try:
            if package_names:
                # Actualizar paquetes específicos
                print(f"\nActualizando {len(package_names)} paquetes...")
                for package_name in package_names:
                    print(f"  - {package_name}")
                    if not self.adapter.install_package(package_name, confirm=False):
                        print(f"    ❌ Falló: {package_name}")
                        return False
                print("✅ Actualización completada")
                return True
            else:
                # Actualizar todo el sistema
                print("\nActualizando sistema completo...")
                return self.adapter.update_cache()
        except Exception as e:
            logger.error(f"Error al actualizar sistema: {e}")
            print(f"\n❌ Error al actualizar sistema: {e}")
            return False

    def get_updates_available(self) -> List[Package]:
        """
        Obtiene la lista de paquetes que pueden ser actualizados

        Returns:
            Lista de objetos Package con versiones disponibles
        """
        try:
            return self.adapter.get_updates_available()
        except Exception as e:
            logger.error(f"Error al obtener actualizaciones: {e}")
            return []

    def get_dependencies(self, package_name: str) -> List[str]:
        """
        Obtiene las dependencias de un paquete

        Args:
            package_name: Nombre del paquete

        Returns:
            Lista de nombres de dependencias
        """
        try:
            return self.adapter.get_dependencies(package_name)
        except PackageNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error al obtener dependencias: {e}")
            return []

    def get_recommends(self, package_name: str) -> List[str]:
        """
        Obtiene las recomendaciones de un paquete

        Args:
            package_name: Nombre del paquete

        Returns:
            Lista de nombres de recomendaciones
        """
        try:
            package = self.get_package_info(package_name)
            return package.recommends
        except PackageNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error al obtener recomendaciones: {e}")
            return []
