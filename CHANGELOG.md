# Changelog — TUI Manager

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/). Las fases (Alfa/Beta/Estable) y sus criterios de salida están definidos en [`docs/ROADMAP.md`](docs/ROADMAP.md); este archivo registra **qué cambió por versión**.

---

## [2.0.1] — 2026-11-21 — mejoras de Temas, snapshots y preparación PyPI

### Agregado
- Wallpaper aleatorio (`R`) e instalación de packs desde carpeta/archivo YAML local (`L`).
- `SnapshotsScreen` en Ajustes: crear/restaurar snapshots con errores accionables.
- Bloque «Proyecto» en Ayuda con licencia MIT, GitHub y contacto por Issues.
- `LICENSE`, `MANIFEST.in` y metadata PyPI corregida (sin correos personales).

### Corregido
- Sin correos personales en el repo: canal único GitHub Issues/Security Advisory.
- `setup.py` funciona al construir sdist (`requirements.txt` incluido en el MANIFEST).

### Validación
- **484 tests verdes** en los 4 hosts · `twine check` PASSED.

---

## [2.0.0] — 2026-11-21 — multiplataforma completa (macOS/Windows) y experiencia táctil (estable)

### Agregado
- Adapters de paquetes para macOS (Homebrew) y Windows (winget/scoop/choco).
- EnvironmentAdapters y SystemControl para Darwin y Windows (wallpaper, modo
  oscuro, launch-or-focus, energía), con degradación por capacidad.
- `--doctor` e `info` del sistema con ramas macOS/Windows.
- Accesibilidad mouse/táctil: botones en modales, clic en «Marcar», Select de
  orden de procesos, botón `?`.
- Elevación segura: `sudo -n` con caché y `sudo -v` en el TTY real al suspender
  la TUI (corregido para SSH delegando `suspend()` al hilo principal).
- Configuración conforme a XDG: `~/.config/tui-manager/`, logs en
  `~/.local/state/tui-manager/`, snapshots en `~/.local/share/tui-manager/`,
  con lectura de la ruta legacy para no perder ajustes.

### Corregido
- `--doctor` solo reporta la CLI relevante de la distro (ya no avisa de apt/dnf
  en Arch ni sugiere instalar pacman cuando está instalado).

### Validación
- **469 tests verdes** en 4 hosts (Notebook, Laptop, Void-Laptop, Termux).
- CI de GitHub verificada en verde: Linux 3.10–3.13 + FreeBSD 13.4/14.2.
- macOS y Windows validados por simulación (no hay esos SO entre los hosts).

---

## [1.2.0] — 2026-11-19 — Onboarding, JSON y comunidad

### Agregado
- `--quickstart`: recorrido guiado por las 10 entradas, reutilizando el menú
  como fuente única; sugiere `tm --doctor`.
- `--json packages|processes|doctor`: salida estructurada para scripts/agentes,
  con errores a stderr y exit codes; `collect_doctor_data()` es fuente única
  compartida con `--doctor`.
- CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md y docs/DEMO.md.
- Badge de CI en README y paso `compileall` en el workflow.

### Validación
- **379 tests verdes**, JSON verificado con `json.load`, YAML válido.

### Nota
- CI en GitHub no ejecutada (requiere permiso). FreeBSD validado por simulación.

---

## [1.1.0] — 2026-11-19 — Interfaz, lote, orden y tema dinámico (completada)

### Agregado
- **1.1-A**: iconos Unicode con fallback ASCII (`TERM=dumb`); Selects compactos
  en Ajustes (`width: 34; max-width: 60%`).
- **1.1-B**: el aviso de Termux solo aparece en Termux; nota neutra en otros SO.
- **1.1-C**: selección múltiple con `Espacio` en Aplicaciones; install/remove por
  lote con una sola confirmación y una sola recarga.
- **1.1-D**: procesos ordenables por cpu, memoria, usuario, nombre y PID.
- **1.1-E**: `theme_source: manual|mutagen`; lector del `matugen.json` real de
  OpenCode/Noctalia y mapeo a paleta textual. El tema del escritorio sigue siendo
  de Noctalia.
- **1.1-F**: Acerca de con versión de SO, dispositivo, tipo, GPU, gestor de
  paquetes, sesión y pantallas, estilo fastfetch.

