# TUI Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20BSD-lightgrey.svg)](https://www.linux.org/)

## Definición

**TUI Manager** es una aplicación de Interfaz de Usuario Terminal (TUI), escrita en Python, que **simula el flujo de control de Omarchy** (la distribución opinionated de DHH basada en Arch + Hyprland) sin ser una distribución: es un **panel de control portátil** que vive en la terminal y da acceso por menú a lo que Omarchy resuelve con sus scripts y su lanzador.

Su propósito: desde un solo menú jerárquico, navegable 100 % por teclado, poder:

- **Gestionar aplicaciones**: ver lo instalado, buscar, instalar/desinstalar, actualizar el sistema y limpiar huérfanos.
- **Monitorear y controlar procesos**: tiempo real, CPU/RAM, terminar, renicear.
- **Configurar el sistema**: toggles y ajustes del entorno (idle, notificaciones, brillo, energía, red, zona horaria).
- **Cambiar temas**: cambiar la apariencia del escritorio completo desde un tema (colores, wallpaper, terminal, barra), estilo Omarchy "pick a theme, change everything".

**La diferencia clave con Omarchy**: Omarchy es una distribución atada a Arch + Hyprland + Quickshell. TUI Manager es **portable**: funciona sobre múltiples sistemas operativos (Linux y BSD), múltiples entornos de escritorio y —foco principal— **window managers** (tiling o no), degradándose con elegancia cuando el entorno no soporta una función.

### Alcance de plataformas

| Nivel | Plataformas | Notas |
|---|---|---|
| Objetivo principal | **Debian/Ubuntu, Arch y derivados, Fedora, Void, Gentoo, OpenSUSE, Alpine, FreeBSD** | Foco en gestores de ventanas |
| Objetivo secundario | NetBSD, OpenBSD, derivados de las anteriores | Vía adaptadores del mismo plano |
| Limitado | **Termux/Android** | Paquetes del prefix (apt/`pkg`), procesos propios, temas internos de la TUI; sin sudo ni toggles de sistema |
| Futuro 2.0 | **macOS** (Homebrew, `defaults`, `osascript`) · **Windows** (winget/scoop/choco, `tasklist`) | Planificado; ver fase «2.0» en [docs/ROADMAP.md](docs/ROADMAP.md) |

| Nivel | Entornos | Soporte esperado |
|---|---|---|
| Completo | **WMs tiling**: Hyprland, Sway, i3, bspwm, dwm, awesome, Qtile | Reload de config, gaps, keybinds, bar |
| Completo | **WMs apilables**: Openbox, Fluxbox, IceWM | Menor superficie, misma interfaz |
| Parcial | **DEs**: KDE Plasma, GNOME, XFCE, MATE, Cinnamon, LXQt | Solo lo que el DE expone por herramienta propia |
| Básico | **TTY / sin entorno** | Paquetes, procesos, tema interno de la TUI |

## Funcionamiento

### Arquitectura en capas

```
┌─────────────────────────────────────────────────┐
│  UI (textual): menús Omarchy-style, pantallas,  │
│  atajos de teclado, temas internos de la TUI    │
├─────────────────────────────────────────────────┤
│  Core: ScreenManager · Config · EventEmitter    │
│  PackageManager · ProcessMonitor · ThemeManager │
│  EnvironmentManager (nuevo)                     │
├──────────────────────┬──────────────────────────┤
│  Plano de SO         │  Plano de entorno        │
│  PackageAdapter por  │  EnvironmentAdapter por  │
│  SO/distro:          │  DE/WM, con modelo de    │
│  apt · pacman · dnf  │  capacidades:            │
│  xbps · emerge · zypper│ HyprlandAdapter (hyprctl)│
│  apk · pkg (FreeBSD) │  SwayAdapter (swaymsg)   │
│                      │  I3Adapter (i3-msg)      │
│                      │  KDE/GNOME/XFCE (gsettings│
│                      │  kdeglobals, xfconf4)    │
│                      │  NullAdapter (TTY)       │
├──────────────────────┴──────────────────────────┤
│  Sistema real: subprocesos, sudo/doas,          │
│  /etc, ~/.config, ps, env vars de sesión        │
└─────────────────────────────────────────────────┘
```

### Flujo de arranque

