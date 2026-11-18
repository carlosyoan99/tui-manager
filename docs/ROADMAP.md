# Roadmap — TUI Manager

Plan por fases: alfas → betas → 1.0 estable. Cada fase tiene **criterios de salida verificables**; una fase no se cierra hasta cumplirlos todos.

**Distribución de alcance (decisión 2026-11-18):** las **alfas** concentran el grueso de la funcionalidad (≈90 %): cada pantalla, acción y atajo nuevo entra en una alfa. Las **betas** cubren el 10 % restante y sobre todo **pulido, integración entre pantallas, coherencia visual/UX y corrección de errores** sobre lo ya implementado. La **1.0 estable** se declara solo cuando todo funciona, está validado en las plataformas objetivo y no quedan criterios pendientes.

Leyenda de investigación previa (fuentes):
- **[OM]** Comportamiento real de Omarchy, verificado en su repo (`bin/omarchy-*`, ~250 scripts) y manual.
- **[ENV]** Detección e integración de DE/WM: variables de sesión (`XDG_CURRENT_DESKTOP`, `WAYLAND_DISPLAY`, `HYPRLAND_INSTANCE_SIGNATURE`, `SWAYSOCK`, `I3SOCK`, `DESKTOP_SESSION`) y CLIs (`hyprctl`, `swaymsg`, `i3-msg`, `gsettings`, `xfconf4`, `kdeglobals`).
- **[BSD]** FreeBSD `pkg` (install/search/info/autoremove) y `doas`/sudo.
- **[TERMUX]** Termux/Android (soporte limitado): `PREFIX`/`TERMUX_VERSION` para detección, `pkg` como envoltorio de apt con repos propios, sin elevación de privilegios, `ps` restringido por Android a procesos propios.
- **[THEME]** Theming unificado: la paleta se aplica por superficie (terminal, GTK vía gsettings/xsettings, Qt vía qt5ct/kdeglobals, bar vía waybar/polybar style, wallpaper) — mismo enfoque de los packs de tema de Omarchy [OM].

---

## Fase Alfa 1 — `0.1.x` «Núcleo usable» ✅ (completada)

**Objetivo**: la TUI existe y hace bien tres cosas: paquetes, procesos, temas internos. Sin adaptadores de entorno todavía.

Trabajo:
- [x] Implementar la capa UI con textual: `MainMenuScreen`, `PackagesScreen`, `ProcessesScreen`, `SettingsScreen`, `HelpScreen`, modales de confirmación.
- [x] `config/default.yaml` + directorio `config/` real.
- [x] Conectar `PackageManager` + adapters existentes a las pantallas.
- [x] Conectar `ProcessMonitor` (listar, filtrar, kill con confirmación, renice).
- [x] Temas internos de la TUI (dark/light/retro ya en `theme_manager.py`).
- [x] Detección de SO con aviso de "no soportado".
- [x] `requirements.txt`: un solo framework TUI (textual), resto en extras de desarrollo.
- [x] `tui-manager --version`, `--doctor`.
- [x] Soporte Termux/Android [TERMUX]: `TermuxAdapter`, detección, sin elevación.
- [x] Tests: adapters con subproceso simulado, distribución, config, UI con `run_test()`.

**Criterios de salida (todos):**
1. `tui-manager` arranca sin excepciones en Debian/Ubuntu, Arch reales **y Termux/Android**.
2. Instalar y desinstalar un paquete trivial, y matar un proceso, funcionan de punta a punta por UI.
3. Cero traceback no manejado en 30 min de uso continuo.
4. `--doctor` reporta SO, gestor de paquetes, entorno detectado, perms sudo/doas.
5. Cobertura de tests del core ≥ 60 %.

---

## Fase Alfa 2 — `0.2.x` «Plano de entorno» ✅ (completada)

**Objetivo**: introducir el **EnvironmentAdapter** y el menú **Sistema**; soporte BSD.

