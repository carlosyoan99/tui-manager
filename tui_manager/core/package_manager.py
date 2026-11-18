"""
Gestor principal de paquetes
"""

import logging
from typing import List, Optional
from .audit import AuditLog
from .package_adapter import PackageAdapter, Package, PackageNotFoundError
from .debian_adapter import DebianAdapter
from .arch_adapter import ArchAdapter
from .fedora_adapter import FedoraAdapter
from .void_adapter import VoidAdapter
from .termux_adapter import TermuxAdapter
from .freebsd_adapter import FreeBSDAdapter
from .pkgsrc_adapter import PkgsrcAdapter
from .perf import PackageCache, paginate

logger = logging.getLogger(__name__)


class PackageManager:
    """Gestor principal de paquetes"""

    def __init__(self, distribution: str = None,
                 audit_log: Optional[AuditLog] = None):
        """
        Inicializa el gestor de paquetes

        Args:
            distribution: Nombre de la distribución. Si es None, se detecta automáticamente
            audit_log: Registro de auditoría opcional. Si es None no se registran
                       acciones (comportamiento por defecto sin cambios).
        """
        self.distribution = distribution or self._detect_distribution()
        self.adapter = self._get_adapter()
        self.audit_log = audit_log
        self._package_cache = PackageCache()
        logger.info(f"PackageManager inicializado para distribución: {self.distribution}")

    def _audit(self, action: str, target: str, result: bool) -> None:
        """Registra una acción destructiva si se inyectó un AuditLog."""
        if self.audit_log is not None:
            self.audit_log.record(action, target, result)

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
            'cachyos': ArchAdapter,
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

    def get_installed_packages(self, filters: dict = None,
                               use_cache: bool = False,
                               offset: int = 0,
                               limit: Optional[int] = None) -> List[Package]:
        """
        Obtiene la lista de paquetes instalados

        Args:
            filters: Diccionario con filtros opcionales:
                     - category: Filtrar por categoría
                     - name: Filtrar por nombre
                     - installed: Solo paquetes instalados
            use_cache: Si es True, reutiliza el listado del adapter cacheado.
                       Por defecto False para no cambiar el comportamiento
                       existente (ni romper tests).
            offset: Fila inicial de la ventana paginada (0 por defecto).
            limit: Número máximo de filas de la ventana (None = todas).

        Returns:
            Lista de objetos Package
        """
        if use_cache:
            packages = self._package_cache.get(
                'installed', self.adapter.get_installed_packages)
        else:
            packages = self.adapter.get_installed_packages()

        if filters:
            if 'category' in filters and filters['category']:
                packages = [p for p in packages if p.category == filters['category']]

            if 'name' in filters and filters['name']:
                packages = [p for p in packages if filters['name'].lower() in p.name.lower()]

            if 'installed' in filters and filters['installed'] is not None:
                packages = [p for p in packages if p.installed == filters['installed']]

        # `paginate` devuelve una copia, de modo que el listado cacheado
        # nunca se expone a mutaciones del llamador.
        packages = paginate(packages, offset, limit)

        logger.debug(f"Retornando {len(packages)} paquetes")
        return packages

    def invalidate_cache(self) -> None:
        """Invalida la caché de listados de paquetes."""
        self._package_cache.invalidate()

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
        success = False
        try:
            success = bool(self.adapter.install_package(package_name, confirm))
            return success
        except PackageNotFoundError as e:
            logger.error(f"Paquete no encontrado: {e}")
            print(f"\n❌ Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error al instalar {package_name}: {e}")
            print(f"\n❌ Error al instalar: {e}")
            return False
        finally:
            self._audit('install_package', package_name, success)
            self.invalidate_cache()

    def remove_package(self, package_name: str, confirm: bool = True) -> bool:
        """
        Desinstala un paquete

        Args:
            package_name: Nombre del paquete a desinstalar
            confirm: Si es True, requiere confirmación

        Returns:
            True si la desinstalación fue exitosa, False en caso contrario
        """
        success = False
        try:
            success = bool(self.adapter.remove_package(package_name, confirm))
            return success
        except PackageNotFoundError as e:
            logger.error(f"Paquete no encontrado: {e}")
            print(f"\n❌ Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error al desinstalar {package_name}: {e}")
            print(f"\n❌ Error al desinstalar: {e}")
            return False
        finally:
            self._audit('remove_package', package_name, success)
            self.invalidate_cache()

    def update_package_cache(self) -> bool:
        """
        Actualiza la caché de paquetes

        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        try:
            result = self.adapter.update_cache()
            self.invalidate_cache()
            return result
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

    def get_orphans(self) -> List[Package]:
        """Huérfanos según el adapter de la distribución."""
        try:
            return self.adapter.get_orphans()
        except Exception as e:
            logger.error(f"Error al obtener huérfanos: {e}")
            return []

    def clean_orphans(self, confirm: bool = True) -> bool:
        """Limpia huérfanos según el adapter de la distribución."""
        success = False
        try:
            success = bool(self.adapter.clean_orphans(confirm=confirm))
            return success
        except Exception as e:
            logger.error(f"Error al limpiar huérfanos: {e}")
            return False
        finally:
            self._audit('clean_orphans', self.distribution, success)