1. **Detección de SO**: lee `/etc/os-release` (o `uname` en BSD) → elige el `PackageAdapter` correcto.
2. **Detección de entorno**: variables de sesión (`XDG_CURRENT_DESKTOP`, `WAYLAND_DISPLAY`, `HYPRLAND_INSTANCE_SIGNATURE`, `SWAYSOCK`, `I3SOCK`, `DESKTOP_SESSION`…) → elige el `EnvironmentAdapter` y consulta su **lista de capacidades**. En Termux/Android se detecta vía `PREFIX`/`TERMUX_VERSION` y se usa `NullAdapter` (soporte limitado: paquetes, procesos y temas internos).
3. **Configuración**: `~/.config/tui-manager/config.yaml` carga tema, intervalos y preferencias.
4. **Menú principal** (estilo Omarchy): el menú se genera dinámicamente — las entradas que el entorno no soporta aparecen deshabilitadas con su motivo, nunca fallan en tiempo de uso.

### Menú jerárquico (mapeado de Omarchy)

| Menú TUI Manager | Equivalente Omarchy | Contenido |
|---|---|---|
| **Aplicaciones** | `omarchy-pkg-*`, menú Install | Instalados, buscar, instalar, desinstalar, huérfanos |
| **Procesos** | btop integrado | Lista en vivo, filtros, kill, renice |
| **Sistema** | `omarchy-toggle-*`, system-* | Bloquear/salir/reiniciar/apagar, idle, notificaciones, brillo, energía, zona horaria, DNS |
| **Temas** | `omarchy-theme-*` | Tema global, wallpaper siguiente/anterior, claro/oscuro, terminal |
| **Actualizar** | `omarchy-update-*` | Ver disponibles, actualizar sistema, keyring/firmware, limpiar caché |
| **Ajustes** | Config propia | Tema de la TUI, intervalos, logging, sudo/doas |
| **Ayuda** | Manual | Atajos, diagnóstico (`tui-manager --doctor`) |

### Principios de diseño

1. **Degradación elegante**: toda acción consulta capacidades del adaptador de entorno; una función no soportada se ve deshabilitada, no rota.
2. **Confirmación antes de acciones destructivas**: desinstalar, matar procesos, tocar configuración del WM.
3. **No romper configs del sistema**: antes de modificar un archivo de configuración ajeno (Hyprland, waybar, GTK), copia de seguridad automática.
4. **Todo por teclado**: navegación con flechas/vim-keys, `?` ayuda, `q` salir, un atajo por entrada de menú.
5. **Adaptadores = extensibilidad**: un nuevo SO o WM es una clase nueva, no un cambio en el resto del código.

## Documentación

- [Guía de Instalación](docs/INSTALL.md)
- [Guía de Uso](docs/USAGE.md)
- [Documentación de la API](docs/API.md)
- [Especificaciones por Módulo](docs/MODULE_SPECS.md)
- [Especificaciones Técnicas](docs/TECHNICAL_SPECS.md)
- [Roadmap y plan por fases](docs/ROADMAP.md)
- [Resumen del proyecto](PROJECT_SUMMARY.md)

## Estructura del proyecto

```
TUI-Manager/
├── tui_manager/
│   ├── main.py               # Punto de entrada
│   ├── core/
│   │   ├── distribution.py   # Detección de SO/distro (Linux, BSD, Termux)
│   │   ├── environment.py    # detección DE/WM + capacidades
│   │   ├── package_manager.py + *_adapter.py  # plano de SO
│   │   ├── categories.py · app_catalog.py     # categorías y apps recomendadas
│   │   ├── alternative_sources.py · sources_adapter.py  # fuentes externas
│   │   ├── process_monitor.py
│   │   ├── theme_manager.py · theme_packs.py
│   │   ├── sysinfo.py · system_control.py
│   │   ├── config.py · event.py
│   ├── i18n.py               # español / inglés
│   └── ui/                   # pantallas y menús textual (app.py, screens.py)
├── config/                   # default.yaml y packs de temas
├── docs/                     # Documentación
└── tests/                    # suite simulada multi-SO + UI + CLI
```

## Estado

**1.0 Estable** — 15 criterios cumplidos y verificado en 4 equipos (CachyOS ×2, Void, Termux). La TUI con [textual](https://textual.textualize.io/) es funcional: paquetes, procesos, system, temas, actualizaciones, ajustes, ayuda, acerca de y logs, con degradación elegante por capacidades. Núcleo multi-SO (Linux, BSD, Termux) con 119 tests verdes. Ver [`CHANGELOG.md`](CHANGELOG.md) y [`docs/ROADMAP.md`](docs/ROADMAP.md) para el detalle de fases y criterios de salida.

## Licencia

MIT.

## Agradecimientos

- Inspirado en [Omarchy](https://github.com/basecamp/omarchy) de DHH (especialmente la charla *Omarchy Quattro*).
- Frameworks: [textual](https://textual.textualize.io/).