Trabajo:
- [x] `core/environment.py`: `EnvironmentDetector` y jerarquía `EnvironmentAdapter` con **modelo de capacidades**.
- [x] `HyprlandAdapter`, `SwayAdapter`, `I3Adapter`, `BspwmAdapter`, `GenericDEAdapter`, `TTYAdapter`, `TermuxEnvironmentAdapter`.
- [x] Menú **Sistema**: bloquear, salir, reiniciar, apagar, suspender, brillo, perfiles de energía, zona horaria, lanzar aplicación.
- [x] Degradación elegante: entrada deshabilitada + motivo cuando la capacidad no existe.
- [x] `FreeBSDAdapter` de paquetes (`pkg`) + soporte `doas` además de sudo.
- [x] Detección de NetBSD/OpenBSD (pkgsrc) como adaptador experimental.
- [x] Backups automáticos antes de modificar configs del WM (`archivo.bak-tm`).
- [x] **A · Launch-or-focus** [OM]: foco si ya corre (hyprctl/swaymsg/i3-msg/bspc/wmctrl) y lanzamiento si no.
- [x] **B · Info del sistema**: pantalla «Acerca de» — SO, kernel, RAM, disco, batería, N paquetes.
- [x] **E · Visor de logs**: log dentro de la TUI con refresco.

**Criterios de salida:**
1. En Hyprland y en i3 reales: gaps y wallpaper conmutables desde el menú Sistema/Temas con backup previo.
2. En un DE (XFCE o KDE): lo no soportado se muestra deshabilitado con motivo, sin errores.
3. En TTY: la app funciona completa salvo menú Sistema/Temas (básico).
4. En FreeBSD: instalar/desinstalar vía `pkg` funciona; sudo y doas ambos soportados.
5. Ninguna escritura a config de terceros sin `.bak-tm` en el mismo paso.

---

## Fase Alfa 3 — `0.3.x` «Temas, Actualizar e interfaz» *(actual)*

**Objetivo**: completar el grueso de las funciones restantes: el momento insignia de los temas, el menú Actualizar, los huérfanos y la capa de interfaz/atajos.

Trabajo:
- [x] **Packs de temas** en YAML (paleta + wallpaper + overrides por superficie) y `config/themes/` con 5 packs [OM].
- [x] Aplicación de paleta por superficie según capacidades: terminal (alacritty/foot/kitty), GTK claro/oscuro, wallpaper; backups `.bak-tm` previos [THEME].
- [ ] Wallpaper: siguiente/anterior/aleatorio del pack desde la pantalla Temas [OM].
- [ ] Toggle claro/oscuro global desde Temas.
- [ ] Instalación/remoción de packs desde el menú (carpeta local + URL).
- [ ] Menú **Actualizar** completo: disponibles, actualizar sistema, huérfanos, caché [OM].
- [ ] Huérfanos por distro en los adapters (apt autoremove, pacman -Qtdq, dnf autoremove, xbps-remove -o, pkg autoremove).
- [ ] **D · Actualización de firmware (opcional)** [OM]: sección del menú Actualizar si `fwupdmgr` está presente.
- [ ] Snapshots de configuración propia (backup/restore de `~/.config/tui-manager`).
- [ ] **Interfaz y atajos**: hoja de estilos textual (layout, bordes, estados), paleta de comandos (`Ctrl+P`), números 1–9 en el menú, foco correcto (lista/tabla primero, `/` para buscar), `?` con ayuda contextual por pantalla, indicadores de carga.
- [ ] Paginación y caché de listas largas; refresco asíncrono de procesos.
- [ ] Cobertura de tests del core ≥ 75 % con simulación multi-SO.

**Criterios de salida:**
1. En Hyprland + terminal soportado: cambiar de tema aplica paleta a terminal + GTK + wallpaper en una sola acción, reversible con backup.
2. Los 5 packs incluidos aplican sin errores en al menos 2 WMs distintos (simulado + real cuando haya hardware).
3. Actualizar sistema y limpiar huérfanos funcionan en Debian, Arch y FreeBSD (simulado).
4. Lista de 5 000+ paquetes navegable sin bloqueo perceptible (< 500 ms por refresco).
5. Toda pantalla responde a `?` con ayuda correcta y los atajos están documentados dentro de la TUI.
6. Cobertura de tests del core ≥ 75 %.

---

## Fase Alfa 4 — `0.4.x` «Catálogo e instantáneas»

**Objetivo**: completar la funcionalidad restante del ~90 % (todo lo que no es pulido).

