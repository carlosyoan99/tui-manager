# Changelog — TUI Manager

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/). Las fases (Alfa/Beta/Estable) y sus criterios de salida están definidos en [`docs/ROADMAP.md`](docs/ROADMAP.md); este archivo registra **qué cambió por versión**.

---

## [0.1.0-alpha.1] — En desarrollo — Fase Alfa 1 «Núcleo usable»

Objetivo de la versión: la TUI arranca y hace bien tres cosas (paquetes, procesos, temas internos), sin adaptadores de entorno.

### En progreso
- Capa UI con textual: `ScreenManager`, `MainMenuScreen`, `PackageManagerScreen`, `ProcessMonitorScreen`, `SettingsScreen`, `HelpScreen` (pendiente de implementar; `main.py` ya importa `tui_manager.ui.screens`).
- `config/default.yaml` y directorio `config/` real.
- `tui-manager --version` y `--doctor`.
- `TermuxAdapter` (apt del prefix, sin elevación) — plataforma de desarrollo actual.
- Primeros tests con subprocesos simulados (mocks).

### Documentación
- **README.md** redefinido: definición (panel de control portable estilo Omarchy, no una distribución) y funcionamiento (arquitectura en capas, flujo de arranque, menú jerárquico mapeado de Omarchy, 5 principios de diseño).
- **docs/ROADMAP.md** nuevo: fases Alfa 1 → Alfa 2 → Beta 1 → Beta 2 → 1.0, con criterios de salida verificables y 15 criterios obligatorios para declarar 1.0 estable.
- **docs/TECHNICAL_SPECS.md** §10: portabilidad multi-SO y entornos — plano de SO (`PackageAdapter` por distro/BSD/Termux) y plano de entorno (`EnvironmentAdapter` por DE/WM con modelo de capacidades), theming unificado por packs de tema.
- **docs/INSTALL.md**: sección de instalación en Termux/Android; corrección de troubleshooting.
- **PROJECT_SUMMARY.md**: objetivo actualizado al nuevo alcance (multi-SO, foco en window managers, Termux limitado).

### Decidido (2026-11-18)
- Framework TUI: **textual** (urwid/blessed descartados).
- Nombre de paquete PyPI y CLI: **`tui-manager`**.
- BSD: **FreeBSD primero** (Alfa 2); OpenBSD/NetBSD post-1.0.
- Theming de escritorio (terminal/GTK/bar/wallpaper) recién en **Beta 1**; Alfa 1 solo temas internos de la TUI.
- Soporte **limitado** a Termux/Android incluido en Alfa 1.
- i18n (es/en) desde Alfa 1.
- Funciones nuevas de Omarchy adoptadas: al roadmap A · Launch-or-focus, B · Info del sistema, E · Visor de logs (Alfa 2); al backlog futuro C/D/F/G/H/I (complejas, fuera del roadmap actual). Ver docs/ROADMAP.md «Backlog».

### Cambiado
- `requirements.txt` limpiado: solo `textual`, `pyyaml`, `python-json-logger` + dev. Los bindings nativos (`python-apt`, `pyalpm`, `pydnf`, `xbps-python`) se eliminaron — verificado que los adaptadores usan subprocesos puros.
- `tui_manager/core/theme_manager.py`: docstring de `get_palette()` marcado como legacy pendiente de migrar a colores de textual.

---

## [0.1.0] — Especificación inicial (estado previo al versionado git)

Estado base documentado en `CREATION_SUMMARY.md` (sin fecha; pre-git).

### Agregado
- Especificación completa: README, INSTALL, USAGE, API, MODULE_SPECS, TECHNICAL_SPECS, PROJECT_SUMMARY, CREATION_SUMMARY.
- Núcleo implementado: `distribution.py` (detección Debian/Arch/Fedora/Void/Gentoo/OpenSUSE/Alpine), `config.py`, `event.py`, `package_manager.py` + adapters (`debian`, `arch`, `fedora`, `void`), `process_monitor.py`, `theme_manager.py` (dark/light/retro), `utils/logger.py`.
- `main.py` (punto de entrada; falla al importar la capa UI aún no creada), `setup.py`, `requirements.txt`.

---

[0.1.0-alpha.1]: https://github.com/tu-usuario/TUI-Manager/compare/0.1.0...0.1.0-alpha.1
[0.1.0]: https://github.com/tu-usuario/TUI-Manager/releases/tag/0.1.0
