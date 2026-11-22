# TUI Manager

[![CI](https://github.com/carlosyoan99/tui-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/carlosyoan99/tui-manager/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20BSD%20%7C%20macOS%20%7C%20Windows%20%7C%20Termux-lightgrey.svg)](https://github.com/carlosyoan99/tui-manager)

**Versión actual: 2.0.2 (estable)** · 567 tests verdes · CI verde en Linux + FreeBSD.

## ¿Qué es?

Un **panel de control en la terminal** inspirado en [Omarchy Quattro](https://github.com/basecamp/omarchy), escrito en Python con [textual](https://textual.textualize.io/). No es una distribución: es un menú jerárquico, navegable 100 % por teclado (y con mouse/táctil), que reúne en un solo lugar lo que antes hacías con varios comandos:

- **Aplicaciones**: ver lo instalado, buscar, instalar/desinstalar (incluido por lote), actualizar y limpiar huérfanos.
- **Procesos**: monitor en tiempo real con CPU/RAM, filtros, orden por 5 criterios, kill, renice y pausa.
- **Sistema**: bloqueo, energía, brillo, perfiles, zona horaria y lanzar apps (con degradación elegante: lo que tu entorno no soporta aparece desactivado con el motivo).
- **Temas**: packs YAML que cambian paleta, wallpaper y modo claro/oscuro por superficie, con backups `.bak-tm`. El tema de la TUI puede seguir dinámicamente el esquema [matugen](https://github.com/InioX/matugen) que genera Noctalia desde tu wallpaper.
- **Actualizar, Ajustes, Ayuda, Acerca de y Logs**, más un **catálogo de 179 apps** en 29 categorías con fuentes alternativas (GitHub, Flatpak, Snap, AppImage) que siempre piden confirmación.

La diferencia con Omarchy: Omarchy está atado a Arch + Hyprland + Quickshell. TUI Manager corre sobre **Linux, BSD, macOS, Windows y Termux**, sobre WMs, DEs o TTY, adaptándose a lo que cada entorno expone.

## Inicio rápido

```bash
tm              # abre la TUI (comando disponible en tus 4 equipos)
tm --version    # tui-manager 2.0.2
tm --doctor     # diagnóstico: SO, distro, gestor, entorno, CLIs, capacidades, elevación
tm --quickstart # recorrido guiado por las 10 entradas del menú
tm --json doctor|packages|processes   # salida estructurada para scripts/agentes
tm --lang en    # interfaz en inglés
```

Si `tm` no está en tu PATH, el comando real es `python3 -m tui_manager.main` desde la carpeta del proyecto.

### Instalación desde fuente

```bash
git clone https://github.com/carlosyoan99/tui-manager.git
cd tui-manager
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pip install -e .
tui-manager
```

En Termux no se puede crear venv (`ensurepip` no disponible): se usa `python3 -m tui_manager.main` con el `textual` del sistema.

## El menú (atajos `[1]`–`[9]` y `[0]`)

| Tecla | Pantalla | Qué hace |
|---|---|---|
| `[1]` | Aplicaciones | Instalar/desinstalar, buscar, caché, upgrade, huérfanos; `Espacio` marca para lote |
| `[2]` | Procesos | CPU/RAM, filtros, orden, kill, renice, pausa |
| `[3]` | Sistema | Energía, brillo, toggles y launch-or-focus según capacidades |
| `[4]` | Temas | Packs, wallpaper siguiente/anterior, claro/oscuro, instalar desde URL |
| `[5]` | Actualizar | Actualizaciones, caché, huérfanos, fwupd opcional |
| `[6]` | Ajustes | Tema de la TUI, origen del tema (manual/matugen), idioma, intervalo |
| `[7]` | Ayuda | Atajos y sugerencia de `--doctor` |
| `[8]` | Acerca de | Info estilo fastfetch: SO, dispositivo, GPU, RAM, pantallas, batería… |
| `[9]` | Logs | Cola del log con refresco |
| `[0]` | Catálogo de apps | 179 apps, marcar e instalar por lote desde fuentes verificadas |

**Atajos útiles:** `?` ayuda contextual · `Esc` volver · `y/n` en confirmaciones (también botones clicables) · `s` cicla el orden de procesos · `Espacio` marca apps.

## Plataformas

| Nivel | Sistemas |
|---|---|
| Completo | Debian/Ubuntu, Arch (CachyOS, Manjaro…), Fedora, Void, FreeBSD |
| Completo | **macOS** (Homebrew, `defaults`, `osascript`) y **Windows** (winget/scoop/choco, `reg`, `powershell`) — validados por simulación |
| Limitado | NetBSD, OpenBSD (pkgsrc), Gentoo, OpenSUSE, Alpine |
| Limitado | Termux/Android: paquetes del prefix, procesos propios, tema interno |
| Entornos | WMs tiling (Hyprland, Sway, i3, bspwm), WMs apilables, DEs (KDE, GNOME, XFCE) y TTY |

## Configuración (XDG)

La app no ensucia tu carpeta personal:

| Dato | Ruta |
|---|---|
| Configuración | `~/.config/tui-manager/config.yaml` (`$XDG_CONFIG_HOME`) |
| Logs | `~/.local/state/tui-manager/logs/app.log` (`$XDG_STATE_HOME`) |
| Snapshots | `~/.local/share/tui-manager/snapshots/` (`$XDG_DATA_HOME`) |

Si tenías la antigua `~/.tui-manager/`, el código la lee como fallback para no perder ajustes, pero escribe siempre en la nueva ruta.

## Seguridad

- Las acciones destructivas piden confirmación y dejan rastro en el log de auditoría (`AuditLog`).
- Instalar desde fuentes externas **siempre notifica y pide OK**; el rollback solo revierte directorios vacíos creados por el propio comando, nunca borra archivos del usuario.
- `sudo` nunca se guarda ni se pasa por argumento: se usa `sudo -n` si hay credenciales cacheadas; si no, se suspende la TUI y se ejecuta `sudo -v` en el TTY real (funciona también por SSH). En BSD se usa `doas`.

## Estructura del proyecto

```
TUI-Manager/
├── tui_manager/
│   ├── main.py                 # CLI: --version/--doctor/--quickstart/--json/--lang
│   ├── i18n.py                 # español / inglés
│   ├── core/
│   │   ├── adapters por SO     # debian, arch, fedora, void, termux, freebsd,
│   │   │                       # pkgsrc, macos, windows
│   │   ├── environment.py      # adapters de DE/WM (capacidades)
│   │   ├── system_control.py   # energía, brillo, bloqueo… por plataforma
│   │   ├── app_catalog.py      # 179 apps / 29 categorías
│   │   ├── alternative_sources.py · sources_adapter.py · stacks.py · snapshots.py
│   │   ├── paths.py            # rutas XDG
│   │   ├── audit.py · perf.py · sysinfo.py · config.py · theme_packs.py
│   └── ui/
│       ├── app.py              # TuiManagerApp (inyección de servicios)
│       ├── screens.py          # las 10 pantallas + modales clicables
│       └── theme_mutagen.py    # paleta dinámica desde matugen
├── config/                     # default.yaml + 5 packs de tema
├── packaging/                  # PKGBUILD, debian/, spec RPM, port FreeBSD
├── tests/                      # 469 tests simulados (multi-SO, sin red real)
├── docs/                       # ver índice abajo
├── CONTRIBUTING.md · SECURITY.md · CODE_OF_CONDUCT.md
├── AGENTS.md                   # guía para agentes de IA
└── .github/workflows/ci.yml    # Linux 3.10–3.13 + FreeBSD 13.4/14.2
```

## Documentación

- Para usuarios: [USAGE.md](docs/USAGE.md) · [INSTALL.md](docs/INSTALL.md) · [DEMO.md](docs/DEMO.md)
- Técnica: [API.md](docs/API.md) · [TECHNICAL_SPECS.md](docs/TECHNICAL_SPECS.md) · [MODULE_SPECS.md](docs/MODULE_SPECS.md)
- Planificación: [ROADMAP.md](docs/ROADMAP.md) · [INVESTIGACION-MERCADO.md](docs/INVESTIGACION-MERCADO.md)
- Trazabilidad: [CHANGELOG.md](CHANGELOG.md) · [docs/QA-REPORT.md](docs/QA-REPORT.md) · [docs/RETROSPECTIVA.md](docs/RETROSPECTIVA.md)
- Idea original: [docs/especificaciones_tui_app.md](docs/especificaciones_tui_app.md)

## Desarrollo

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest --cov=tui_manager.core --cov-report=term -q
```

La suite es 100 % simulada (`FakeRunner`, `monkeypatch`): ningún test ejecuta `sudo`, `pacman`, `brew`, `winget` ni red. La CI corre en GitHub Actions con la misma suite en 6 combinaciones de SO/Python.

## Licencia

[MIT](LICENSE) — Carlos Yoan.
