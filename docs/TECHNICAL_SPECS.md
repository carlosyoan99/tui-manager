# Especificaciones Técnicas Detalladas

## 1. Arquitectura del Sistema

### 1.1 Patrones de Diseño

#### Patrón MVC (Model-View-Controller)
- **Modelo**: Datos de paquetes y procesos
- **Vista**: Interfaz TUI con textual
- **Controlador**: Lógica de negocio y gestión de comandos

#### Patrón Adapter
- Wrapper para cada gestor de paquetes (apt, pacman, dnf, xbps, etc.)
- Abstracción de comandos nativos

#### Patrón Strategy
- Estrategias de monitoreo de procesos
- Estrategias de búsqueda de paquetes

### 1.2 Flujo de Datos

```
Usuario → Interfaz TUI → Controlador → Modelo → Adapter → Sistema Operativo
                      ↑                                        ↓
                      └─────────────── Datos del Sistema ←──────┘
```

## 2. Gestión de Paquetes

### 2.1 Arquitectura del Módulo

```python
class PackageManager:
    def __init__(self, distribution: str):
        self.distribution = distribution
        self.adapter = self._get_adapter()

    def _get_adapter(self) -> PackageAdapter:
        """Selecciona el adaptador según la distribución"""
        adapters = {
            'debian': DebianAdapter,
            'ubuntu': DebianAdapter,
            'arch': ArchAdapter,
            'fedora': FedoraAdapter,
            'void': VoidAdapter,
            # ... más distribuciones
        }
        return adapters.get(self.distribution.lower(), GenericAdapter)

    def get_installed_packages(self) -> List[Package]:
        """Retorna lista de paquetes instalados"""

    def search_package(self, query: str) -> List[Package]:
        """Busca paquetes por nombre o descripción"""

    def install_package(self, package: str) -> bool:
        """Instala un paquete"""

    def remove_package(self, package: str) -> bool:
        """Desinstala un paquete"""

    def update_package_cache(self) -> bool:
        """Actualiza la caché de paquetes"""

    def upgrade_system(self) -> bool:
        """Actualiza todo el sistema"""
```

### 2.2 Implementación por Distribución

#### Debian/Ubuntu
```python
class DebianAdapter(PackageAdapter):
    """Gestor para Debian y Ubuntu usando apt"""

    def get_installed_packages(self):
        cmd = ['apt', 'list', '--installed']
        result = subprocess.run(cmd, capture_output=True, text=True)

        packages = []
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if line.strip():
                # Formato: package/version/arch
                parts = line.split('/')
                if len(parts) >= 2:
                    package = Package(
                        name=parts[0],
                        version=parts[1].split('[')[0],
                        description=self._get_description(parts[0]),
                        installed=True
                    )
                    packages.append(package)
        return packages

    def install_package(self, package: str) -> bool:
        cmd = ['sudo', 'apt', 'install', '-y', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def remove_package(self, package: str) -> bool:
        cmd = ['sudo', 'apt', 'remove', '-y', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
```

#### Arch Linux
```python
class ArchAdapter(PackageAdapter):
    """Gestor para Arch Linux usando pacman"""

    def get_installed_packages(self):
        cmd = ['pacman', '-Q', '--info']
        result = subprocess.run(cmd, capture_output=True, text=True)

        packages = []
        current_package = None

        for line in result.stdout.split('\n'):
            if line.startswith('Package '):
                if current_package:
                    packages.append(current_package)
                current_package = Package(name=line.split()[1])
            elif current_package and line.startswith('Version '):
                current_package.version = line.split()[1]
            # ... más campos

        if current_package:
            packages.append(current_package)

        return packages

    def install_package(self, package: str) -> bool:
        cmd = ['sudo', 'pacman', '-S', '--noconfirm', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def remove_package(self, package: str) -> bool:
        cmd = ['sudo', 'pacman', '-R', '--noconfirm', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
```

#### Fedora
```python
class FedoraAdapter(PackageAdapter):
    """Gestor para Fedora usando dnf"""

    def get_installed_packages(self):
        cmd = ['dnf', 'list', 'installed']
        result = subprocess.run(cmd, capture_output=True, text=True)

        packages = []
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if line.strip():
                # Formato: package.version.arch
                parts = line.split('.')
                if len(parts) >= 2:
                    name = parts[0]
                    version = parts[1].split('[')[0]
                    package = Package(name=name, version=version)
                    packages.append(package)
        return packages

    def install_package(self, package: str) -> bool:
        cmd = ['sudo', 'dnf', 'install', '-y', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def remove_package(self, package: str) -> bool:
        cmd = ['sudo', 'dnf', 'remove', '-y', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
```

