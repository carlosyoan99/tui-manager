# Especificaciones Detalladas por Módulo

## 1. Módulo de Gestión de Paquetes

### 1.1 Descripción
Este módulo se encarga de la gestión de paquetes del sistema operativo, proporcionando una interfaz unificada para diferentes gestores de paquetes (apt, pacman, dnf, xbps, etc.).

### 1.2 Responsabilidades
- Detectar la distribución Linux del sistema
- Seleccionar el adaptador apropiado para la distribución
- Ejecutar comandos de gestión de paquetes
- Parsear y validar la salida de los comandos
- Manejar errores y excepciones
- Cachear resultados para mejorar el rendimiento

### 1.3 Interfaces Públicas

```python
class PackageManager:
    """Gestor principal de paquetes"""

    def __init__(self, distribution: str = None):
        """
        Inicializa el gestor de paquetes

        Args:
            distribution: Nombre de la distribución. Si es None, se detecta automáticamente
        """
        pass

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
        pass

    def search_package(self, query: str) -> List[Package]:
        """
        Busca paquetes por nombre o descripción

        Args:
            query: Término de búsqueda

        Returns:
            Lista de objetos Package encontrados
        """
        pass

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
        pass

    def install_package(self, package_name: str, confirm: bool = True) -> bool:
        """
        Instala un paquete

        Args:
            package_name: Nombre del paquete a instalar
            confirm: Si es True, requiere confirmación

        Returns:
            True si la instalación fue exitosa, False en caso contrario

        Raises:
            PackageNotFoundError: Si el paquete no existe
            InstallFailedError: Si la instalación falló
        """
        pass

    def remove_package(self, package_name: str, confirm: bool = True) -> bool:
        """
        Desinstala un paquete

        Args:
            package_name: Nombre del paquete a desinstalar
            confirm: Si es True, requiere confirmación

        Returns:
            True si la desinstalación fue exitosa, False en caso contrario

        Raises:
            PackageNotFoundError: Si el paquete no existe
            RemoveFailedError: Si la desinstalación falló
        """
        pass

    def update_package_cache(self) -> bool:
        """
        Actualiza la caché de paquetes

        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        pass

    def upgrade_system(self, package_names: List[str] = None) -> bool:
        """
        Actualiza el sistema completo o paquetes específicos

        Args:
            package_names: Lista de paquetes a actualizar. Si es None, actualiza todo

        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        pass

    def get_updates_available(self) -> List[Package]:
        """
        Obtiene la lista de paquetes que pueden ser actualizados

        Returns:
            Lista de objetos Package con versiones disponibles
        """
        pass

    def get_dependencies(self, package_name: str) -> List[str]:
        """
        Obtiene las dependencias de un paquete

        Args:
            package_name: Nombre del paquete

        Returns:
            Lista de nombres de dependencias
        """
        pass

    def get_recommends(self, package_name: str) -> List[str]:
        """
        Obtiene las recomendaciones de un paquete

        Args:
            package_name: Nombre del paquete

        Returns:
            Lista de nombres de recomendaciones
        """
        pass
```

### 1.4 Excepciones

```python
class PackageNotFoundError(Exception):
    """Paquete no encontrado"""

    def __init__(self, package_name: str):
        super().__init__(f"Paquete '{package_name}' no encontrado")
        self.package_name = package_name


class InstallFailedError(Exception):
    """Falló la instalación"""

    def __init__(self, package_name: str, error_message: str = ""):
        super().__init__(f"Falló la instalación de '{package_name}': {error_message}")
        self.package_name = package_name
        self.error_message = error_message


class RemoveFailedError(Exception):
    """Falló la desinstalación"""

    def __init__(self, package_name: str, error_message: str = ""):
        super().__init__(f"Falló la desinstalación de '{package_name}': {error_message}")
        self.package_name = package_name
        self.error_message = error_message


class CommandExecutionError(Exception):
    """Error al ejecutar un comando"""

    def __init__(self, command: List[str], returncode: int, stderr: str):
        super().__init__(f"Error al ejecutar comando '{' '.join(command)}'")
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
```

### 1.5 Datos Internos

