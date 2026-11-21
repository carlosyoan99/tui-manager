# Documentación de la API

## Índice

1. [PackageManager](#packagemanager)
2. [ProcessMonitor](#processmonitor)
3. [DistributionDetector](#distributiondetector)
4. [ThemeManager](#thememanager)
5. [Config](#config)
6. [Eventos](#eventos)
7. [Ejemplos](#ejemplos)
8. [Empaquetado](#empaquetado)

---

## PackageManager

### Clase: `PackageManager`

Gestor principal de paquetes del sistema.

#### Constructor

```python
from tui_manager.core.package_manager import PackageManager

pm = PackageManager(distribution='debian')
```

#### Métodos

##### `get_installed_packages(filters=None)`

Obtiene la lista de paquetes instalados.

**Parámetros:**
- `filters` (dict, opcional): Filtros opcionales
  - `category` (str): Filtrar por categoría
  - `name` (str): Filtrar por nombre
  - `installed` (bool): Solo paquetes instalados

**Retorna:**
- `List[Package]`: Lista de objetos Package

**Ejemplo:**
```python
# Obtener todos los paquetes instalados
packages = pm.get_installed_packages()

# Filtrar por categoría
dev_packages = pm.get_installed_packages(category='development')

# Filtrar por nombre
firefox = pm.get_installed_packages(name='firefox')
```

**Lanza:**
- `PackageManagerError`: Si hay un error al obtener los paquetes

---

##### `search_package(query)`

Busca paquetes por nombre o descripción.

**Parámetros:**
- `query` (str): Término de búsqueda

**Retorna:**
- `List[Package]`: Lista de objetos Package encontrados

**Ejemplo:**
```python
# Buscar paquetes que contengan "python"
python_packages = pm.search_package('python')

# Buscar por descripción
text_packages = pm.search_package('editor de texto')
```

**Lanza:**
- `PackageManagerError`: Si hay un error en la búsqueda

---

##### `get_package_info(package_name)`

Obtiene información detallada de un paquete.

**Parámetros:**
- `package_name` (str): Nombre del paquete

**Retorna:**
- `Package`: Objeto Package con información completa

**Ejemplo:**
```python
info = pm.get_package_info('firefox')
print(f"Nombre: {info.name}")
print(f"Versión: {info.version}")
print(f"Descripción: {info.description}")
```

**Lanza:**
- `PackageNotFoundError`: Si el paquete no existe
- `PackageManagerError`: Si hay un error al obtener la información

---

##### `install_package(package_name, confirm=True)`

Instala un paquete.

**Parámetros:**
- `package_name` (str): Nombre del paquete a instalar
- `confirm` (bool): Si es True, requiere confirmación

**Retorna:**
- `bool`: True si la instalación fue exitosa

**Ejemplo:**
```python
# Instalar con confirmación
success = pm.install_package('firefox')

# Instalar sin confirmación (no recomendado)
success = pm.install_package('python3', confirm=False)
```

**Lanza:**
- `PackageNotFoundError`: Si el paquete no existe
- `InstallFailedError`: Si la instalación falló
- `PackageManagerError`: Si hay un error general

---

##### `remove_package(package_name, confirm=True)`

Desinstala un paquete.

**Parámetros:**
- `package_name` (str): Nombre del paquete a desinstalar
- `confirm` (bool): Si es True, requiere confirmación

**Retorna:**
- `bool`: True si la desinstalación fue exitosa

**Ejemplo:**
```python
# Desinstalar con confirmación
success = pm.remove_package('firefox')

# Desinstalar sin confirmación (no recomendado)
success = pm.remove_package('old-package', confirm=False)
```

**Lanza:**
- `PackageNotFoundError`: Si el paquete no existe
- `RemoveFailedError`: Si la desinstalación falló
- `PackageManagerError`: Si hay un error general

---

##### `update_package_cache()`

Actualiza la caché de paquetes.

**Retorna:**
- `bool`: True si la actualización fue exitosa

**Ejemplo:**
```python
# Actualizar la caché
success = pm.update_package_cache()
```

**Lanza:**
- `PackageManagerError`: Si hay un error al actualizar la caché

---

##### `upgrade_system(package_names=None)`

Actualiza el sistema completo o paquetes específicos.

**Parámetros:**
- `package_names` (List[str], opcional): Lista de paquetes a actualizar. Si es None, actualiza todo.

**Retorna:**
- `bool`: True si la actualización fue exitosa

**Ejemplo:**
```python
# Actualizar todo el sistema
success = pm.upgrade_system()

# Actualizar solo ciertos paquetes
success = pm.upgrade_system(['firefox', 'python3', 'vim'])
```

**Lanza:**
- `PackageManagerError`: Si hay un error durante la actualización

---

##### `get_updates_available()`

Obtiene la lista de paquetes que pueden ser actualizados.

**Retorna:**
- `List[Package]`: Lista de objetos Package con versiones disponibles

**Ejemplo:**
```python
# Ver qué paquetes pueden ser actualizados
updates = pm.get_updates_available()
for pkg in updates:
    print(f"{pkg.name}: {pkg.version} -> {pkg.available_version}")
```

**Lanza:**
- `PackageManagerError`: Si hay un error al obtener las actualizaciones

---

##### `get_dependencies(package_name)`

Obtiene las dependencias de un paquete.

**Parámetros:**
- `package_name` (str): Nombre del paquete

**Retorna:**
- `List[str]`: Lista de nombres de dependencias

**Ejemplo:**
```python
# Obtener dependencias
deps = pm.get_dependencies('firefox')
print(f"Dependencias: {', '.join(deps)}")
```

**Lanza:**
- `PackageNotFoundError`: Si el paquete no existe
- `PackageManagerError`: Si hay un error al obtener las dependencias

---

## ProcessMonitor

### Clase: `ProcessMonitor`

Monitor de procesos en tiempo real.

#### Constructor

```python
from tui_manager.core.process_monitor import ProcessMonitor

pm = ProcessMonitor(refresh_interval=2)
```

#### Métodos

##### `get_processes(filters=None)`

Obtiene la lista de procesos.

**Parámetros:**
- `filters` (dict, opcional): Filtros opcionales
  - `user` (str): Filtrar por usuario
  - `name` (str): Filtrar por nombre de comando
  - `min_cpu` (float): CPU mínimo (porcentaje)
  - `max_cpu` (float): CPU máximo (porcentaje)
  - `min_mem` (float): Memoria mínima (MB)
  - `max_mem` (float): Memoria máxima (MB)
  - `pid` (int): Filtrar por PID

**Retorna:**
- `List[Process]`: Lista de objetos Process

**Ejemplo:**
```python
# Obtener todos los procesos
processes = pm.get_processes()

# Filtrar por usuario
my_processes = pm.get_processes(user='carlosyoan')

# Filtrar por CPU
high_cpu = pm.get_processes(min_cpu=10.0)

# Filtrar por nombre
firefox_processes = pm.get_processes(name='firefox')
```

**Lanza:**
- `ProcessMonitorError`: Si hay un error al obtener los procesos

---

##### `get_process_by_pid(pid)`

Obtiene información de un proceso específico.

**Parámetros:**
- `pid` (int): ID del proceso

**Retorna:**
- `Process`: Objeto Process con información del proceso

**Ejemplo:**
```python
# Obtener información de un proceso específico
process = pm.get_process_by_pid(1234)
print(f"PID: {process.pid}")
print(f"CPU: {process.cpu}%")
print(f"Memoria: {process.get_memory_usage_mb()} MB")
```

**Lanza:**
- `ProcessNotFoundError`: Si el proceso no existe
- `ProcessMonitorError`: Si hay un error general

---

##### `kill_process(pid, signal=15)`

Termina un proceso.

**Parámetros:**
- `pid` (int): ID del proceso
- `signal` (int, opcional): Señal a enviar (15=SIGTERM, 9=SIGKILL)

**Retorna:**
- `bool`: True si el proceso fue terminado

**Ejemplo:**
```python
# Terminar un proceso con SIGTERM (graceful shutdown)
success = pm.kill_process(1234)

# Terminar con SIGKILL (forzado)
success = pm.kill_process(1234, signal=9)
```

**Lanza:**
- `ProcessNotFoundError`: Si el proceso no existe
- `SignalError`: Si hay un error al enviar la señal

---

##### `renice_process(pid, nice)`

Cambia la prioridad de un proceso.

**Parámetros:**
- `pid` (int): ID del proceso
- `nice` (int): Valor de prioridad (-20 a 19)

**Retorna:**
- `bool`: True si la prioridad fue cambiada

**Ejemplo:**
```python
# Cambiar a prioridad alta
success = pm.renice_process(1234, -10)

# Cambiar a prioridad baja
success = pm.renice_process(1234, 10)
```

**Lanza:**
- `ProcessNotFoundError`: Si el proceso no existe
- `SignalError`: Si hay un error al cambiar la prioridad

---

##### `get_total_cpu_usage()`

Obtiene el uso total de CPU del sistema.

**Retorna:**
- `float`: Porcentaje de CPU usado

**Ejemplo:**
```python
# Ver uso total de CPU
cpu_usage = pm.get_total_cpu_usage()
print(f"CPU usado: {cpu_usage}%")
```

---

##### `get_total_memory_usage()`

Obtiene el uso total de memoria del sistema.

**Retorna:**
- `dict`: Diccionario con:
  - `total` (float): Memoria total (MB)
  - `used` (float): Memoria usada (MB)
  - `free` (float): Memoria libre (MB)
  - `available` (float): Memoria disponible (MB)
  - `percentage` (float): Porcentaje usado

**Ejemplo:**
```python
# Ver uso de memoria
mem_usage = pm.get_total_memory_usage()
print(f"Memoria total: {mem_usage['total']} MB")
print(f"Memoria usada: {mem_usage['used']} MB")
print(f"Porcentaje usado: {mem_usage['percentage']}%")
```

---

##### `get_top_processes(count=10, by='cpu')`

Obtiene los procesos más consumidoros.

**Parámetros:**
- `count` (int, opcional): Número de procesos a retornar
- `by` (str, opcional): 'cpu' o 'mem' para ordenar por CPU o memoria

**Retorna:**
- `List[Process]`: Lista de procesos ordenados

**Ejemplo:**
```python
# Obtener los 10 procesos que más usan CPU
top_cpu = pm.get_top_processes(count=10, by='cpu')

# Obtener los 10 procesos que más usan memoria
top_mem = pm.get_top_processes(count=10, by='mem')
```

---

## DistributionDetector

### Clase: `DistributionDetector`

Detector de distribución Linux.

#### Métodos

##### `detect()`

Detecta la distribución del sistema.

**Retorna:**
- `str`: Nombre de la distribución (debian, arch, fedora, void, etc.)

**Ejemplo:**
```python
from tui_manager.core.distribution import DistributionDetector

dist = DistributionDetector.detect()
print(f"Distribución: {dist}")
```

**Lanza:**
- `DistributionError`: Si no se puede detectar la distribución

---

##### `get_distro_name()`

Obtiene el nombre completo de la distribución.

**Retorna:**
- `str`: Nombre de la distribución

**Ejemplo:**
```python
dist_name = DistributionDetector.get_distro_name()
print(f"Distribución: {dist_name}")
```

---

##### `get_distro_version()`

Obtiene la versión de la distribución.

**Retorna:**
- `str`: Versión de la distribución

**Ejemplo:**
```python
dist_version = DistributionDetector.get_distro_version()
print(f"Versión: {dist_version}")
```

---

##### `get_package_manager()`

Obtiene el gestor de paquetes por defecto.

**Retorna:**
- `str`: Nombre del gestor de paquetes

**Ejemplo:**
```python
pkg_manager = DistributionDetector.get_package_manager()
print(f"Gestor de paquetes: {pkg_manager}")
```

---

##### `is_supported()`

Verifica si la distribución es soportada.

**Retorna:**
- `bool`: True si la distribución es soportada

**Ejemplo:**
```python
from tui_manager.core.distribution import DistributionDetector

if DistributionDetector.is_supported():
    print("Tu distribución es soportada")
else:
    print("Tu distribución no es soportada")
```

---

## ThemeManager

### Clase: `ThemeManager`

Gestor de temas.

#### Constructor

```python
from tui_manager.core.theme_manager import ThemeManager

tm = ThemeManager(theme_name='dark')
```

#### Métodos

##### `get_current_theme()`

Obtiene el nombre del tema actual.

**Retorna:**
- `str`: Nombre del tema

**Ejemplo:**
```python
current_theme = tm.get_current_theme()
print(f"Tema actual: {current_theme}")
```

---

##### `set_theme(theme_name)`

Cambia el tema actual.

**Parámetros:**
- `theme_name` (str): Nombre del nuevo tema

**Retorna:**
- `bool`: True si el tema fue cambiado

**Ejemplo:**
```python
# Cambiar a tema claro
tm.set_theme('light')

# Cambiar a tema retro
tm.set_theme('retro')
```

**Lanza:**
- `ThemeError`: Si el tema no existe

---

##### `get_colors()`

Obtiene los colores del tema actual.

**Retorna:**
- `dict`: Diccionario con los colores

**Ejemplo:**
```python
colors = tm.get_colors()
print(f"Primario: {colors['primary']}")
print(f"Fondo: {colors['background']}")
```

---

##### `get_color(name)`

Obtiene un color específico del tema.

**Parámetros:**
- `name` (str): Nombre del color

**Retorna:**
- `tuple`: Tupla (foreground, background)

**Ejemplo:**
```python
primary = tm.get_color('primary')
print(f"Primario: {primary}")
```

---

##### `list_themes()`

Lista todos los temas disponibles.

**Retorna:**
- `List[str]`: Lista de nombres de temas

**Ejemplo:**
```python
themes = tm.list_themes()
print(f"Temas disponibles: {', '.join(themes)}")
```

---

## Config

### Clase: `Config`

Gestor de configuración.

#### Constructor

```python
from tui_manager.core.config import Config

config = Config(config_file='~/.config/tui-manager/config.yaml')
```

#### Métodos

##### `get(key, default=None)`

Obtiene un valor de configuración.

**Parámetros:**
- `key` (str): Clave de configuración
- `default` (any, opcional): Valor por defecto si la clave no existe

**Retorna:**
- `any`: Valor de configuración

**Ejemplo:**
```python
theme = config.get('theme', 'dark')
refresh_interval = config.get('refresh_interval', 2)
```

---

##### `set(key, value)`

Establece un valor de configuración.

**Parámetros:**
- `key` (str): Clave de configuración
- `value` (any): Valor a establecer

**Retorna:**
- `None`

**Ejemplo:**
```python
config.set('theme', 'light')
config.set('refresh_interval', 5)
```

---

##### `get_all()`

Obtiene todos los valores de configuración.

**Retorna:**
- `dict`: Diccionario con toda la configuración

**Ejemplo:**
```python
all_config = config.get_all()
print(f"Configuración completa: {all_config}")
```

---

##### `set_all(config_dict)`

Establece todos los valores de configuración.

**Parámetros:**
- `config_dict` (dict): Diccionario con la nueva configuración

**Retorna:**
- `None`

**Ejemplo:**
```python
new_config = {
    'theme': 'retro',
    'refresh_interval': 3,
    'auto_update': False
}
config.set_all(new_config)
```

---

##### `reset_to_default()`

Restaura la configuración a los valores por defecto.

**Retorna:**
- `None`

**Ejemplo:**
```python
config.reset_to_default()
```

---

##### `save()`

Guarda la configuración en archivo.

**Retorna:**
- `None`

**Ejemplo:**
```python
config.save()
```

---

##### `load()`

Carga la configuración desde archivo.

**Retorna:**
- `None`

**Ejemplo:**
```python
config.load()
```

---

## Eventos

### Eventos Personalizados

La aplicación emite eventos que pueden ser escuchados:

```python
from tui_manager.core.event import EventEmitter

# Crear un event emitter
emitter = EventEmitter()

# Escuchar eventos de paquetes
@emitter.on('package.installed')
def on_package_installed(package_name):
    print(f"Paquete {package_name} instalado")

@emitter.on('package.removed')
def on_package_removed(package_name):
    print(f"Paquete {package_name} eliminado")

# Escuchar eventos de procesos
@emitter.on('process.killed')
def on_process_killed(pid):
    print(f"Proceso {pid} terminado")

@emitter.on('process.reniced')
def on_process_reniced(pid, old_nice, new_nice):
    print(f"Proceso {pid} prioridad cambiada de {old_nice} a {new_nice}")
```

### Tipos de Eventos

- `package.installed`: Se emite cuando se instala un paquete
- `package.removed`: Se emite cuando se elimina un paquete
- `package.updated`: Se emite cuando se actualiza un paquete
- `process.killed`: Se emite cuando se termina un proceso
- `process.reniced`: Se emite cuando se cambia la prioridad de un proceso
- `system.updated`: Se emite cuando se actualiza el sistema

---

## Ejemplos

### Ejemplo Completo

```python
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.process_monitor import ProcessMonitor
from tui_manager.core.distribution import DistributionDetector
from tui_manager.core.theme_manager import ThemeManager
from tui_manager.core.config import Config

# Detectar distribución
dist = DistributionDetector.detect()
print(f"Distribución detectada: {dist}")

# Crear gestor de paquetes
pm = PackageManager(distribution=dist)

# Obtener paquetes instalados
packages = pm.get_installed_packages()
print(f"Paquetes instalados: {len(packages)}")

# Buscar paquetes
python_packages = pm.search_package('python')
print(f"Paquetes Python encontrados: {len(python_packages)}")

# Instalar un paquete
success = pm.install_package('htop', confirm=False)
print(f"Instalación de htop: {'exitosa' if success else 'fallida'}")

# Crear monitor de procesos
pm = ProcessMonitor(refresh_interval=2)
processes = pm.get_processes()

# Filtrar procesos de alto uso de CPU
high_cpu = pm.get_processes(min_cpu=10.0)

# Ver configuración
config = Config()
theme = config.get('theme', 'dark')
print(f"Tema actual: {theme}")
```

### Ejemplo con Eventos

```python
from tui_manager.core.event import EventEmitter

emitter = EventEmitter()

# Configurar listeners
@emitter.on('package.installed')
def log_package_install(package_name):
    print(f"[INFO] {package_name} instalado")

@emitter.on('package.removed')
def log_package_remove(package_name):
    print(f"[WARN] {package_name} eliminado")

@emitter.on('process.killed')
def log_process_kill(pid):
    print(f"[INFO] Proceso {pid} terminado")

# Usar la API
from tui_manager.core.package_manager import PackageManager

pm = PackageManager()

# Estos eventos serán emitidos automáticamente
pm.install_package('firefox', confirm=False)
pm.remove_package('old-app', confirm=False)

from tui_manager.core.process_monitor import ProcessMonitor

pm = ProcessMonitor()
pm.kill_process(1234)
```

---

## Errores y Excepciones

### PackageManagerError

Excepción base para errores de gestión de paquetes.

**Subclases:**
- `PackageNotFoundError`: Paquete no encontrado
- `InstallFailedError`: Falló la instalación
- `RemoveFailedError`: Falló la desinstalación
- `CommandExecutionError`: Error al ejecutar un comando

### ProcessMonitorError

Excepción para errores del monitor de procesos.

**Subclases:**
- `ProcessNotFoundError`: Proceso no encontrado
- `SignalError`: Error al enviar señal

### DistributionError

Excepción para errores de detección de distribución.

### ThemeError

Excepción para errores de temas.

---

## Notas Adicionales

- Todos los métodos que realizan operaciones de I/O pueden lanzar excepciones
- Los métodos que modifican el sistema requieren permisos de administrador
- Los procesos se actualizan automáticamente cada `refresh_interval` segundos
- La configuración se guarda automáticamente después de cada cambio
- `InstallResult` (instalaciones desde fuentes alternativas) es **truthy/falsy**:
  implementa `__bool__` devolviendo `ok`, por lo que `if result:` equivale a
  `if result.ok:`. Expone `ok`, `app`, `source`, `returncode`, `actions` y `error`.
- El rollback de una instalación fallida **nunca borra archivos del usuario**:
  solo revierte directorios vacíos creados por el propio comando. Si un directorio
  quedó con contenido, se deja intacto y se registra un aviso en el log para
  limpieza manual.

---

## Empaquetado

Los descriptores por plataforma están en [`packaging/`](../packaging/):
`PKGBUILD` (Arch/AUR), `debian/` (`control` + `rules` + `changelog`),
`tui-manager.spec` (Fedora/RPM) y `freebsd/` (`Makefile` + `pkg-descr`).
Todos usan el nombre `tui-manager` y la versión `0.5.0` (release
`0.5.0-beta.1`). Las dependencias son las de `requirements.txt`: `textual`,
`pyyaml` y `python-json-logger`; no se requieren bindings nativos.

Comandos por canal natural (detalle en la [guía de instalación](INSTALL.md)):

| Plataforma | Canal | Comando |
|---|---|---|
| Debian/Ubuntu | PyPI / `.deb` | `python3 -m pip install --user tui-manager` · `dpkg-buildpackage -us -uc -b` desde `packaging/debian/` |
| Arch | AUR / PKGBUILD | `makepkg -si` desde `packaging/` |
| Fedora | RPM | `rpmbuild -ba packaging/tui-manager.spec` |
| Void | PyPI | `python3 -m pip install --user tui-manager` |
| FreeBSD | port / `pkg` | `make makesum && sudo make install clean` desde `packaging/freebsd/` |
| Termux | PyPI en el prefix | `python -m pip install tui-manager` |

En esta entrega no se ejecutaron builds: los descriptores son plantillas que
requieren verificar el tag `v0.5.0` y las sumas antes de publicar. Stacks,
fwupd y snapshots están **en Beta 2** (B2-3); no se documentan aquí como
funciones terminadas.
