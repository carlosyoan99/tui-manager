# PLAN-ALFA3 — Cierre de Alfa 3: fuentes alternativas seguras y verificables

> **Estado:** propuesto por el Arquitecto — Día 1 del equipo de 3 agentes.
> **Repo:** `/home/carlosyoan/Documents/Projects/TUI-Manager` · rama `main` · commit base `5e986c1`.
> **Versión:** 0.3.0-alpha.3 · **Suite base:** 137 tests verdes.
> **Supervisión:** Carlos (Python + Linux/shell), 1–2 h/día. Aprueba el plan y el veredicto de QA.

---

## 1. Objetivo

Cerrar Alfa 3 endureciendo `tui_manager/core/alternative_sources.py`, que hoy cumple su
función pero tiene tres huecos concretos (verificados leyendo el código):

| # | Hueco | Evidencia en el código |
|---|---|---|
| H1 | `get_available_tools()` usa `subprocess.run(['which', ...])` y marca `repo` siempre como `True`, aunque el gestor no exista. | `alternative_sources.py`: `tool_available()` y `get_available_tools()` |
| H2 | `_execute_install()` corre con `capture_output=False` y hace `print(...)`: sin log estructurado, sin timeout, sin control de salida. | `alternative_sources.py`: `_execute_install()` |
| H3 | `_build_command('appimage')` inventa una URL (`.../releases/latest/download/appimage`) que no existe; no hay rollback ni resultado tipado, solo `bool`. | `alternative_sources.py`: `_build_command()` e `install()` |

**No es objetivo:** cambiar de framework, tocar la TUI salvo lo mínimo para mostrar el
resultado, ni instalar nada de verdad en el sistema.

---

## 2. Subtareas

### ST-1 — Validación de herramientas y de comandos ofrecidos · ~1 h

- **Objetivo:** que solo se ofrezcan fuentes realmente instalables y con comandos válidos.
- **Archivos:** `tui_manager/core/alternative_sources.py`, `tests/test_sources.py`.
- **Cambios esperados:**
  - `tool_available()` → `shutil.which(tool)` (mockeable, sin subprocess).
  - `repo` se resuelve con el gestor real de la distro (`DistributionDetector.get_package_manager()`),
    no con `True` fijo.
  - `_build_command('appimage')` deja de inventar URLs: si `app.identifiers['appimage']`
    no empieza por `http`, la fuente se descarta en `validate_sources()`.
  - Nueva `validate_sources(sources) -> List[InstallSource]`, usada por `build_sources()`.
- **Criterio de aceptación (pytest):**
  - Con `shutil.which` mockeado, `build_sources()` hace **0** llamadas a `subprocess.run`.
  - Un AppImage con identificador no-URL **no aparece** en las fuentes.
  - `git` sin `git`/`curl` en el PATH **no ofrece** fuente `github`.
- **Verificación:** `pytest -q tests/test_sources.py` → 0 fallos (≥ 12 tests base + nuevos).

### ST-2 — Ejecución segura y logging estructurado · ~1,5 h

- **Objetivo:** ejecutar con captura y timeout, y dejar rastro auditable sin ruido.
- **Archivos:** `tui_manager/core/alternative_sources.py`, `utils/logger.py` (solo si hace falta), `tests/test_sources.py`.
- **Cambios esperados:**
  - `subprocess.run(command, capture_output=True, text=True, timeout=…)`.
  - `logger.info` / `logger.error` con `extra` o formato fijo:
    `app`, `source`, `returncode`, `duracion_ms`, `exit_code`.
  - Los `print()` de producción se sustituyen por mensajes que la TUI ya sabe mostrar
    (o por `logger`). like `stderr` se acota a las últimas ~20 líneas.
  - Normalizar `Requires_sudo` → `requires_sudo` (mantener alias temporal si hay callers).
- **Criterio de aceptación (pytest):**
  - Con `FakeRunner` (ver `tests/conftest.py`), `_execute_install()` llama a
    `subprocess.run` con `capture_output=True` y un `timeout` explícito.
  - Se emite un log de éxito y uno de fallo con los 4 campos anteriores.
  - No queda ningún `print(` nuevo en `alternative_sources.py`.
- **Verificación:** `grep -n 'print(' alternative_sources.py` → solo los callbacks de consola
  permitidos; `pytest -q tests/test_sources.py` → 0 fallos.

### ST-3 — Resultado tipado y rollback mínimo · ~1,5 h

- **Objetivo:** saber exactamente qué pasó y deshacer solo lo que el propio comando creó.
- **Archivos:** `tui_manager/core/alternative_sources.py`, `tui_manager/core/sources_adapter.py`,
  `tui_manager/ui/screens.py` (solo `AppsScreen._do_install`), `tests/test_sources.py`, `tests/test_ui.py`.
- **Cambios esperados:**
  - `InstallResult` (dataclass) con `ok`, `app`, `source`, `returncode`, `actions`, `error`.
  - `__bool__` para que los callers actuales (`if ok:`) sigan funcionando sin cambios.
  - `actions` registra los pasos ejecutados; el rollback **nunca borra** archivos del usuario:
    solo revierte lo creado por el propio comando (ej. directorio de `git clone` creado en esta sesión).
  - `AppsScreen` muestra `result.error` cuando falla.
- **Criterio de aceptación (pytest):**
  - Fallo simulado en cada una de las 5 fuentes → `InstallResult.ok is False`,
    `error` no vacío, `returncode` correcto.
  - Éxito → `actions` con al menos 1 entrada y `ok is True`.
  - `tests/test_ui.py` sigue en 0 fallos (el `__bool__` evita romper la TUI).