```python
class Package:
    """Modelo de datos para paquetes"""

    # Categorías de paquetes
    CATEGORIES = {
        'development': 'Desarrollo',
        'system': 'Sistema',
        'multimedia': 'Multimedia',
        'network': 'Red',
        'games': 'Juegos',
        'office': 'Oficina',
        'utilities': 'Utilidades',
        'security': 'Seguridad',
        'database': 'Base de datos',
        'other': 'Otros'
    }

    def __init__(
        self,
        name: str,
        version: str = None,
        description: str = "",
        installed: bool = False,
        size: str = "",
        dependencies: List[str] = None,
        recommends: List[str] = None,
        category: str = "other"
    ):
        self.name = name
        self.version = version
        self.description = description
        self.installed = installed
        self.size = size
        self.dependencies = dependencies or []
        self.recommends = recommends or []
        self.category = category

    def get_category_name(self) -> str:
        """Obtiene el nombre de la categoría en español"""
        return self.CATEGORIES.get(self.category, self.category)

    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'installed': self.installed,
            'size': self.size,
            'dependencies': self.dependencies,
            'recommends': self.recommends,
            'category': self.category
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Package':
        """Crea instancia desde diccionario"""
        return cls(
            name=data['name'],
            version=data.get('version'),
            description=data.get('description', ''),
            installed=data.get('installed', False),
            size=data.get('size', ''),
            dependencies=data.get('dependencies', []),
            recommends=data.get('recommends', []),
            category=data.get('category', 'other')
        )
```

### 1.6 Implementación del Adaptador

```python
class PackageAdapter:
    """Clase base para adaptadores de paquetes"""

    def get_installed_packages(self) -> List[Package]:
        """Deben implementar este método"""
        raise NotImplementedError

    def get_package_info(self, package_name: str) -> Package:
        """Deben implementar este método"""
        raise NotImplementedError

    def install_package(self, package_name: str) -> bool:
        """Deben implementar este método"""
        raise NotImplementedError

    def remove_package(self, package_name: str) -> bool:
        """Deben implementar este método"""
        raise NotImplementedError

    def search_packages(self, query: str) -> List[Package]:
        """Deben implementar este método"""
        raise NotImplementedError

    def update_cache(self) -> bool:
        """Deben implementar este método"""
        raise NotImplementedError
```

## 2. Módulo de Monitoreo de Procesos

### 2.1 Descripción
Este módulo monitorea los procesos en tiempo real, proporcionando información detallada sobre su uso de recursos y permitiendo acciones sobre ellos.

### 2.2 Responsabilidades
- Obtener lista de procesos del sistema
- Parsear la salida del comando `ps`
- Filtrar procesos según criterios específicos
- Enviar señales a procesos
- Calcular métricas de uso de recursos
- Actualizar en tiempo real

### 2.3 Interfaces Públicas

```python
class ProcessMonitor:
    """Monitor de procesos"""

    def __init__(self, refresh_interval: int = 2):
        """
        Inicializa el monitor de procesos

        Args:
            refresh_interval: Intervalo de actualización en segundos
        """
        pass

    def get_processes(self, filters: dict = None) -> List[Process]:
        """
        Obtiene la lista de procesos

        Args:
            filters: Diccionario con filtros opcionales:
                     - user: Filtrar por usuario
                     - name: Filtrar por nombre de comando
                     - min_cpu: CPU mínimo (porcentaje)
                     - max_cpu: CPU máximo (porcentaje)
                     - min_mem: Memoria mínima (MB)
                     - max_mem: Memoria máxima (MB)
                     - pid: Filtrar por PID

        Returns:
            Lista de objetos Process
        """
        pass

    def get_process_by_pid(self, pid: int) -> Process:
        """
        Obtiene información de un proceso específico

        Args:
            pid: ID del proceso

        Returns:
            Objeto Process con información del proceso

        Raises:
            ProcessNotFoundError: Si el proceso no existe
        """
        pass

    def kill_process(self, pid: int, signal: int = 15) -> bool:
        """
        Termina un proceso

        Args:
            pid: ID del proceso
            signal: Señal a enviar (15=SIGTERM, 9=SIGKILL)

        Returns:
            True si el proceso fue terminado, False en caso contrario
        """
        pass

    def renice_process(self, pid: int, nice: int) -> bool:
        """
        Cambia la prioridad de un proceso

        Args:
            pid: ID del proceso
            nice: Valor de prioridad (-20 a 19)

        Returns:
            True si la prioridad fue cambiada, False en caso contrario
        """
        pass

    def get_total_cpu_usage(self) -> float:
        """
        Obtiene el uso total de CPU del sistema

        Returns:
            Porcentaje de CPU usado
        """
        pass

    def get_total_memory_usage(self) -> dict:
        """
        Obtiene el uso total de memoria del sistema

        Returns:
            Diccionario con:
            - total: Memoria total (MB)
            - used: Memoria usada (MB)
            - free: Memoria libre (MB)
            - available: Memoria disponible (MB)
            - percentage: Porcentaje usado
        """
        pass

    def get_top_processes(self, count: int = 10, by: str = 'cpu') -> List[Process]:
        """
        Obtiene los procesos más consumidoros

        Args:
            count: Número de procesos a retornar
            by: 'cpu' o 'mem' para ordenar por CPU o memoria

        Returns:
            Lista de procesos ordenados
        """
        pass

    def start_monitoring(self, callback: Callable):
        """
        Inicia el monitoreo en tiempo real

        Args:
            callback: Función a llamar cuando hay actualizaciones
        """
        pass

    def stop_monitoring(self):
        """Detiene el monitoreo en tiempo real"""
        pass
```