### Validación
- **361 tests verdes**, py_compile OK. Formato matugen verificado en 3 laptops.

---

## [1.0.0] — 2026-11-19 — 1.0 Estable (completada)

No añade funciones: declara estabilidad tras cumplir los 15 criterios del roadmap
y la regla multi-equipo del usuario.

### Validación multi-equipo (333 tests por host, soak 120 s sin errores)
- Notebook (CachyOS), laptop (CachyOS), void (Void Linux), movil (Termux/Android).
- Bug de Void corregido: detección de gestor por binarios reales (`xbps-query`).

### Criterios cerrados
- Cobertura `core` 68 % → 82 % (49 tests nuevos).
- `--doctor` con sugerencias accionables.
- Arranque 160-186 ms; refresco 66.7 ms; 5000 paquetes paginados.
- Auditoría, backups reversibles, docs al día, CI Linux+FreeBSD (YAML válido).

### Observación
- CI no ejecutada en GitHub (sin publicación); FreeBSD validado por simulación,
  no en máquina real (no disponible).

---

## [0.7.0-beta.3] — 2026-11-19 — Fase Beta 3 «Rendimiento, estabilidad y experiencia» (completada)

### Agregado
- **B3-1**: `core/perf.py` con `measure_call`, `paginate` y `PackageCache`;
  `get_installed_packages`/`get_processes` con `offset`/`limit` y caché
  invalidada automáticamente tras install/remove/update_cache.
- **B3-2**: 76 handlers auditados (0 I/O síncrono); kill/renice delegados a
  workers; guardia AST que falla si un `action_*` llama a subprocess; sondeo
  de procesos pausable con intervalo configurable.
- **B3-3**: `ui/notifications.py` con `notify()` (notify-send con fallback,
  nunca instala), `progress_animation()` y `reduced_motion_enabled()`;
  bandera `native_notifications: false` por defecto en la config.
- **B3-4**: CI de GitHub Actions en Linux + FreeBSD y checklist con medición
  de arranque/refresco.

### Validación
- **283 tests verdes**, py_compile OK, smoke y `--doctor` correctos.
- Arranque real medido: 160–186 ms (objetivo < 2 s).
- 5000 paquetes: carga 0.323 ms, paginación 0.802 ms, caché hits=50/misses=1.

---

## [0.6.0-beta.2] — 2026-11-18 — Fase Beta 2 «Portabilidad y distribución» (completada)

### Agregado
- **B2-1**: `core/audit.py` con `AuditEntry`/`AuditLog` (timestamp ISO, actor,
  acción, destino, resultado), inyección opcional en PackageManager y
  ProcessMonitor, persistencia JSONL y sanitización de credenciales.
- **B2-2**: `--doctor` consulta versión de apt/pacman/dnf/pkg/xbps-query con
  timeout y fallback «N/D»; `?` abre ayuda contextual en 11 pantallas.
- **B2-3**: Stacks por rol (dev/terminal/web), `fwupd_available()` (solo
  detección) y snapshots con `.bak-tm` conservado, sin btrfs/zfs.
- **B2-4**: `packaging/` con PKGBUILD, debian/, spec RPM y port FreeBSD;
  INSTALL por plataforma sin placeholders.

### Validación
- **236 tests verdes**, py_compile OK, smoke y `--doctor` correctos.
- paquetería no ejecutada (solo descriptores, sin builds ni publicación).

---

## [0.5.0-beta.1] — 2026-11-18 — Fase Beta 1 «Pulido e integración» (completada)

Sin funciones nuevas. Cuatro agentes en paralelo (Arquitecto, dos Implementadores
y Documentador) más verificación final.

### Cambiado
- **B1-1**: normalización NFKD + aliases es/en replicada en `DebianAdapter`,
  `VoidAdapter` y `TermuxAdapter` (9 tests nuevos, 54 en adapters).
- **B1-2**: flujo instalar → recargar → notify en `finally` (sin workers anidados);
  8 estados vacíos uniformes con la clase `status` y claves i18n existentes.
- **B1-3**: `tests/manual-checklist.md` con 40 ítems sobre 10 pantallas;
  USAGE y API documentan mensajes accionables, ayuda contextual y rollback.
- Versión del paquete y CLI a `0.5.0-beta.1`.