- **Verificación:** suite completa → 0 fallos (137 base + nuevos).

### ST-4 — Documentación y cierre de trazabilidad · ~1 h

- **Objetivo:** que el repo cuente qué cambió y que el roadmap no contradiga la realidad.
- **Archivos:** `CHANGELOG.md`, `docs/USAGE.md`, `docs/ROADMAP.md`, `docs/QA-REPORT.md`.
- **Cambios esperados:**
  - CHANGELOG: entrada de cierre de Alfa 3 con los 3 huecos resueltos.
  - USAGE: explicar `preferred_install_method` y el aviso de fuentes externas.
  - ROADMAP: **decisión pendiente de Carlos** — el catálogo ya se entregó en `0.3.x`
    pero el roadmap lo lista en Alfa 4 (líneas 94–106). Alinear o anotar el desfase.
  - `docs/QA-REPORT.md`: veredicto final del Verificador.
- **Criterio de aceptación:**
  - `pytest -q` → 0 fallos; `py_compile` de todos los `.py` tocados → OK.
  - Smoke headless: menú `[1]`–`[9]`/`[0]`, Acerca de con SOFTWARE/HARDWARE,
    Ajustes con las 3 ayudas, `--version` y `--doctor` sin errores.
  - `git status --short` sin archivos fuera del proyecto.

---

## 3. Contratos de entrada / salida

### Implementador (Agente 2)

| | Contenido |
|---|---|
| **Recibe** | De Carlos: número de subtarea (`ST-1`…`ST-4`) + este PLAN + los archivos listados. |
| **Entrega** | ① commit **local** (sin push), ② diff, ③ salida final de `pytest -q`, ④ lista de archivos tocados, ⑤ nota explícita: *"sin red, sin sudo, sin escribir fuera del proyecto"*. |
| **No hace** | No elige otra subtarea, no instala, no borra, no hace push/ssh, no toca `~`. |

### Verificador (Agente 3)

| | Contenido |
|---|---|
| **Recibe** | Hash del commit del Implementador + los criterios de la subtarea (este PLAN). |
| **Entrega** | `docs/QA-REPORT.md` con tabla (subtarea / tests / py_compile / smoke / regresiones / estado), bugs con severidad y veredicto **ACEPTAR** o **RECHAZAR**. |
| **No hace** | No modifica código, no borra, no publica, no envía, no ejecuta red/sudo. |

### Carlos (dueño del producto)

| | Contenido |
|---|---|
| **Recibe** | El PLAN (este archivo), el diff diario y el QA report. |
| **Decide** | Aprueba el plan, elige la subtarea del día y acepta o rechaza el veredicto. 5–15 min/día. |

---

## 4. Firmas esperadas de las funciones nuevas

```python
# tui_manager/core/alternative_sources.py
from dataclasses import dataclass

@dataclass(frozen=True)
class InstallResult:
    ok: bool
    app: str
    source: str
    returncode: int
    actions: tuple = ()
    error: str = ""

    def __bool__(self) -> bool:      # compatibilidad con callers actuales
        return self.ok


class AlternativeSourceManager:
    def tool_available(self, tool: str) -> bool: ...          # shutil.which
    def get_available_tools(self) -> Dict[str, bool]: ...     # repo = gestor real
    def validate_sources(self, sources: List[InstallSource]) -> List[InstallSource]: ...
    def _execute_install(self, app: AppEntry,
                         source: InstallSource) -> InstallResult: ...   # antes -> bool
    def install(self, app: AppEntry,
                package_installed: bool = False) -> InstallResult: ...  # antes -> bool
```

`InstallSource.requires_sudo` (minúscula) reemplaza a `Requires_sudo`; si otro módulo lo
usa, se conserva un alias de solo lectura durante esta alfa.

---

## 5. Riesgos y prohibiciones

**Prohibido para los 3 agentes (sin permiso explícito de Carlos):**
- Publicar, enviar, borrar, hacer `git push`, `ssh movil` ni ningún comando de red.
- Instalar paquetes, `sudo`, `pip install`.
- Escribir fuera de `/home/carlosyoan/Documents/Projects/TUI-Manager/`.
- Ejecutar instalaciones reales en tests: siempre `FakeRunner` / `monkeypatch`.

**Riesgos concretos:**
1. **Falsa disponibilidad:** si `repo` sigue siendo `True` fijo, la TUI ofrecerá `apt`
   en un sistema sin `apt`. → cubierto por ST-1.
2. **URL inventada:** el AppImage actual apunta a un path inexistente. → ST-1.
3. **Regresión silenciosa:** cambiar `bool` por `InstallResult` puede romper
   `AppsScreen._do_install`. → `__bool__` en ST-3 + test UI.
4. **Rename de `Requires_sudo`:** buscar todos los usos antes de renombrar. → ST-2.
5. **Desalineación de roadmap:** catálogo en `0.3.x` vs Alfa 4. → decisión de Carlos en ST-4.
6. **Tiempo:** 1–2 h/día no alcanza para 2 subtareas el mismo día; el plan asume **1 subtarea/día**.

---

## 6. Checkpoint diario (lo ejecuta Carlos)

```bash
cd ~/Documents/Projects/TUI-Manager
git status --short
git log --oneline -3
.venv/bin/python -m pytest -q
.venv/bin/python -m tui_manager.main --version
```

**Señal de éxito del día:** un commit local nuevo, `pytest -q` en 0 fallos y un
`docs/QA-REPORT.md` actualizado con veredicto explícito.
**Señal de alerta:** cualquier cambio fuera del proyecto, comando de red, o veredicto
RECHAZAR sin corrección al día siguiente.