#### Void Linux
```python
class VoidAdapter(PackageAdapter):
    """Gestor para Void Linux usando xbps"""

    def get_installed_packages(self):
        cmd = ['xbps-query', '-l']
        result = subprocess.run(cmd, capture_output=True, text=True)

        packages = []
        for line in result.stdout.split('\n'):
            if line.strip():
                # Formato: l package.version
                parts = line.split()
                if len(parts) >= 2:
                    package = Package(
                        name=parts[1].split(':')[0],
                        version=parts[1].split(':')[1].split('-')[0]
                    )
                    packages.append(package)
        return packages

    def install_package(self, package: str) -> bool:
        cmd = ['sudo', 'xbps-install', '-y', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def remove_package(self, package: str) -> bool:
        cmd = ['sudo', 'xbps-remove', '-y', package]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
```

### 2.3 Modelo de Paquete

```python
class Package:
    """Modelo de datos para paquetes"""

    def __init__(
        self,
        name: str,
        version: str = None,
        description: str = "",
        installed: bool = False,
        size: str = "",
        dependencies: List[str] = None,
        category: str = "general"
    ):
        self.name = name
        self.version = version
        self.description = description
        self.installed = installed
        self.size = size
        self.dependencies = dependencies or []
        self.category = category

    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'installed': self.installed,
            'size': self.size,
            'dependencies': self.dependencies,
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
            category=data.get('category', 'general')
        )
```

## 3. Monitoreo de Procesos

### 3.1 Arquitectura del Módulo

```python
class ProcessMonitor:
    """Monitor de procesos en tiempo real"""

    def __init__(self):
        self.processes = []
        self.refresh_interval = 2  # segundos

    def get_processes(self, filters: dict = None) -> List[Process]:
        """Retorna lista de procesos con filtros opcionales"""
        cmd = ['ps', 'aux']
        result = subprocess.run(cmd, capture_output=True, text=True)

        processes = []
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if line.strip():
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    process = Process(
                        pid=int(parts[1]),
                        user=parts[0],
                        cpu=float(parts[2]),
                        mem=float(parts[3]),
                        vsz=int(parts[4]),
                        rss=int(parts[5]),
                        nice=int(parts[6]),
                        start=parts[7],
                        time=parts[8],
                        command=' '.join(parts[9:])
                    )
                    processes.append(process)

        # Aplicar filtros
        if filters:
            processes = self._apply_filters(processes, filters)

        return processes

    def kill_process(self, pid: int, signal: int = 15) -> bool:
        """Envía señal a un proceso"""
        cmd = ['kill', '-s', str(signal), str(pid)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def renice_process(self, pid: int, nice: int) -> bool:
        """Cambia la prioridad de un proceso"""
        cmd = ['renice', str(nice), '-p', str(pid)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def _apply_filters(self, processes: List[Process], filters: dict) -> List[Process]:
        """Aplica filtros a la lista de procesos"""
        filtered = processes

        if 'user' in filters and filters['user']:
            filtered = [p for p in filtered if p.user == filters['user']]

        if 'name' in filters and filters['name']:
            filtered = [p for p in filtered if filters['name'].lower() in p.command.lower()]

        if 'min_cpu' in filters and filters['min_cpu']:
            filtered = [p for p in filtered if p.cpu >= filters['min_cpu']]

        if 'max_cpu' in filters and filters['max_cpu']:
            filtered = [p for p in filtered if p.cpu <= filters['max_cpu']]

        return filtered
```

### 3.2 Modelo de Proceso

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

    def get_memory_percentage(self) -> float:
        """Retorna porcentaje de memoria del sistema"""
        # Necesita acceso al total de memoria del sistema
        total_mem = self._get_total_memory()
        return (self.rss / total_mem) * 100

    @staticmethod
    def _get_total_memory() -> int:
        """Obtiene la memoria total del sistema"""
        cmd = ['cat', '/proc/meminfo']
        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in result.stdout.split('\n'):
            if line.startswith('MemTotal:'):
                parts = line.split()
                return int(parts[1])

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

