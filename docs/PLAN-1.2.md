# PLAN-1.2 — Onboarding, datos para scripts y comunidad

> **Estado:** propuesto · **Versión objetivo:** `1.2.0`.
> **Repo:** commit base `0c0b9d6` (1.1.0 publicada) · 361 tests · 4 hosts en verde.
> **Origen:** `docs/INVESTIGACION-MERCADO.md` §2–4.
> **Regla:** mantener 361 tests en los 4 hosts antes de cerrar.
> **Permisos:** CI ejecutada en GitHub y publicación requieren OK explícito; no se hacen aquí.

---

## 1. Subtareas (paralelas, archivos separados)

### 1.2-A — `tm quickstart` (onboarding guiado) · ~2 h
- **Archivos:** `tui_manager/main.py`, `tui_manager/ui/screens.py`, `tui_manager/i18n.py`, `tests/test_cli.py`, `tests/test_ui.py`.
- Opción `--quickstart`: asistente que explica las 10 entradas y ejecuta un `--doctor` guiado.
- Criterio: tests CLI/UI en verde; sin cambiar atajos ni menú.

### 1.2-B — Salida `--json` para scripts/agentes · ~2 h
- **Archivos:** `tui_manager/main.py`, `tui_manager/cli_json.py` (nuevo), `tests/test_cli_json.py` (nuevo).
- `--json packages|processes|doctor` → JSON estructurado a stdout, sin colores; errores a stderr con exit code válido.
- Criterio: JSON válido con `jq`, sin subprocess reales en tests.

### 1.2-C — Documentación de comunidad · ~1 h
- **Archivos:** `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` (nuevos), `README.md`.
- Criterio: sin placeholders; enlaces correctos al repo `carlosyoan99/tui-manager`.

### 1.2-D — CI y demo visual · ~1 h
- **Archivos:** `.github/workflows/ci.yml`, `docs/DEMO.md` (nuevo), `README.md`.
- Añadir job de lint/compile; DEMO con comandos `vhs`/asciinema (no ejecutar).
- Criterio: YAML válido; badge en README apuntando al workflow real.

### 1.2-E — Verificación y cierre
- Suite en 4 hosts, versión `1.2.0`, CHANGELOG/QA, recopiar y testear.

---

## 2. Reglas

Sin publicar, enviar, borrar, push ni red salvo la autorizada para testear hosts. La ejecución de CI en GitHub y el push final requieren tu OK.
