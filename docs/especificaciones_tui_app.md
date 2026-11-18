> **Nota de recreación (2026-11-18):** este es el documento fundacional original,
> escrito antes de la primera línea de código. Se recrea aquí para que la idea
> inicial quede versionada junto al proyecto. El estado actual y las fases viven
> en [`README.md`](../README.md), [`docs/ROADMAP.md`](ROADMAP.md) y
> [`CHANGELOG.md`](../CHANGELOG.md). Algunas decisiones aquí propuestas cambiaron
> (por ejemplo urwid → textual); esas decisiones están registradas en el CHANGELOG.

# Especificaciones TUI App - Gestor de Paquetes y Procesos

## 1. Resumen del Proyecto

Una aplicación de Interfaz de Usuario Terminal (TUI) para Linux que permite gestionar aplicaciones instaladas, instalar/desinstalar paquetes, y monitorear procesos en segundo plano de forma intuitiva y multiplataforma.

**Inspiration**: Omarchy Quattro (gestor de paquetes TUI con interfaz tipo menú)

## 2. Arquitectura del Sistema

### 2.1 Stack Tecnológico

#### Opción A: Python (Recomendado)
- **Framework TUI**: `urwid` (más completo) o `textual` (moderno y fácil de usar)
- **Parser de comandos**: `subprocess` (built-in)
- **Gestión de paquetes**: `python-apt` (Debian), `pyalpm` (Arch), `pydnf` (Fedora), `xbps-python` (Void)
- **Interfaz de usuario**: `blessed` para helpers visuales

#### Opción B: JavaScript/TypeScript
- **Framework TUI**: `blessed` (más maduro) o `ink` (moderno)
- **Parser de comandos**: `child_process` (Node.js)
- **Gestión de paquetes**: `@npm/package-manager` (wrapper de paquetes nativos)
- **Interfaz de usuario**: `blessed` para helpers visuales

### 2.2 Arquitectura en Capas

```
┌─────────────────────────────────────┐
│         Capa de Interfaz TUI         │
│  (navegación, menús, visualización)  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Capa de Lógica de Negocio       │
│  (gestión de paquetes, procesos)     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Capa de Abstracción de OS       │
│  (wrapper para diferentes distros)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│        Sistema Operativo Linux       │
│  (comandos nativos: apt, pacman, etc)│
└─────────────────────────────────────┘
```

## 3. Características Funcionales

### 3.1 Gestión de Paquetes

#### 3.1.1 Ver Aplicaciones Instaladas
- Listado de paquetes instalados
- Filtros por categoría (desarrollo, multimedia, sistema, etc.)
- Búsqueda por nombre, descripción, versión
- Información detallada (dependencias, tamaño, repositorio)

#### 3.1.2 Instalación de Paquetes
- Buscador de paquetes
- Visualización de metadatos (dependencias, descripción)
- Progreso de instalación
- Manejo de errores y dependencias faltantes
- Soporte para repositorios adicionales

#### 3.1.3 Desinstalación de Paquetes
- Listado de paquetes instalados
- Visualización de dependencias
- Opción para eliminar dependencias no usadas
- Confirmación antes de desinstalar

#### 3.1.4 Gestión de Repositorios
- Añadir/eliminar repositorios
- Actualizar lista de paquetes
- Actualizar todo el sistema

### 3.2 Monitoreo de Procesos

#### 3.2.1 Visualización de Procesos
- Lista de procesos activos
- Filtros por usuario, nombre, CPU, memoria
- Gráficos de uso de recursos
- Ordenamiento dinámico

#### 3.2.2 Acciones sobre Procesos
- Terminar procesos (kill)
- Cambiar prioridad (nice/renice)
- Mostrar detalles del proceso
- Filtrar por nombre de comando

### 3.3 Interfaz de Usuario

#### 3.3.1 Navegación
- Menús anidados tipo Omarchy
- Atajos de teclado
- Barra de estado
- Ayuda integrada

#### 3.3.2 Temas
- Tema claro/oscuro
- Personalización de colores
- Temas predefinidos (flat, retro, modern)