## 4. Interfaz de Usuario

### 4.1 Estructura de Pantallas

```python
class ScreenManager:
    """Gestor de pantallas TUI"""

    def __init__(self):
        self.screens = {
            'main': MainMenuScreen(),
            'package_manager': PackageManagerScreen(),
            'package_details': PackageDetailsScreen(),
            'process_monitor': ProcessMonitorScreen(),
            'settings': SettingsScreen(),
            'help': HelpScreen()
        }
        self.current_screen = 'main'

    def show_screen(self, screen_name: str):
        """Muestra una pantalla específica"""
        if screen_name in self.screens:
            self.current_screen = screen_name
            self.screens[screen_name].show()

    def navigate(self, direction: str):
        """Navega entre pantallas"""
        if direction == 'up':
            self._navigate_up()
        elif direction == 'down':
            self._navigate_down()

    def _navigate_up(self):
        """Navega a la pantalla anterior"""
        # Lógica de navegación

    def _navigate_down(self):
        """Navega a la siguiente pantalla"""
        # Lógica de navegación
```

### 4.2 Pantalla de Gestión de Paquetes

```python
class PackageManagerScreen(Screen):
    """Pantalla principal de gestión de paquetes"""

    def __init__(self):
        super().__init__()
        self.package_manager = PackageManager(detect_distribution())
        self.packages = []
        self.selected_package = None
        self.filter_text = ""

        # Widgets
        self.header = Header("📦 Gestión de Paquetes")
        self.search_box = Text("Buscar: ", edit_text="")
        self.filter_buttons = ButtonGroup([
            ("[I]nstalados", "installed"),
            ("[D]isponibles", "available"),
            ("[F]iltros", "filters")
        ])
        self.package_list = PackageListWidget()
        self.status_bar = StatusBar("Listo")

    def show(self):
        """Muestra la pantalla (textual: la pantalla es un App/Screen)"""
        self.refresh_packages()
        # textual monta la pantalla dentro de su App principal (ScreenManager);
        # no hay MainLoop manual.

    def refresh_packages(self):
        """Actualiza la lista de paquetes"""
        if self.filter_text:
            self.packages = self.package_manager.search_package(self.filter_text)
        else:
            self.packages = self.package_manager.get_installed_packages()

        self.package_list.set_packages(self.packages)

    def compose(self):
        """Layout declarativo (textual)"""
        yield Header()
        yield self.search_box          # Input
        yield self.filter_buttons      # RadioSet / botones
        yield self.package_list        # DataTable
        yield Footer()                 # atajos visibles
```

## 5. Detección de Distribución

```python
class DistributionDetector:
    """Detecta la distribución Linux del sistema"""

    @staticmethod
    def detect() -> str:
        """Detecta la distribución actual"""
        if os.path.exists('/etc/debian_version'):
            if os.path.exists('/etc/arch-release'):
                return 'arch'
            elif os.path.exists('/etc/fedora-release'):
                return 'fedora'
            else:
                return 'debian'

        elif os.path.exists('/etc/void-release'):
            return 'void'

        elif os.path.exists('/etc/gentoo-release'):
            return 'gentoo'

        elif os.path.exists('/etc/suse-release'):
            return 'opensuse'

        elif os.path.exists('/etc/alpine-release'):
            return 'alpine'

        # Fallback: intentar detectar por nombre del archivo
        for release_file in ['/etc/os-release', '/etc/lsb-release']:
            if os.path.exists(release_file):
                with open(release_file, 'r') as f:
                    for line in f:
                        if line.startswith('ID='):
                            return line.split('=')[1].strip('"')

        return 'generic'

    @staticmethod
    def get_distro_name() -> str:
        """Obtiene el nombre de la distribución"""
        cmd = ['lsb_release', '-ds']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()

    @staticmethod
    def get_distro_version() -> str:
        """Obtiene la versión de la distribución"""
        cmd = ['lsb_release', '-rs']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()
```

## 6. Gestión de Temas