### 2.4 Excepciones

```python
class ProcessNotFoundError(Exception):
    """Proceso no encontrado"""

    def __init__(self, pid: int):
        super().__init__(f"Proceso con PID {pid} no encontrado")
        self.pid = pid


class SignalError(Exception):
    """Error al enviar señal"""

    def __init__(self, pid: int, signal: int, error: str):
        super().__init__(f"Error al enviar señal {signal} al proceso {pid}: {error}")
        self.pid = pid
        self.signal = signal
        self.error = error
```

### 2.5 Modelo de Proceso

```python
class Process:
    """Modelo de datos para procesos"""

    def __init__(
        self,
        pid: int,
        user: str,
        cpu: float,
        mem: float,
        vsz: int,
        rss: int,
        nice: int,
        start: str,
        time: str,
        command: str
    ):
        self.pid = pid
        self.user = user
        self.cpu = cpu
        self.mem = mem
        self.vsz = vsz  # Virtual memory size (KB)
        self.rss = rss  # Resident set size (KB)
        self.nice = nice
        self.start = start
        self.time = time
        self.command = command

    def get_memory_usage_mb(self) -> float:
        """Retorna uso de memoria en MB"""
        return self.rss / 1024

    def get_virtual_memory_mb(self) -> float:
        """Retorna memoria virtual en MB"""
        return self.vsz / 1024

    def get_memory_percentage(self, total_memory_mb: float) -> float:
        """Retorna porcentaje de memoria del sistema"""
        return (self.rss / (total_memory_mb * 1024)) * 100

    def get_status(self) -> str:
        """Obtiene el estado del proceso (usando /proc)"""
        try:
            with open(f'/proc/{self.pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('State:'):
                        return line.split(':')[1].strip()
        except FileNotFoundError:
            return 'unknown'
        return 'unknown'

    def get_ppid(self) -> int:
        """Obtiene el PID del proceso padre"""
        try:
            with open(f'/proc/{self.pid}/stat', 'r') as f:
                parts = f.read().split()
                return int(parts[3])
        except FileNotFoundError:
            return 0

    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'pid': self.pid,
            'user': self.user,
            'cpu': self.cpu,
            'mem': self.mem,
            'vsz': self.vsz,
            'rss': self.rss,
            'nice': self.nice,
            'start': self.start,
            'time': self.time,
            'command': self.command
        }
```

## 3. Módulo de Interfaz de Usuario

### 3.1 Descripción
Este módulo proporciona la interfaz de usuario TUI, utilizando textual para crear una experiencia de usuario intuitiva y moderna.

### 3.2 Responsabilidades
- Crear y gestionar las pantallas TUI
- Manejar eventos de teclado
- Mostrar información de forma clara
- Proporcionar navegación intuitiva
- Implementar temas y estilos

### 3.3 Estructura de Pantallas