Trabajo:
- [ ] **C · Stacks recomendados** [OM]: catálogo YAML portátil de apps por rol (editor, terminal, navegador, dev) que usa el plano de paquetes e instala en lote.
- [ ] **F · Snapshots extendidos** [OM]: backup/restore de configs del WM y bar (sobre `.bak-tm`); nunca snapshots de sistema (btrfs/zfs).
- [ ] Webapps ligeras (**G**) si el catálogo lo requiere; documentar H/I como fase post-1.0.

**Criterios de salida:**
1. Instalar un stack completo (p. ej. «dev») desde el catálogo funciona en Debian y Arch simulados.
2. Restaurar un snapshot devuelve exactamente los archivos previos y conserva el `.bak-tm`.
3. Catálogo visible y legible en la TUI sin bloquear.

---

## Fase Beta 1 — `0.5.x` «Pulido e integración (10 % restante)»

**Objetivo**: no añade funciones nuevas; pule, integra y corrige lo implementado en las alfas.

Trabajo:
- [ ] Corrección de errores detectados en pruebas reales (CachyOS/Void/Termux).
- [ ] Integración entre pantallas: flujos coherentes (instalar → recargar lista → tema → wallpaper), estados vacíos y mensajes uniformes.
- [ ] Consistencia visual: misma jerarquía, colores y espaciado en todas las pantallas; ajustes finos de theming por superficie (bar/GTK/Qt).
- [ ] Atajos finales y accesibilidad (foco, navegación solo-teclado, modales).
- [ ] Manejo de errores uniforme: toda acción fallida muestra mensaje accionable (nunca traceback).
- [ ] Ayuda contextual definitiva por pantalla.

**Criterios de salida:**
1. Sesión de prueba guiada (checklist) sin errores ni estados confusos en Debian, Arch, FreeBSD y Termux.
2. Toda acción destructiva pasa por confirmación y deja rastro en el log.
3. Ninguna pantalla bloquea la UI más de 500 ms.

---

## Fase Beta 2 — `0.6.x` «Portabilidad y distribución»

**Objetivo**: calidad de producto y alcance de plataformas completo.

Trabajo:
- [ ] Manejo de errores uniforme: toda acción fallida muestra mensaje accionable en la TUI (nunca traceback).
- [ ] Ayuda integrada contextual por pantalla (`?`).
- [ ] Diagnóstico `--doctor` ampliado: capacidades del entorno, SO, versión de CLIs.
- [ ] Empaquetado: `pip install tui-manager` (PyPI), PKGBUILD (AUR), `.deb`/`.rpm` buildables, port/pkg para FreeBSD.
- [ ] i18n: español e inglés (esqueleto de traducciones).
- [ ] Logging de auditoría de acciones destructivas (kill, remove, writes) [seguridad].
- [ ] Docs al día con la realidad: USAGE con capturas asciinema, API, INSTALL por plataforma.

**Criterios de salida:**
1. Instalable en Debian, Arch, Fedora y FreeBSD desde sus canales naturales, sin pasos manuales de dependencias.
2. Toda pantalla responde `?` con ayuda correcta.
3. Cero mensajes de error sin accionable en una sesión de prueba guiada (checklist en `tests/manual-checklist.md`).
4. Auditoría registra todas las acciones destructivas con timestamp y destino.

---

## 1.0 Estable

### Criterios para declarar 1.0 estable

Se declaran **todos** obligatorios (no es una lista de deseos, es una barrera):

**Funcionalidad**
1. Los 6 menús principales (Aplicaciones, Procesos, Sistema, Temas, Actualizar, Ajustes) completos y operativos.
2. Pack de temas que cambia terminal + GTK/Qt + bar + wallpaper en los WMs objetivo.
3. Sistema de capacidades: ninguna función rota en entorno no soportado (degradación verificada).

**Portabilidad**
4. Funciona sin modificaciones en: ≥ 5 distribuciones Linux (Debian, Arch, Fedora, Void + 1 más) y FreeBSD.
5. Soporte verificado en ≥ 3 WMs tiling, ≥ 1 WM apilable y ≥ 2 DEs con degradación elegante.
6. Modo TTY funcional (paquetes + procesos + ajustes internos) y soporte limitado verificable en Termux/Android.

**Robustez**
7. ≥ 80 % de cobertura de tests en `core`; CI verde en Linux + FreeBSD (GitHub Actions).
8. Sesión de 2 horas de uso real sin traceback no manejado, en al menos 2 plataformas distintas.
9. Toda modificación a configs de terceros hace backup previo y es reversible.