```python
class ThemeManager:
    """Gestor de temas TUI"""

    THEMES = {
        'dark': {
            'primary': 'dark blue',
            'secondary': 'dark cyan',
            'success': 'dark green',
            'warning': 'dark yellow',
            'error': 'dark red',
            'background': 'black',
            'foreground': 'light gray'
        },
        'light': {
            'primary': 'blue',
            'secondary': 'cyan',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
            'background': 'white',
            'foreground': 'black'
        },
        'retro': {
            'primary': 'brown',
            'secondary': 'dark green',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
            'background': 'black',
            'foreground': 'light gray'
        }
    }

    def __init__(self, theme_name: str = 'dark'):
        self.theme_name = theme_name
        self.colors = self.THEMES.get(theme_name, self.THEMES['dark'])

    def get_color(self, name: str) -> tuple:
        """Obtiene color del tema"""
        return self.colors.get(name, 'default')

    def list_themes(self) -> List[str]:
        """Lista todos los temas disponibles"""
        return list(self.THEMES.keys())

    def set_theme(self, theme_name: str):
        """Cambia el tema"""
        if theme_name in self.THEMES:
            self.theme_name = theme_name
            self.colors = self.THEMES[theme_name]
```

## 7. Manejo de Errores

```python
class PackageManagerError(Exception):
    """Excepción base para errores de gestión de paquetes"""

    def __init__(self, message: str, command: str = None):
        super().__init__(message)
        self.command = command
        self.stderr = ""

    def __str__(self):
        msg = f"{super().__str__()}"
        if self.command:
            msg += f"\nComando: {self.command}"
        if self.stderr:
            msg += f"\nError: {self.stderr}"
        return msg


class ProcessMonitorError(Exception):
    """Excepción para errores del monitor de procesos"""

    pass


class UIError(Exception):
    """Excepción para errores de interfaz"""

    pass
```

## 8. Configuración

```python
class Config:
    """Gestor de configuración"""

    DEFAULT_CONFIG = {
        'theme': 'dark',
        'auto_update': True,
        'refresh_interval': 2,
        'show_details': True,
        'sort_by': 'name',
        'sort_order': 'asc'
    }

    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.path.expanduser('~/.tui-manager/config.yaml')
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Carga la configuración desde archivo"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f) or self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Guarda la configuración en archivo"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f)

    def get(self, key: str, default=None):
        """Obtiene un valor de configuración"""
        return self.config.get(key, default)

    def set(self, key: str, value):
        """Establece un valor de configuración"""
        self.config[key] = value
        self.save_config()
```

## 10. Portabilidad Multi-SO y Entornos (DE/WM)

TUI Manager separa la portabilidad en **dos planos independientes de adaptadores**:

### 10.1 Plano de SO — `PackageAdapter`

Ya implementado en `core/`: `DebianAdapter`, `ArchAdapter`, `FedoraAdapter`, `VoidAdapter`. Se agregan:

| Adaptador | SO | Gestor | Comandos clave |
|---|---|---|---|
| `GentooAdapter` | Gentoo | emerge | `emerge --search`, `emerge -a` |
| `AlpineAdapter` | Alpine | apk | `apk search`, `apk add/del` |
| `SuseAdapter` | OpenSUSE | zypper | `zypper search`, `zypper in/rm` |
| `FreeBSDAdapter` | FreeBSD | pkg | `pkg search/info`, `pkg install/remove`, `pkg autoremove` |
| `PkgsrcAdapter` (exp.) | NetBSD/OpenBSD | pkg_add/pkgin | `pkgin search`, `pkg_add/r` |
| `TermuxAdapter` | Android (Termux) | apt/pkg del prefix | `pkg search`, `pkg install/remove` (envoltorio de apt, repos de Termux) |

**Elevación de privilegios**: se detecta `sudo` o `doas` (BSD) y se usa el disponible; nunca se guardan credenciales. **En Termux/Android no hay elevación**: todos los comandos corren como usuario del prefix (`/data/data/com.termux`), y las acciones de sistema (toggles, energía) no aplican.

### 10.4 Termux/Android (soporte limitado)

Termux es un objetivo oficial de soporte **limitado** y sirve además como plataforma de prueba de primer orden (la app corre allí en un terminal real):