```python
class Screen:
    """Clase base para todas las pantallas"""

    def show(self):
        """Muestra la pantalla"""
        pass

    def hide(self):
        """Oculta la pantalla"""
        pass

    def handle_input(self, key):
        """Maneja entrada del usuario"""
        pass

    def refresh(self):
        """Actualiza el contenido de la pantalla"""
        pass


class MainMenuScreen(Screen):
    """Pantalla de menú principal"""

    def __init__(self):
        super().__init__()
        self.menu_items = [
            ("Gestión de Paquetes", "package_manager"),
            ("Monitoreo de Procesos", "process_monitor"),
            ("Configuración", "settings"),
            ("Acerca de", "about"),
            ("Ayuda", "help"),
            ("Salir", "quit")
        ]

    def show(self):
        """Muestra el menú principal"""
        # Implementación con textual

    def handle_input(self, key):
        """Maneja entrada del usuario"""
        if key in ('up', 'down'):
            # Navegar hacia arriba/abajo
        elif key == 'enter':
            # Seleccionar opción
        elif key == 'q':
            # Salir
        elif key == '?':
            # Mostrar ayuda


class PackageManagerScreen(Screen):
    """Pantalla de gestión de paquetes"""

    def __init__(self, package_manager: PackageManager):
        super().__init__()
        self.package_manager = package_manager
        self.packages = []
        self.filter_text = ""

    def show(self):
        """Muestra la pantalla de gestión de paquetes"""
        # Implementación con textual

    def refresh(self):
        """Actualiza la lista de paquetes"""
        if self.filter_text:
            self.packages = self.package_manager.search_package(self.filter_text)
        else:
            self.packages = self.package_manager.get_installed_packages()

    def handle_input(self, key):
        """Maneja entrada del usuario"""
        if key == 'enter':
            # Seleccionar paquete
        elif key == 'q':
            # Salir
        elif key == 's':
            # Cambiar tema
        elif key == 'r':
            # Refrescar
```

### 3.4 Gestor de Pantallas

```python
class ScreenManager:
    """Gestor de pantallas"""

    def __init__(self):
        self.screens = {}
        self.current_screen = None

    def add_screen(self, name: str, screen: Screen):
        """Agrega una pantalla"""
        self.screens[name] = screen

    def show_screen(self, name: str):
        """Muestra una pantalla"""
        if name in self.screens:
            self.screens[name].show()
            self.current_screen = name

    def handle_input(self, key):
        """Maneja entrada del usuario en la pantalla actual"""
        if self.current_screen:
            self.screens[self.current_screen].handle_input(key)

    def refresh_current_screen(self):
        """Refresca la pantalla actual"""
        if self.current_screen:
            self.screens[self.current_screen].refresh()
```

## 4. Módulo de Detección de Distribución

### 4.1 Descripción
Este módulo detecta la distribución Linux del sistema y selecciona el adaptador de paquetes apropiado.

### 4.2 Responsabilidades
- Detectar la distribución Linux
- Detectar la versión de la distribución
- Detectar el gestor de paquetes
- Proporcionar información de la distribución

### 4.3 Interfaces Públicas

```python
class DistributionDetector:
    """Detector de distribución Linux"""

    @staticmethod
    def detect() -> str:
        """
        Detecta la distribución del sistema

        Returns:
            Nombre de la distribución (debian, arch, fedora, void, etc.)
        """
        pass

    @staticmethod
    def get_distro_name() -> str:
        """
        Obtiene el nombre completo de la distribución

        Returns:
            Nombre de la distribución
        """
        pass

    @staticmethod
    def get_distro_version() -> str:
        """
        Obtiene la versión de la distribución

        Returns:
            Versión de la distribución
        """
        pass

    @staticmethod
    def get_package_manager() -> str:
        """
        Obtiene el gestor de paquetes por defecto

        Returns:
            Nombre del gestor de paquetes
        """
        pass

    @staticmethod
    def is_supported() -> bool:
        """
        Verifica si la distribución es soportada

        Returns:
            True si la distribución es soportada
        """
        pass

    @staticmethod
    def get_supported_distributions() -> List[str]:
        """
        Obtiene lista de distribuciones soportadas

        Returns:
            Lista de nombres de distribuciones soportadas
        """
        pass
```

