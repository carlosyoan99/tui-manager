# PLAN-BETA1 — Pulido e integración (0.5.x)

> **Estado:** propuesto por el Arquitecto · inicio del equipo de 4 agentes.
> **Repo:** `/home/carlosyoan/Documents/Projects/TUI-Manager` · commit base `18bbde7`.
> **Versión actual:** 0.3.0-alpha.3 → objetivo `0.5.0-beta.1`.
> **Suite base:** 158 tests verdes · catálogo: 179 apps / 29 categorías.
> **Regla:** no se añaden funciones nuevas; solo pulido, integración y corrección (según `docs/ROADMAP.md`, línea 121).

---

## 1. Objetivo y criterios de salida (del roadmap, líneas 131–134)

1. Sesión de prueba guiada (checklist) sin errores ni estados confusos en Debian, Arch, FreeBSD y Termux.
2. Toda acción destructiva pasa por confirmación y deja rastro en el log.
3. Ninguna pantalla bloquea la UI más de 500 ms.

---

## 2. Subtareas (archivos separados → ejecutables en paralelo)

### B1-1 — Corrección de parsers reales (Debian / Arch / Void / Termux) · ~2 h

- **Archivos:** `tui_manager/core/*_adapter.py`, `tests/test_adapters.py`.
- **Objetivo:** extender el fix de localización de `ArchAdapter` (ya hecho para `pacman -Qi` en español) a los adapters con salidas localizadas o formatos reales no cubiertos: `DebianAdapter` (`apt list --installed`), `VoidAdapter` (`xbps-query -l`) y `TermuxAdapter` (`pkg list-installed`).
- **Criterio:** tests con salidas canned reales; 0 llamadas a subprocess no simuladas; `pytest -q tests/test_adapters.py` en 0 fallos.
- **Agente:** Implementador de código de sistema.

### B1-2 — Integración entre pantallas y estados vacíos · ~2 h

- **Archivos:** `tui_manager/ui/screens.py`, `tui_manager/ui/app.tcss` (solo estos).
- **Objetivo:** flujo coherente instalar → recargar lista → notify; estados vacíos uniformes ("sin resultados", "sin fuentes", "sin paquetes") en todas las tablas/listas; mismos márgenes y jerarquía visual.
- **Criterio:** tests UI con fakes: instalación recarga la tabla; lista vacía muestra mensaje; `pytest -q tests/test_ui.py` en 0 fallos.
- **Agente:** Implementador de UI.

### B1-3 — Errores accionables y ayuda contextual · ~1,5 h

- **Archivos:** `docs/USAGE.md`, `docs/API.md`, `tests/manual-checklist.md` (solo estos).
- **Objetivo:** checklist de sesión guiada por pantalla (criterio 1), documentar que ninguna acción muestra traceback y que toda acción destructiva pide confirmación y deja log (criterio 2), y medir tiempo de respuesta objetivo <500 ms (criterio 3).
- **Criterio:** `tests/manual-checklist.md` existe y cubre las 10 pantallas del menú; docs sin afirmaciones falsas sobre el estado.
- **Agente:** Documentador / curador de prompts (nuevo en Beta 1).

### B1-4 — Verificación y cierre · ~1 h

- **Archivos:** solo lectura + `docs/QA-REPORT.md` al final.
- **Objetivo:** suite completa, smoke de TUI, `--doctor`, verificar que no haya tracebacks en acciones fallidas simuladas.
- **Criterio:** 158+ tests verdes, veredicto ACEPTAR/RECHAZAR.
- **Agente:** Verificador.

---

## 3. Contratos de los 4 agentes

| Agente | Recibe | Entrega |
|---|---|---|
| Arquitecto | ROADMAP + estado del repo | Este plan |
| Implementador sistema | B1-1 | Commit local, diff, pytest de adapters |
| Implementador UI | B1-2 | Commit local, diff, pytest de UI |
| Documentador | B1-3 | Archivos de docs + checklist |
| Verificador | Commits de todos | `docs/QA-REPORT.md` con veredicto |

---

## 4. Reglas y riesgos

**Prohibido sin permiso explícito:** publicar, enviar, borrar, `git push`, `ssh`, `sudo`, instalar paquetes, escribir fuera del proyecto. Red solo para revisar URLs (ya autorizada).

**Riesgos:**
1. Dos agentes tocando `screens.py` → **evitado**: B1-2 es el único que lo edita.
2. Doc desalineada (pasó en Alfa 3) → **evitado**: el Documentador tiene este rol dedicado.
3. Regresión en parsers al normalizar localización → cubierta con tests canned.
4. Tiempo: la suite tarda ~8 min; el Verificador usa timeout amplio.

---

## 5. Checkpoint

```bash
cd ~/Documents/Projects/TUI-Manager
git status --short && git log --oneline -3
.venv/bin/python -m pytest -q tests/test_adapters.py tests/test_ui.py
.venv/bin/python -m tui_manager.main --version
```
