# Roadmap — TUI Manager

Plan por fases: alfas → betas → 1.0 estable. Cada fase tiene **criterios de salida verificables**; una fase no se cierra hasta cumplirlos todos.

Leyenda de investigación previa (fuentes):
- **[OM]** Comportamiento real de Omarchy, verificado en su repo (`bin/omarchy-*`, ~250 scripts) y manual.
- **[ENV]** Detección e integración de DE/WM: variables de sesión (`XDG_CURRENT_DESKTOP`, `WAYLAND_DISPLAY`, `HYPRLAND_INSTANCE_SIGNATURE`, `SWAYSOCK`, `I3SOCK`, `DESKTOP_SESSION`) y CLIs (`hyprctl`, `swaymsg`, `i3-msg`, `gsettings`, `xfconf4`, `kdeglobals`).
- **[BSD]** FreeBSD `pkg` (install/search/info/autoremove) y `doas`/sudo.
- **[TERMUX]** Termux/Android (soporte limitado): `PREFIX`/`TERMUX_VERSION` para detección, `pkg` como envoltorio de apt con repos propios, sin elevación de privilegios, `ps` restringido por Android a procesos propios.
- **[THEME]** Theming unificado: la paleta se aplica por superficie (terminal, GTK vía gsettings/xsettings, Qt vía qt5ct/kdeglobals, bar vía waybar/polybar style, wallpaper) — mismo enfoque de los packs de tema de Omarchy [OM].

---

## Fase Alfa 1 — `0.1.x` «Núcleo usable» *(actual)*

**Objetivo**: la TUI existe y hace bien tres cosas: paquetes, procesos, temas internos. Sin adaptadores de entorno todavía.

Trabajo:
- [ ] Implementar la capa UI con textual: `ScreenManager`, `MainMenuScreen`, `PackageManagerScreen`, `ProcessMonitorScreen`, `SettingsScreen`, `HelpScreen` (main.py ya los importa — hoy el arranque falla).
- [ ] `config/default.yaml` + directorio `config/` real (hoy referenciado pero ausente).
- [ ] Conectar `PackageManager` + adapters existentes a las pantallas.
- [ ] Conectar `ProcessMonitor` (listar, filtrar, kill con confirmación, renice).
- [ ] Temas internos de la TUI (dark/light/retro ya en `theme_manager.py`).
- [ ] Detección de SO con aviso de "no soportado" ya existente en `main.py`.
- [ ] Corregir `requirements.txt`: elegir **un** framework TUI (ver decisión pendiente), mover lo demás a extras opcionales.
- [ ] `tui-manager --version`, `--doctor` (diagnóstico de entorno).
- [ ] Soporte Termux/Android en Alfa 1 [TERMUX]: `TermuxAdapter` (apt del prefix), detección de Termux, sin elevación — el entorno actual de desarrollo sirve de banco de pruebas continuo.
- [ ] Primeros tests: adapters con subproceso simulado (mocks), distribución, config.

**Criterios de salida (todos):**
1. `tui-manager` arranca sin excepciones en Debian/Ubuntu, Arch reales **y Termux/Android**.
2. Instalar y desinstalar un paquete trivial, y matar un proceso, funcionan de punta a punta por UI.
3. Cero traceback no manejado en 30 min de uso continuo.
4. `--doctor` reporta SO, gestor de paquetes, entorno detectado, perms sudo/doas.
5. Cobertura de tests del core ≥ 60 %.

---

## Fase Alfa 2 — `0.2.x` «Plano de entorno» 

**Objetivo**: introducir el **EnvironmentAdapter** y el menú **Sistema**; soporte BSD.

Trabajo:
- [ ] `core/environment.py`: `EnvironmentDetector` (variables de sesión + CLIs) y jerarquía `EnvironmentAdapter` con **modelo de capacidades** (cada adaptador declara qué sabe hacer: `reload_config`, `set_gaps`, `set_wallpaper`, `toggle_bar`, `set_keybind`, `lock_screen`, `set_dark_mode`…).
- [ ] `HyprlandAdapter` (hyprctl), `SwayAdapter` (swaymsg), `I3Adapter` (i3-msg), `BspwmAdapter` (bspc), `NullAdapter` (TTY/DE sin CLI) [ENV].
- [ ] `KDEAdapter`/`GNOMEAdapter`/`XFCEAdapter` de superficie parcial (gsettings, kdeglobals, xfconf4) [ENV].
- [ ] Menú **Sistema**: bloquear, salir, reiniciar, apagar, idle, notificaciones, brillo, perfiles de energía, zona horaria [OM].
- [ ] Degradación elegante: entrada de menú deshabilitada + motivo cuando la capacidad no existe.
- [ ] `FreeBSDAdapter` de paquetes (`pkg`) + soporte `doas` además de sudo [BSD].
- [ ] Detección de NetBSD/OpenBSD (pkgsrc/pkg_add) como adaptador experimental.
- [ ] Backups automáticos antes de modificar configs del WM (`archivo.bak-tm`).

**Criterios de salida:**
1. En Hyprland y en i3 reales: gaps y wallpaper conmutables desde el menú Sistema/Temas con backup previo.
2. En un DE (XFCE o KDE): lo no soportado se muestra deshabilitado con motivo, sin errores.
3. En TTY: la app funciona completa salvo menú Sistema/Temas (básico).
4. En FreeBSD: instalar/desinstalar vía `pkg` funciona; sudo y doas ambos soportados.
5. Ninguna escritura a config de terceros sin `.bak-tm` en el mismo paso.

---

## Fase Beta 1 — `0.3.x` «Temas Omarchy-like»

**Objetivo**: el momento insignia: elegir un tema y cambiar todo a la vez [OM][THEME].

Trabajo:
- [ ] **Packs de temas** en YAML (estilo Omarchy: paleta + wallpaper + overrides por superficie) y directorio `config/themes/` con 5–8 packs (Catppuccin, Gruvbox, Tokyo Night, Nord, Everforest…) [OM].
- [ ] `ThemeManager` ampliado: aplica la paleta por superficie según capacidades del entorno — terminal (alacritty/foot/kitty), GTK claro/oscuro, Qt, bar (waybar/polybar), wallpaper.
- [ ] Wallpaper: siguiente/anterior/aleatorio del pack [OM].
- [ ] Toggle claro/oscuro global.
- [ ] Instalación/remoción de packs de temas desde el propio menú (carpeta local + URL).
- [ ] Menú **Actualizar** completo: disponibles, actualizar sistema, huérfanos, caché [OM].
- [ ] Snapshots de configuración propia (backup/restore de `~/.config/tui-manager`).
- [ ] Paginación y caché de listas largas de paquetes; refresco asíncrono de procesos (no bloquea la UI).

**Criterios de salida:**
1. En Hyprland + terminal soportado: cambiar de tema aplica paleta a terminal + GTK + bar + wallpaper en una sola acción y es reversible.
2. Los 5 packs incluidos aplican sin errores en al menos 2 WMs distintos.
3. Actualizar sistema y limpiar huérfanos funcionan en Debian, Arch y FreeBSD.
4. Lista de 5 000+ paquetes navegable sin bloqueo perceptible (< 500 ms por refresco).
5. Cobertura de tests del core ≥ 75 %.

---

## Fase Beta 2 — `0.4.x` «Pulido y portabilidad»

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