## 5. Módulo de Gestión de Temas

### 5.1 Descripción
Este módulo gestiona los temas visuales de la aplicación TUI.

### 5.2 Responsabilidades
- Definir temas disponibles
- Aplicar temas a la interfaz
- Guardar y cargar configuración de temas
- Proporcionar herramientas para crear nuevos temas

### 5.3 Interfaces Públicas

```python
class ThemeManager:
    """Gestor de temas"""

    DEFAULT_THEME = 'dark'

    THEMES = {
        'dark': {
            'primary': 'dark blue',
            'secondary': 'dark cyan',
            'success': 'dark green',
            'warning': 'dark yellow',
            'error': 'dark red',
            'background': 'black',
            'foreground': 'light gray',
            'highlight': 'dark blue',
            'selected': 'dark blue bold'
        },
        'light': {
            'primary': 'blue',
            'secondary': 'cyan',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
            'background': 'white',
            'foreground': 'black',
            'highlight': 'blue',
            'selected': 'blue bold'
        },
        'retro': {
            'primary': 'brown',
            'secondary': 'dark green',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
            'background': 'black',
            'foreground': 'light gray',
            'highlight': 'brown',
            'selected': 'brown bold'
        }
    }

    def __init__(self, theme_name: str = None):
        """
        Inicializa el gestor de temas

        Args:
            theme_name: Nombre del tema a usar
        """
        pass

    def get_current_theme(self) -> str:
        """
        Obtiene el nombre del tema actual

        Returns:
            Nombre del tema
        """
        pass

    def set_theme(self, theme_name: str):
        """
        Cambia el tema actual

        Args:
            theme_name: Nombre del nuevo tema
        """
        pass

    def get_colors(self) -> dict:
        """
        Obtiene los colores del tema actual

        Returns:
            Diccionario con los colores
        """
        pass

    def get_color(self, name: str) -> tuple:
        """
        Obtiene un color específico del tema

        Args:
            name: Nombre del color

        Returns:
            Tupla (foreground, background)
        """
        pass

    def list_themes(self) -> List[str]:
        """
        Lista todos los temas disponibles

        Returns:
            Lista de nombres de temas
        """
        pass

    def is_theme_available(self, theme_name: str) -> bool:
        """
        Verifica si un tema está disponible

        Args:
            theme_name: Nombre del tema

        Returns:
            True si el tema está disponible
        """
        pass
```

## 6. Módulo de Configuración

### 6.1 Descripción
Este módulo gestiona la configuración de la aplicación.

### 6.2 Responsabilidades
- Cargar configuración desde archivo
- Guardar configuración en archivo
- Proporcionar acceso a valores de configuración
- Validar configuración

### 6.3 Interfaces Públicas

```python
class Config:
    """Gestor de configuración"""

    DEFAULT_CONFIG = {
        'theme': 'dark',
        'auto_update': True,
        'refresh_interval': 2,
        'show_details': True,
        'sort_by': 'name',
        'sort_order': 'asc',
        'default_category': 'all',
        'show_notifications': True,
        'log_level': 'info'
    }

    def __init__(self, config_file: str = None):
        """
        Inicializa el gestor de configuración

        Args:
            config_file: Ruta del archivo de configuración
        """
        pass

    def get(self, key: str, default=None):
        """
        Obtiene un valor de configuración

        Args:
            key: Clave de configuración
            default: Valor por defecto si la clave no existe

        Returns:
            Valor de configuración
        """
        pass

    def set(self, key: str, value):
        """
        Establece un valor de configuración

        Args:
            key: Clave de configuración
            value: Valor a establecer
        """
        pass

    def get_all(self) -> dict:
        """
        Obtiene todos los valores de configuración

        Returns:
            Diccionario con toda la configuración
        """
        pass

    def set_all(self, config_dict: dict):
        """
        Establece todos los valores de configuración

        Args:
            config_dict: Diccionario con la nueva configuración
        """
        pass

    def reset_to_default(self):
        """Restaura la configuración a los valores por defecto"""
        pass

    def save(self):
        """Guarda la configuración en archivo"""
        pass

    def load(self):
        """Carga la configuración desde archivo"""
        pass
```
