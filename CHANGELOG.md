# Changelog — TUI Manager

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/). Las fases (Alfa/Beta/Estable) y sus criterios de salida están definidos en [`docs/ROADMAP.md`](docs/ROADMAP.md); este archivo registra **qué cambió por versión**.

---

## [0.2.0-alpha.2] — En desarrollo — Fase Alfa 2 «Plano de entorno»

Objetivo de la versión: menú **Sistema** con degradación elegante por capacidades, **A · Launch-or-focus**, **B · Acerca de** y **E · Visor de logs**; elevación con doas en BSD.

### Agregado
- **Menú Sistema** (`SystemScreen`): bloquear, salir, reiniciar, apagar, suspender, brillo ±, perfiles de energía, zona horaria y lanzar aplicación — cada entrada se deshabilita con el motivo exacto (herramienta/capacidad que falta) vía `SystemControl.availability()`; reiniciar/apagar con confirmación; `SystemControl` con fallbacks BSD (`shutdown -r/-p now`, `zzz`).
- **A · Launch-or-focus** [OM]: `launch_or_focus(env, comando)` en `core/environment.py` — enfoca si ya corre (`focus_window` por WM: hyprctl class:, swaymsg/i3-msg `[class=…] focus`, bspc `class=…`, wmctrl `-a`), si no lanza; flujo probado con salidas reales canned de `hyprctl -j clients` y árbol de sway.
- **B · Acerca de** (`AboutScreen` + `core/sysinfo.py`): SO, kernel, RAM (/proc o sysctl), disco raíz, batería (Termux/sysfs), N paquetes, CPU, entorno.
- **E · Visor de logs** (`LogsScreen`): cola del log (~/.tui-manager/logs/app.log) con refresco manual [r] y automático cada 2 s; mensaje vacío si no existe.
- **Elevación BSD con doas**: `FreeBSDAdapter` y `PkgsrcAdapter` eligen sudo→doas→nada (`_elevator()`); comandos antepuestos correctamente.
- Menú principal: entradas Sistema, Acerca de y Logs habilitadas; Temas y Actualizar siguen deshabilitadas (Beta 1).
- i18n: `system.launch_prompt`, `logs.empty` (es/en).

### Tests
- `tests/test_adapters.py`: +5 (list_windows/focus de Hyprland/Sway/i3/bspwm/GenericDE con outputs reales canned; 5 caminos de `launch_or_focus`; flujo completo Hyprland).
- `tests/test_core.py`: +7 (availability degradada y completa; reboot fallback BSD; sysinfo RAM/batería/disco/paquetes; doas preferido y antepuesto en FreeBSD; sudo antepuesto en pkgsrc).
- `tests/test_ui.py`: +5 (gating del menú Sistema con capacidades fakes; flujo de lanzar con InputScreen; Acerca de llena datos; Logs con cola real y mensaje vacío).

### Validación en vivo (Termux/Android)
- `launch_or_focus` → `launched` (setsid real); sysinfo: Android 17, 8 núcleos, 5425 MB RAM, 338 paquetes, batería 69% vía termux-battery-status; Logs muestra el log real.
- Menú Sistema en vivo: solo `launch` habilitado; el resto deshabilitado con motivo — degradación elegante correcta en Termux. (Bug corregido durante la validación: `Services.detect` no cableaba el entorno a `SystemControl`.)

---

## [0.1.0-alpha.1] — 2026-11-18 — Fase Alfa 1 «Núcleo usable» (completada)

Objetivo de la versión: la TUI arranca y hace bien tres cosas (paquetes, procesos, temas internos), sin adaptadores de entorno. **Cumplido:** suite 88/88 verde + smoke en vivo en Termux (338 paquetes reales renderizados, navegación completa).

### Agregado
- **Capa UI textual** (`tui_manager/ui/`): `TuiManagerApp` + `Services` (inyección de dependencias para tests) y pantallas `MainMenuScreen`, `PackagesScreen` (DataTable: listar/buscar/instalar/remover/info/caché con modales de confirmación), `ProcessesScreen` (refresco por intervalo configurable, kill SIGTERM/SIGKILL, renice, pausa, filtro), `SettingsScreen` (tema interno dark/light/retro aplicado a textual, idioma, intervalo) y `HelpScreen`.
- Menú con **degradación elegante**: entradas Sistema (→ Alfa 2), Temas y Actualizar (→ Beta 1) visibles pero deshabilitadas, con la fase en la que llegan.
- Temas internos de `ThemeManager` registrados como temas de textual (`tm-dark`, `tm-light`, `tm-retro`).
- `main.py` reescrito: `argparse` con `--version`, `--doctor` (informe de SO, distro, gestor, entorno de escritorio, capacidades, elevación, Python, textual y config) y `--lang es|en`; sin banner ni flujo lineal antiguo.
- i18n: clave nueva `menu.coming_soon` (es/en).
- Tests de UI: `tests/test_ui.py` (11 tests con `run_test()` y fakes inyectados: menú, navegación, búsqueda, instalar/cancelar, kill, renice, ajustes, ayuda) y `tests/test_cli.py` (4 tests de CLI).

### Cambiado
- Versión del paquete: `0.1.0-alpha.1`.

### Simulación y validación
- Suite de pruebas con **subprocesos simulados** (salidas reales canned de apt/pacman/dnf/xbps/pkg/pkgin/dpkg): **88 tests verdes** (73 núcleo/adapters + 11 UI + 4 CLI).
- Validación **en vivo en Termux/Android**: `--doctor` detecta termux → TermuxAdapter → TermuxEnvironmentAdapter (capacidad `launch_app`); smoke headless de la TUI real con `run_test()` — 338 paquetes reales en la tabla y navegación menú↔aplicaciones correcta.
- Bugs corregidos gracias a la simulación: parsers de formato real (Arch `-Qi`/`-Ss`, Debian `apt search`, Fedora `dnf check-update` rc=100, Void `-l`/`-Rs`/`-S`), bloque de `pacman -Qi` perdido por línea en blanco, columnas corridas de `ps aux`, sudo innecesario en comandos de solo lectura, imports faltantes de `Package`, bloqueo por `_get_description` con un subproceso por paquete (eliminado).

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
- Funciones nuevas de Omarchy adoptadas **A–I completas al roadmap**: A/B/E en Alfa 2; C/D/F en Beta 1; G/H/I en fase Post-1.0 planeada.
- **macOS y Windows planificados para la versión 2.0** (fase nueva en docs/ROADMAP.md; no afecta criterios de 1.0).

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
- `categories.py`: 15 categorías y ~180 apps comunes compartidas por todos los adapters.
- `environment.py`: plano de entorno (DE/WM) con modelo de capacidades; `system_control.py`; `theme_packs.py` + 5 packs en `config/themes/`.
- i18n es/en (`tui_manager/i18n.py`); `config/default.yaml`.
- Tests simulados multi-SO: `tests/` (conftest FakeRunner + adapters, distribución, entorno, temas, config, procesos).

---

[0.1.0-alpha.1]: https://github.com/tu-usuario/TUI-Manager/compare/0.1.0...0.1.0-alpha.1
[0.1.0]: https://github.com/tu-usuario/TUI-Manager/releases/tag/0.1.0