- **Detección**: `PREFIX` contiene `com.termux`, `TERMUX_VERSION` definida, o `uname -o` = Android → `OSInfo` reporta `termux/android` y el gestor es apt del prefix (el comando `pkg` es un envoltorio de apt con repos de Termux).
- **Paquetes**: solo los del ecosistema Termux (los nombres difieren de Debian; `python` en vez de `python3`, etc.). Opcional: detección de `proot-distro` para operar distros completas instaladas dentro de Termux.
- **Procesos**: `ps` limitado por la seguridad de Android — solo procesos propios y del prefix; kill de procesos de otras apps no es posible (sin root). La UI debe ocultar/deshabilitar las columnas que Android no reporta.
- **Entorno**: `EnvironmentDetector` devuelve `NullAdapter` (sin WM); el menú Sistema aparece deshabilitado con motivo. Temas: solo el tema interno de la TUI (textual).
- **Elevación**: sin `sudo`/`doas`; en dispositivos rooteados puede usarse `su` de forma opcional y explícita.

### 10.2 Plano de entorno — `EnvironmentAdapter` (nuevo)

Detección mediante variables de sesión y CLIs, en orden de especificidad:

```python
# Pseudocódigo de EnvironmentDetector
HYPRLAND_INSTANCE_SIGNATURE   → HyprlandAdapter   (CLI: hyprctl)
SWAYSOCK                      → SwayAdapter       (CLI: swaymsg)
I3SOCK                        → I3Adapter         (CLI: i3-msg)
BSPWM_SOCKET                  → BspwmAdapter      (CLI: bspc)
XDG_CURRENT_DESKTOP = KDE     → KDEAdapter        (gsettings/kdeglobals)
XDG_CURRENT_DESKTOP = GNOME   → GNOMEAdapter      (gsettings)
XDG_CURRENT_DESKTOP = XFCE    → XFCEAdapter       (xfconf4)
default                       → NullAdapter       (capacidades mínimas)
```

**Modelo de capacidades** — cada adaptador declara lo que soporta; la UI deshabilita el resto:

```python
class Capability(Enum):
    RELOAD_CONFIG = auto()      # hyprctl reload / swaymsg reload / i3-msg reload
    SET_GAPS = auto()           # hyprctl, bspc
    SET_WALLPAPER = auto()      # swww/swaymsg/hsetroot/feh (según sesión)
    SET_DARK_MODE = auto()      # gsettings / hyprland.conf colors
    TOGGLE_BAR = auto()         # waybar kill/launch, polybar
    SET_TERMINAL_COLORS = auto()
    LOCK_SCREEN = auto()
    SET_POWER_PROFILE = auto()  # powerprofilesctl
    TOGGLE_IDLE = auto()
    LIST_WINDOWS = auto()

class EnvironmentAdapter(ABC):
    name: str
    def capabilities(self) -> set[Capability]: ...
    def supports(self, cap: Capability) -> bool: ...
    # Un método por capacidad; NotImplementedError nunca debe llegar a la UI
    # porque la UI consulta supports() antes.
```

Reglas:

1. **Degradación elegante**: una capacidad ausente se refleja como entrada deshabilitada en el menú con su motivo; jamás un error en tiempo de uso.
2. **Backup antes de escribir**: todo cambio a configs de terceros (`~/.config/hypr/`, `waybar/`, `alacritty/`…) crea `archivo.bak-tm` en el mismo paso.
3. **El plano SO y el plano entorno no se conocen entre sí**: PackageManager ignora WMs y EnvironmentAdapter ignora distros. La UI compone ambos.

### 10.3 Theming unificado

Un **pack de tema** (YAML, estilo Omarchy) define una única fuente de verdad y se aplica por superficie según capacidades:

```yaml
name: tokyo-night
palette:
  bg: "#1a1b26"
  fg: "#c0caf5"
  accent: "#7aa2f7"
  # ... 16 colores
wallpaper: backgrounds/tokyo-night.jpg
surfaces:                    # overrides opcionales por superficie
  alacritty: {file: alacritty.toml}
  waybar: {style: style.css}
```

Al aplicarlo, `ThemeManager` recorre las superficies que el entorno declara y delega en el adaptador; en un DE expone solo lo expuesto (GTK/Qt), en TTY solo el tema interno de la TUI.

## 9. Logging

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Configura el logger principal"""

    if log_file is None:
        log_file = os.path.expanduser('~/.tui-manager/logs/app.log')

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Manejador de archivo con rotación
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # Manejador de consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formateador
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```
