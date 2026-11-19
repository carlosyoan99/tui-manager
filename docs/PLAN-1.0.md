# PLAN-1.0 — Barrera de estabilidad

> **Estado:** plan del Arquitecto · **Versión objetivo:** `1.0.0`.
> **Repo:** commit base `bb57ceb` (Beta 3) · suite base 283 tests verdes.
> **Regla del usuario (2026-11-19):** *no se cierra hasta que se pruebe en todos
> los equipos disponibles*: esta notebook (CachyOS), `ssh laptop` (CachyOS),
> `ssh void` (Void Linux) y `ssh movil` (Termux/Android).

---

## 1. Los 15 criterios (del roadmap) y su estado

| # | Criterio | Estado |
|---|---|---|
| 1 | 6 menús principales completos | ✅ cubierto en alfas |
| 2 | Pack de temas terminal+GTK/Qt+bar+wallpaper | ⬜ verificar en WMs reales |
| 3 | Degradación elegante sin funciones rotas | ✅ verificado en Termux |
| 4 | ≥5 distros Linux + FreeBSD | ⬜ FreeBSD no ejecutado aún |
| 5 | ≥3 WMs tiling, ≥1 apilable, ≥2 DEs | ⬜ documentado, no ejecutado |
| 6 | TTY + Termux limitado | ✅ Termux verificado |
| 7 | ≥80 % cobertura en `core`; CI Linux+FreeBSD | ⬜ **medir cobertura** |
| 8 | Sesión 2 h sin traceback en 2 plataformas | ⬜ **ejecutar prueba prolongada** |
| 9 | Backups previos reversibles | ✅ `.bak-tm` verificado en B2-3 |
| 10 | Arranque < 2 s | ✅ medido 160–186 ms |
| 11 | Refresco < 500 ms, listas paginadas | ✅ medido 66.7 ms / 5000 paquetes |
| 12 | Confirmación + auditoría destructiva | ✅ B2-1 |
| 13 | Sin credenciales en claro | ✅ sanitización en auditoría |
| 14 | Docs sin funcionalidades fantasma | ✅ B2-4/B3-4 |
| 15 | `--doctor` autodiagnostica y señala el fix | ⬜ **solo informa, no sugiere** |

**Pendientes reales: #2, #4, #5, #7, #8, #15 — más la regla multi-equipo.**

---

## 2. Subtareas (paralelas, archivos separados)

### R1-1 — Cobertura ≥80 % en `core` · ~2 h
- **Archivos:** `tests/test_coverage.py` (nuevo), `tests/conftest.py`, `pyproject.toml` o `.coveragerc` (nuevo).
- Medir con `pytest --cov=tui_manager.core --cov-report=term-missing`; agregar tests hasta ≥80 %.

### R1-2 — `--doctor` con sugerencia de fix · ~1,5 h
- **Archivos:** `tui_manager/main.py`, `tests/test_cli.py`.
- Cada `[AVISO]` debe incluir una acción concreta (ej. "instalar textual: pip install textual"). Sin comandos de red ni ejecución.

### R1-3 — Prueba prolongada y multi-equipo · ~2 h
- **Archivos:** `tests/soak.py` (nuevo), `docs/QA-REPORT.md`, `tests/manual-checklist.md`.
- Bucle de 2 h con operaciones de solo lectura sobre los 4 hosts; registrar tracebacks. Reporte por host.

### R1-4 — Cierre y versión 1.0 · ~1 h
- **Archivos:** `CHANGELOG.md`, `README.md`, `docs/QA-REPORT.md`, `tui_manager/__init__.py`, `setup.py`.
- Solo si TODOS los equipos pasan y los 15 criterios están en ✅.

---

## 3. Orden de ejecución

1. Copiar repo a los 4 hosts y verificar dependencias (**en curso**: móvil ✅ 283 tests; laptop/void instalando).
2. Correr suite completa en laptop y void.
3. Ejecutar R1-1 y R1-2 en paralelo en esta notebook.
4. Ejecutar R1-3 (prueba prolongada) en los 4 hosts.
5. R1-4: cerrar 1.0 **solo si** todo pasa.

---

## 4. Reglas

Sin publicar, enviar, borrar, push ni cambios fuera del proyecto sin permiso. La red está autorizada para copiar/testear en los hosts. `notify-send`, `fwupdmgr` y builds no se ejecutan. **Si un host falla, 1.0 NO se cierra**: se documenta y se corrige.
