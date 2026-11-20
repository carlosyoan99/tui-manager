# PLAN — Betas previas a 2.0

> **Estado:** propuesto · **Objetivo:** validar en campo antes del release 2.0 (macOS/Windows).
> **Regla del usuario:** no se declara 2.0 sin pasar por betas de prueba.
> **Origen:** peticiones 2026-11/20 (mouse/táctil en modales, sudo con contraseña) + ROADMAP 2.0.

---

## 1. Versiones beta

| Beta | Versión | Contenido | Plataformas de prueba |
|---|---|---|---|
| **Beta A** | `2.0.0-beta.1` | Accesibilidad mouse/táctil + elevación sudo correcta | 4 hosts (3 laptops + Termux) |
| **Beta B** | `2.0.0-beta.2` | macOS (Homebrew/defaults/osascript) simulado + Windows (winget/scoop/tasklist) simulado | tests multi-SO simulados |
| **Beta C** | `2.0.0-beta.3` | Integración final, docs 2.0, correcciones de campo | 4 hosts + simulación |
| 2.0 final | `2.0.0` | Solo si las 3 betas pasan | — |

---

## 2. Beta A — subtareas (lo que pediste ahora)

### 2.0-A1 — Modales compatibles con mouse y pantalla táctil
- **Archivos:** `tui_manager/ui/screens.py`, `tui_manager/ui/app.tcss`, `tests/test_ui.py`.
- **Qué:** los modales dejan de depender solo de atajos:
  - `ConfirmScreen`: botones **Sí / No** clicables (textual `Button`) además de `y/n/Esc`.
  - `InputScreen`: botones **Aceptar / Cancelar** además de `Enter/Esc`.
  - `SelectScreen`: lista ya clicable por `ListView`, pero añadir botón **Cancelar**.
  - Foco inicial en el botón primario; `Tab` alterna; clic funciona con mouse y táctil.
- **Criterio:** test que simula clic en cada botón y verifica el `dismiss`; atajos siguen funcionando.

### 2.0-A2 — Otras características con el mismo problema (auditoría táctil)
- **Archivos:** mismos de A1.
- **Qué identifiqué y cubro:**
  - Marcado múltiple con `Espacio` → añadir **clic en la columna «Marcar»** de la tabla.
  - Orden de procesos solo con `s` → añadir **Select compacto de orden** clicable.
  - Ayuda solo con `?` → añadir **botón `?`** en la barra de cada pantalla.
  - «Volver» solo con `Esc` → botón **← Volver** en pantallas con teclado/táctil.
  - Confirmaciones de acciones por lote → mismo `ConfirmScreen` con botones.
- **Criterio:** test de que cada acción tiene al menos un control clicable.

### 2.0-A3 — sudo con petición de contraseña funcional
- **Archivos:** `tui_manager/core/package_adapter.py`, `tui_manager/ui/app.py`, `tui_manager/main.py`, `tests/test_sudo.py` (nuevo).
- **Problema real:** `subprocess.run(..., capture_output=True)` captura stdout/stderr, así que **sudo no tiene TTY donde mostrar el prompt** y la operación falla o cuelga sin pedir contraseña.
- **Solución (segura, sin guardar credenciales):**
  1. Si `os.geteuid()==0` → ejecutar sin sudo.
  2. Si no, detectar `sudo -n true` (credenciales cacheadas) → ejecutar con `sudo -n`.
  3. Si no hay caché, **suspender la TUI** (`App.suspend()`) y ejecutar `sudo -v` en el TTY real para que el usuario escriba su contraseña; luego reanudar y reintentar.
  4. Si se cancela o falla → mensaje accionable, nunca traceback. Nunca se guarda ni se pasa la contraseña por argumento.
  5. Soporte `doas` en BSD con el mismo patrón.
- **Criterio:** tests simulados del flujo (sin sudo real); verificación manual en los 4 hosts.

### 2.0-A4 — Cierre Beta A
- Suite en 4 hosts, versión `2.0.0-beta.1`, CHANGELOG/QA, verificación manual de clic y sudo.

---

## 3. Reglas

Sin publicar, enviar, borrar, push ni red salvo la autorizada. `sudo -v` se ejecuta solo con consentimiento del usuario y en el TTY real. La contraseña nunca se almacena ni se registra.