### Validación
- **167 tests verdes**, py_compile OK, smoke de TUI y `--doctor` correctos.
- 146 claves i18n usadas, 0 faltantes; 0 `traceback.print`.

### Decisión resuelta (2026-11-18)
- El desfase C/D/F quedó resuelto: se diferencian a **Beta 2** para respetar
  que Beta 1 no añade funciones nuevas. Ver `docs/ROADMAP.md`.

---

## [0.3.0-alpha.3] — 2026-11-18 — Fase Alfa 3 «Catálogo y fuentes» (completada)

Objetivo: ampliar el catálogo de aplicaciones recomendadas con categorías ricas y
permitir instalar desde fuentes alternativas (GitHub, Flatpak, Snap, AppImage),
notificando siempre al usuario y pidiendo confirmación; respetar la preferencia
de formato configurada y preguntar cuando haya varias variantes.

### Agregado
- `core/app_catalog.py`: catálogo de ~80 aplicaciones con metadatos de fuentes
  (`repo`, `github`, `flatpak`, `snap`, `appimage`) y 24 categorías.
- Extensión del catálogo a **179 aplicaciones en 29 categorías** (se añaden
  `backup`, `monitoring`, `finance`, `writing` y `accessibility`). Cuatro URLs
  AppImage verificadas con HTTP 200: `code`/VSCodium, Obsidian, Joplin y
  KeePassXC; se retiran las fuentes AppImage sin URL verificada.
- `core/alternative_sources.py`: `AlternativeSourceManager` con notificación,
  confirmación obligatoria para fuentes no oficiales y selección de variante.
- `core/sources_adapter.py`: proveedor de fuentes para la TUI (textual).
- `SourcesScreen` en la TUI: instalar desde catálogo con elección de fuente.
- Preferencia `preferred_install_method` en `config/default.yaml`.

### Cambiado
- **Menú principal**: cada entrada muestra su atajo al inicio (`[1] …` a `[9] …`,
  y `[0]` para el catálogo de apps, 10ª entrada). Atajos 1–9/0, ↑/↓, Enter.
- **Acerca de**: info ampliada de software (SO, kernel, distro, entorno, plataforma,
  arquitectura, equipo, usuario, Python, uptime, shell, terminal, paquetes) y
  hardware (modelo de CPU, núcleos lógicos/físicos, RAM total/usada/disponible,
  swap, disco total/usado/libre, batería), en dos secciones.
- **Indicador de carga**: `LoadingIndicator` de textual en Acerca de, Aplicaciones
  y Catálogo para tareas que demoran; se oculta al terminar.
- **Ajustes**: cada opción tiene etiqueta y explicación (tema, idioma e intervalo
  de refresco de procesos), aclarando para qué sirve la última opción.

### Corregido
- **Cierre de Alfa 3 (equipo de 3 agentes, Días 1–5):** los 3 huecos de
  `alternative_sources.py` quedaron resueltos y verificados (`QA-REPORT.md`):
  1. `build_sources()` hace 0 llamadas a `subprocess.run`; `repo` depende del
     gestor real; AppImage sin URL http(s) se descarta (`validate_sources`).
  2. `_execute_install()` con `capture_output=True`, `timeout=300` y log
     estructurado (`app/source/returncode/duracion_ms/exit_code`).
  3. `InstallResult` con rollback conservador: solo revierte directorios vacíos
     creados por el propio comando; nunca borra archivos del usuario.
- **Bug funcional CachyOS:** `pacman -Qi` localizado en español devolvía 0
  paquetes; el parser ahora normaliza clases es/en → **1202 paquetes en vivo**.
- `distribution.py`: orden de detección (os-release primero) para devolver el ID
  real (ubuntu/mint) en vez de `debian`; ramas de arch/fedora fuera de debian_version.
- Tests de detección frágiles: se mockea `subprocess.run` para no depender de que
  `lsb_release` exista en el host.
- Adapters BSD: los comandos de solo lectura ya no anteponen sudo/doas.
- Metadatos placeholder de `setup.py` y `__init__.py` reemplazados.
- Suite en **153 tests verdes**, veredicto QA **ACEPTAR**.
- README y CHANGELOG alineados con el estado real de Alfa 2.

---

## [0.2.0-alpha.2] — 2026-11-18 — Fase Alfa 2 «Plano de entorno» (completada)

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