**Rendimiento**
10. Arranque < 2 s en hardware modesto (≤ 8 GB RAM, HDD/SSD viejo).
11. Refresco de procesos < 500 ms; listas de paquetes paginadas con respuesta inmediata.

**Seguridad**
12. Confirmación explícita antes de toda acción destructiva; registro de auditoría.
13. Ninguna contraseña manejada en claro; sudo/doas invocados sin guardar credenciales.

**Documentación**
14. README, INSTALL (por plataforma), USAGE, API y ROADMAP reflejan la versión publicada, sin funcionalidades fantasma documentadas.
15. `--doctor` capaz de autodiagnosticar una instalación rota y señalar el fix.

---

## Decisiones tomadas (2026-11-18)

1. **Framework TUI: textual**. urwid/blessed descartados. `requirements.txt` limpiado (los adaptadores usan subproceso puro, sin bindings nativos).
2. **Theming de escritorio: como está planificado** — solo temas internos de la TUI en Alfa 1; escritorio completo (terminal/GTK/bar/wallpaper) en Beta 1.
3. **BSD: FreeBSD primero** en Alfa 2; OpenBSD/NetBSD post-1.0.
4. **Nombre: `tui-manager`** para PyPI y comando de CLI.
5. **i18n (es/en) desde Alfa 1.**
6. **Funciones nuevas adoptadas de la investigación de Omarchy** (2026-11-18, A–I completas, en el roadmap):
   - **Alfa 2**: A · Launch-or-focus, B · Info del sistema «Acerca de», E · Visor de logs.
   - **Beta 1**: C · Stacks recomendados, D · fwupd opcional, F · Snapshots extendidos (configs del WM).
   - **Post-1.0 planeado**: G · Webapps, H · Integración agéntica, I · Capacidades de hardware.
7. **Soporte macOS y Windows planificado para la versión 2.0** (no en 1.0): macOS vía Homebrew y `defaults`/`osascript`; Windows vía winget/scoop/choco y `tasklist`/`taskkill`. Ver fase «2.0» en este roadmap.

## Post-1.0 — fase planeada (G · H · I)

Adoptadas al roadmap (2026-11-18) como fase siguiente a 1.0. Se priorizarán después de 1.0 estable y cada una entrará con sus propios criterios al promoverse.

| # | Función | Origen Omarchy | Idea para TUI Manager |
|---|---|---|---|
| G | Webapps | `omarchy-webapp-install` | Sitios como apps dedicadas vía navegador del entorno |
| H | Integración agéntica | Omarchy 4 (agentes) | CLI estructurada y amigable para agentes de IA |
| I | Capacidades de hardware | `omarchy-toggle-*`, hibernación, screensaver | Cada capacidad vive o muere según el `EnvironmentAdapter`; nada asumido |

---

## 2.0 — macOS y Windows (planeada)

Soporte **nativo** a macOS y Windows, extendiendo los dos planos de adaptadores (SO y entorno) definidos en la spec técnica. No forma parte de los criterios de 1.0.

### macOS
- **Paquetes**: `MacOSAdapter` (Homebrew: `brew search/info/install/remove`, `brew update/upgrade`; `brew services` opcional).
- **Entorno**: `MacOSAdapter` de entorno — wallpaper vía `osascript`, modo oscuro vía `defaults write -g AppleInterfaceStyle`, launch-or-focus con `open -a`.
- **Procesos**: `ps`/`kill` nativos (BSD userland — el ProcessMonitor ya es portable a BSD ps).

### Windows
- **Paquetes**: `WindowsAdapter` con detección en orden winget → scoop → choco (`winget search/install/uninstall`, `scoop install`, `choco`).
- **Procesos**: `tasklist`/`taskkill` (y PowerShell `Get-Process`) detrás del mismo ProcessMonitor.
- **Entorno**: `WindowsAdapter` — personalización vía registro (`HKCU\Software\Microsoft\Windows\CurrentVersion\Themes`), wallpaper vía `win32` API, terminal Windows.
- **Requisito**: textual corre en Windows Terminal; la TUI debe validar capacidades de consola.

Criterios de salida: se definirán al promover la fase; primer objetivo es Alfa-equivalente (paquetes + procesos) en cada SO.
