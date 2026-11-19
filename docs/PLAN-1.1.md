# PLAN-1.1 — Interfaz, multiselección, datos y tema dinámico

> **Estado:** propuesto · **Versión objetivo:** `1.1.0`.
> **Repo:** commit base `0970cbd` (1.0.0) · 333 tests · cobertura core 82 %.
> **Origen:** peticiones del usuario 2026-11-19. Son **reparaciones y mejoras**, no nuevas áreas de producto.
> **Regla:** mantener el contrato de 1.0 (4 hosts en verde). Todo cambio se recopia y re-testea en los 4 equipos antes de cerrar.

---

## 1. Las 6 peticiones → subtareas

### 1.1-A — Iconos y Selects compactos en la UI · ~2 h
- **Archivos:** `tui_manager/ui/screens.py`, `tui_manager/ui/app.tcss`.
- **Qué:** añadir iconos Unicode/Nerd-Font (con fallback ASCII si la fuente no los soporta) a títulos y entradas del menú; los `Select` de Ajustes dejan de ocupar todo el ancho (ancho fijo + alineación a la izquierda, `width: auto`/`max-width` en tcss).
- **Criterio:** test UI que verifica el `width` del select y que las etiquetas siguen legibles con `TERM=dumb`. Sin romper atajos ni estados vacíos.

### 1.1-B — Quitar el aviso de Termux en otros sistemas · ~0,5 h
- **Archivos:** `tui_manager/ui/screens.py` (o donde esté el `Static` de nota), `tui_manager/i18n.py`.
- **Qué:** la nota «Termux/Android: soporte limitado…» solo se muestra cuando `DistributionDetector.is_termux()` es True. En Debian/Arch/Void/BSD no aparece (o se sustituye por una nota neutra).
- **Criterio:** test parametrizado por distro: termux → nota visible; arch → nota ausente.

### 1.1-C — Selección múltiple en Aplicaciones (acciones por lote) · ~3 h
- **Archivos:** `tui_manager/ui/screens.py`, `tui_manager/ui/app.tcss`, `tests/test_ui.py`.
- **Qué:** `DataTable` con `cursor_type='cell'` o checkbox en columna; tecla `Espacio` marca/desmarca; acciones instal/remove y `StackInstaller` operan sobre la selección; confirmación única con resumen (`N paquetes`).
- **Criterio:** test con fakes: marcar 3 filas → remove se llama 3 veces y la tabla se recarga una vez; cancelar no ejecuta nada.

### 1.1-D — Ordenar procesos por usuario, memoria y alfabético · ~1,5 h
- **Archivos:** `tui_manager/ui/screens.py`, `tui_manager/i18n.py`, `tests/test_ui.py`.
- **Qué:** ampliar `_sort` de `{cpu, mem}` a `{cpu, mem, user, name, pid}`; tecla `s` cicla; etiqueta y clave i18n por criterio; dirección ascendente/descendente según criterio.
- **Criterio:** test por cada criterio con procesos falsos (usuario, nombre, memoria, PID) verificando el orden de la tabla.

### 1.1-E — Tema mutagen dinámico + aclarar alcance del tema · ~3 h
- **Archivos:** `tui_manager/ui/theme_mutagen.py` (nuevo), `tui_manager/core/config.py`, `tui_manager/ui/screens.py`, `config/default.yaml`, `docs/USAGE.md`.
- **Qué:**
  - Aclarar en Ajustes que el selector es **tema de la TUI** (no del escritorio, que lo gestiona Noctalia).
  - Nueva opción `theme_source: manual | mutagen` (default `manual`). Con `mutagen`, la TUI consulta el **mismo esquema que usa OpenCode/Noctalia** (archivo/variable de tema dinámico generado desde el wallpaper) y mapea sus colores al tema textual.
  - Respetar `prefers-reduced-motion` y el fallback al tema manual si no hay esquema.
  - Investigar el formato real de mutagen en las notebooks (ver `docs/INVESTIGACION-MERCADO.md` §5).
- **Criterio:** test con un esquema mutagen simulado → paleta textual aplicada; sin esquema → fallback manual; opción visible en Ajustes.

### 1.1-F — Acerca de estilo fastfetch · ~3 h
- **Archivos:** `tui_manager/core/sysinfo.py`, `tui_manager/ui/screens.py`, `tui_manager/i18n.py`, `tests/test_core.py`.
- **Qué:** ampliar con: versión del SO (`/etc/os-release` `VERSION`/`PRETTY_NAME`), nombre del dispositivo (`hostname` + `getprop ro.product.model` en Termux), tipo (laptop/desktop/VM/Termux vía `systemd-detect-virt`/DMI), GPU (`lspci`/`sysctl`/`ro.gpu`), gestor de paquetes, tiempo activo, pantallas (`xrandr`/`hyprctl monitors`/`swaymsg -t get_outputs`), resolución, shell, sesión, CPU, RAM, swap, disco, batería, logo ASCII del SO.
- **Criterio:** test con salidas canned de `hyprctl`, `xrandr`, `/sys/class/dmi/id` y Termux; N/D honesto cuando no hay dato; sin subprocess en la UI (va en worker).

---

## 2. Orden y verificación

1. A + B (UI pequeña, se hacen juntas) → tests UI.
2. C + D (tablas) → tests UI.
3. E (investigar mutagen antes de codificar) → tests config/UI.
4. F (sysinfo) → tests core.
5. Suite completa en la notebook → recopiar a los 4 hosts → suite + soak en los 4 → recién cerrar 1.1.

---

## 3. Reglas

Sin publicar, enviar, borrar, push ni cambios fuera del proyecto sin permiso. Red solo para revisar formatos de mutagen. Ninguna acción destructiva real en tests.