#### 3.3.3 Diseño
- Panel izquierdo con navegación
- Panel central con contenido
- Panel derecho con información adicional
- Modo pantalla completa

## 4. Compatibilidad por Distribución

### 4.1 Debian/Ubuntu y derivados
- **Gestor**: `apt` / `dpkg`
- **Comandos nativos**: `apt list`, `apt install`, `apt remove`, `apt show`
- **Backend**: `python-apt`

### 4.2 Arch Linux y derivados
- **Gestor**: `pacman`
- **Comandos nativos**: `pacman -S`, `pacman -R`, `pacman -Q`, `pacman -Si`
- **Backend**: `pyalpm` (recomendado) o `pacman` vía subprocess

### 4.3 Fedora y derivados
- **Gestor**: `dnf` / `yum`
- **Comandos nativos**: `dnf list installed`, `dnf install`, `dnf remove`
- **Backend**: `pydnf` o `dnf` vía subprocess

### 4.4 Void Linux
- **Gestor**: `xbps`
- **Comandos nativos**: `xbps-query`, `xbps-install`, `xbps-remove`
- **Backend**: `xbps-python`

### 4.5 Alpine Linux
- **Gestor**: `apk`
- **Comandos nativos**: `apk info`, `apk add`, `apk del`
- **Backend**: `pyapk` o `apk` vía subprocess

### 4.6 OpenSUSE
- **Gestor**: `zypper`
- **Comandos nativos**: `zypper list-installed`, `zypper install`, `zypper remove`
- **Backend**: `python-zypper` o `zypper` vía subprocess

### 4.7 Gentoo
- **Gestor**: `emerge`
- **Comandos nativos**: `emerge --list`, `emerge`, `emerge --unmerge`
- **Backend**: `gentoolkit` o `emerge` vía subprocess

### 4.8 Otros (Solus, Manjaro, etc.)
- Detectar automáticamente el gestor disponible
- Fallback a comandos genéricos si no hay backend específico

## 5. Flujo de Usuario

### 5.1 Inicio de Aplicación
1. Detectar distribución Linux
2. Cargar módulos de paquetes y procesos
3. Mostrar menú principal

### 5.2 Menú Principal
- Gestión de Paquetes
- Monitoreo de Procesos
- Configuración
- Ayuda

### 5.3 Gestión de Paquetes
1. Navegar a "Ver Paquetes Instalados"
2. Filtrar y buscar
3. Seleccionar paquete para ver detalles
4. Opciones: Instalar, Desinstalar, Ver Detalles

### 5.4 Monitoreo de Procesos
1. Navegar a "Monitorear Procesos"
2. Ver lista de procesos
3. Filtros y ordenamiento
4. Acciones: Terminar, Detalles

## 6. Dependencias

### 6.1 Python (Opción Recomendada)

#### Dependencias mínimas
```python
# urwid - Framework TUI completo
urwid>=2.6.0

# blessed - Helpers para TUI
blessed>=1.20.0

# python-apt - Debian/Ubuntu
python-apt>=2.7.0

# pyalpm - Arch Linux
pyalpm>=0.10.0

# pydnf - Fedora
pydnf>=4.2.0

# xbps-python - Void Linux
xbps-python>=0.29.0
```

#### Dependencias opcionales
```python
# colorama - Soporte multiplataforma de colores
colorama>=0.4.6

# requests - API requests
requests>=2.31.0

# pyyaml - Configuración
pyyaml>=6.0.1
```

### 6.2 JavaScript/TypeScript (Opción Alternativa)

#### Dependencias mínimas
```json
{
  "dependencies": {
    "blessed": "^1.0.0",
    "blessed-contrib": "^0.10.3",
    "chalk": "^4.1.0",
    "commander": "^11.0.0"
  },
  "devDependencies": {
    "@types/blessed": "^1.0.0",
    "@types/node": "^20.0.0"
  }
}
```

## 7. Viabilidad del Proyecto

### 7.1 Factibilidad Técnica

**Muy Alta** - El proyecto es completamente viable con ambas opciones de stack

#### Ventajas de Python:
- ✅ Frameworks TUI maduros y completos (urwid, textual)
- ✅ Módulos para gestión de paquetes de cada distribución
- ✅ Comunidad grande y documentación abundante
- ✅ Fácil integración con el sistema
- ✅ Menor curva de aprendizaje para scripts

#### Ventajas de JavaScript:
- ✅ Desarrollo moderno con TypeScript
- ✅ Ecosistema npm grande
- ✅ Migración fácil de scripts web a TUI
- ✅ Buen soporte para interfaces tipo terminal

### 7.2 Desafíos Técnicos

1. **Compatibilidad de paquetes**
   - Cada distribución usa comandos diferentes
   - Solución: Capa de abstracción con wrappers

2. **Manejo de errores**
   - Algunos comandos fallan con errores específicos
   - Solución: Manejo robusto de excepciones

3. **Privilegios**
   - Algunas operaciones requieren root
   - Solución: Detectar y solicitar sudo automáticamente

4. **Performance**
   - Listar todos los paquetes puede ser lento
   - Solución: Caché y paginación

### 7.3 Recomendación

**Usar Python con urwid o textual**

#### Razones:
1. Más maduro para TUIs
2. Mejor soporte para gestión de paquetes
3. Menor fricción para integración con el sistema
4. Más opciones para callbacks y eventos
5. Menor cantidad de dependencias para el mismo resultado

## 8. Estructura de Directorios

```
tui-manager/
├── src/
│   ├── __init__.py
│   ├── main.py              # Punto de entrada
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── screens.py       # Pantallas TUI
│   │   ├── widgets.py       # Widgets personalizados
│   │   ├── themes.py        # Temas y colores
│   │   └── navigation.py    # Sistema de navegación
│   ├── core/
│   │   ├── __init__.py
│   │   ├── package_manager.py  # Gestor de paquetes
│   │   ├── process_monitor.py  # Monitoreo de procesos
│   │   ├── distribution.py     # Detección de distribución
│   │   └── commands.py         # Comandos nativos
│   ├── models/
│   │   ├── __init__.py
│   │   ├── package.py          # Modelo de paquete
│   │   ├── process.py          # Modelo de proceso
│   │   └── command.py          # Modelo de comando
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Logging
│       └── helpers.py          # Funciones auxiliares
├── tests/
│   ├── __init__.py
│   ├── test_package_manager.py
│   ├── test_process_monitor.py
│   └── test_distribution.py
├── config/
│   ├── default.yaml            # Configuración por defecto
│   └── themes/                 # Temas predefinidos
│       ├── dark.yaml
│       ├── light.yaml
│       └── retro.yaml
├── docs/
│   ├── INSTALL.md              # Guía de instalación
│   ├── USAGE.md                # Guía de uso
│   └── API.md                  # Documentación API
├── requirements.txt            # Dependencias Python
├── setup.py                    # Script de instalación
├── README.md                   # Documentación principal
└── LICENSE                     # Licencia
```

## 9. Interfaz de Usuario (Mockup)

### 9.1 Menú Principal
```
┌─────────────────────────────────────────────────────┐
│  🎛️  TUI Manager v1.0.0                              │
├─────────────────────────────────────────────────────┤
│  [G] Gestión de Paquetes                            │
│  [P] Monitoreo de Procesos                          │
│  [C] Configuración                                   │
│  [?] Ayuda                                           │
├─────────────────────────────────────────────────────┤
│  Presiona cualquier tecla para continuar            │
└─────────────────────────────────────────────────────┘
```

### 9.2 Gestión de Paquetes
```
┌─────────────────────────────────────────────────────┐
│  📦 Gestión de Paquetes                              │
├─────────────────────────────────────────────────────┤
│  [Buscar: ]___________________[Buscar]             │
│  [Instalados] [Disponibles] [Filtros]               │
├─────────────────────────────────────────────────────┤
│  [1] firefox  │ v115.0  │  [Instalar] [Ver]        │
│  [2] python3  │ v3.11   │  [Instalar] [Ver]        │
│  [3] vim      │ v9.0    │  [Desinstalar] [Ver]     │
│  [4] git      │ v2.42   │  [Instalar] [Ver]        │
│  [5] neovim   │ v0.9    │  [Instalar] [Ver]        │
├─────────────────────────────────────────────────────┤
│  Página 1/10  |  [Anterior] [Siguiente]             │
└─────────────────────────────────────────────────────┘
```

### 9.3 Monitoreo de Procesos
```
┌─────────────────────────────────────────────────────┐
│  📊 Monitoreo de Procesos                            │
├─────────────────────────────────────────────────────┤
│  [Usuario: carlosyoan] [Filtro: _______________]    │
│  [CPU] [MEM] [PID] [Comando]                        │
├─────────────────────────────────────────────────────┤
│  [PID]  [CPU%]  [MEM%]  [Comando                    │
│  1234   2.3     5.1     firefox                      │
│  5678   1.1     2.3     python3                       │
│  9012   0.8     1.5     gnome-shell                   │
│  3456   0.5     0.9     bash                          │
│  7890   0.3     0.5     htop                          │
├─────────────────────────────────────────────────────┤
│  [Kill] [Detalles] [Actualizar] [Filtrar]           │
└─────────────────────────────────────────────────────┘
```

## 10. Roadmap de Desarrollo

### Fase 1: MVP (2-3 semanas)
- [x] Estructura base del proyecto
- [ ] Detección de distribución
- [ ] Listado de paquetes instalados
- [ ] Búsqueda de paquetes
- [ ] Instalación básica de paquetes
- [ ] Interfaz TUI básica con urwid
- [ ] Tema claro/oscuro

### Fase 2: Funcionalidad Completa (3-4 semanas)
- [ ] Desinstalación de paquetes
- [ ] Gestión de repositorios
- [ ] Monitoreo de procesos
- [ ] Filtros avanzados
- [ ] Temas personalizados
- [ ] Ayuda integrada
- [ ] Configuración persistente

### Fase 3: Optimización y Mejoras (2-3 semanas)
- [ ] Caché de paquetes
- [ ] Paginación de listas
- [ ] Mejor manejo de errores
- [ ] Actualización automática del sistema
- [ ] Exportar/importar configuraciones
- [ ] Script de instalación portable

### Fase 4: Documentación y Distribución (1-2 semanas)
- [ ] Documentación completa
- [ ] Script de instalación
- [ ] Página en GitHub
- [ ] Publicar en PyPI
- [ ] Crear paquetes para distribuciones

## 11. Consideraciones de Seguridad

- Validar todas las entradas de usuario
- Sanitizar comandos antes de ejecutar
- Manejo seguro de permisos (sudo)
- Logs de auditoría de acciones
- No ejecutar comandos con privilegios sin confirmación
- Validar que los comandos sean ejecutables

## 12. Licencia

Propuesta: MIT License (permite uso libre, modificación y distribución)

## 13. Recursos Adicionales

### Documentación
- [Urwid Documentation](https://urwid.org/)
- [Textual Documentation](https://textual.dev/)
- [Blessed Documentation](https://github.com/christopheraue/blessed)
- [Omarchy GitHub](https://github.com/omarchy/omarchy)

### Comandos de Paquetes
- [Debian Package Management](https://wiki.debian.org/Apt)
- [Arch Package Management](https://wiki.archlinux.org/title/Pacman)
- [Fedora Package Management](https://docs.fedoraproject.org/en-US/quick-docs/dnf/)
- [Void Package Management](https://docs.voidlinux.org/manual/packages.html)

### Referencias de TUI
- [Terminal User Interfaces in Python](https://realpython.com/python-tkinter/)
- [Building TUI Apps with Python](https://docs.python.org/3/library/curses.html)

## 14. Conclusión

El proyecto es **altamente viable** y recomendado para desarrollo con Python debido a:
1. Frameworks TUI maduros y bien documentados
2. Soporte robusto para gestión de paquetes en todas las distribuciones
3. Menor complejidad técnica para integración con el sistema
4. Gran comunidad de soporte

La arquitectura propuesta permite una fácil extensión y mantenimiento a largo plazo.
