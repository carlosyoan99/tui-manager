# QA-REPORT — Cierre de Alfa 3 (Día 5 del equipo)

**Verificador:** Agente 3 · **Rango revisado:** `bd83a8f..ee2e1eb` (Días 2–4)
**Fecha:** 2026-11-18 · **Repo:** `/home/carlosyoan/Documents/Projects/TUI-Manager`

---

## 1. Tabla de verificación

| Subtarea | Commit | Tests | py_compile | Smoke TUI | Regresiones | Estado |
|---|---|---|---|---|---|---|
| ST-1 validación de fuentes | `b7c3f60` | ✅ 17 en `test_sources` | ✅ | ✅ | `--version` OK | **ACEPTAR** |
| Hotfix pacman localizado + ST-2 logging | `e6db3af` | ✅ 65 en adapters+sources | ✅ | ✅ | `--doctor` OK | **ACEPTAR** |
| ST-3 `InstallResult` + rollback | `ee2e1eb` | ✅ 27 sources + 26 UI | ✅ | ✅ | menú `[1]`–`[9]`/`[0]` | **ACEPTAR** |
| **Suite completa** | — | ✅ **153 passed**, 0 fallos | ✅ | ✅ | 0.3.0-alpha.3 | **ACEPTAR** |

### Detalle de la suite final

```
153 tests collected
153 passed in ~140 s
PYTEST_EXIT=0
```

### Smoke headless (textual `run_test`)

- Menú: 10 entradas con atajo visible `[1]` … `[9]` y `[0]` para Catálogo.
- Acerca de: secciones `SOFTWARE` y `HARDWARE`, `LoadingIndicator` oculto al terminar.
- Ajustes: 3 ayudas visibles (tema, idioma, intervalo de refresco de procesos).
- `--version`: `tui-manager 0.3.0-alpha.3`.
- `--doctor`: CachyOS → ArchAdapter → SwayAdapter, capacidades y elevación OK.

### Verificación en vivo (bug reportado por Carlos)

```text
paquetes detectados: 1202
ejemplo: a52dec 0.8.0-3 | Library for decoding ATSC A/52 (AC-3) audio s
```

Antes del hotfix: **0 paquetes**. Causa: `pacman -Qi` localizado en español
(`Nombre`, `Versión`, `Descripción`, `Depende de`). Resuelto con normalización
de claves ASCII + aliases es/en.

---

## 2. Alcance y permisos

- **6 archivos tocados**, todos bajo `tui_manager/`, `tests/` y `docs/`.
- **Fuera del proyecto: ninguno.**
- Sin `git push`, `ssh`, `pip install`, `sudo` ni comandos de red en código de producción
  (verificado con `git diff bd83a8f..HEAD`).
- Sin borrados: el rollback de ST-3 solo elimina **directorios vacíos** creados por el
  propio comando; nunca toca archivos del usuario (testeado en las 5 fuentes).

---

## 3. Hallazgos

| Severidad | Hallazgo | Disposición |
|---|---|---|
| ~~ALTO~~ **RESUELTO** | 0 paquetes en CachyOS por locale español | Hotfix en `e6db3af` + test con salida canned real |
| BAJO | El smoke usa `Services(distribution='arch')` con `package_manager=None`, por eso "Paquetes: N/D" en Acerca de; en la app real con `Services.detect()` son 1202 | No es bug de código. No corregir. |
| BAJO | 8 apps del catálogo (`vivaldi`, `code`, `obsidian`, `joplin`, `keepassxc`, `bitwarden`, `lmstudio`, `anki`) dejaron de ofrecer AppImage al descartar URLs inventadas | Consecuencia esperada de ST-1. Requiere URLs reales → **permiso de red pendiente** |
| BAJO | `ROADMAP.md` lista el catálogo en Alfa 4 aunque ya se entregó en `0.3.x` | A resolver en ST-4 (Día 6), decisión de Carlos |

**Bugs bloqueantes: 0.**

---

## 4. Veredicto

> ## ✅ ACEPTAR

Los cuatro cambios cumplen sus criterios de aceptación. La suite completa pasa
(153/153), no hay regresiones, no se tocó nada fuera del proyecto y no se ejecutaron
comandos de red, sudo ni instalaciones reales. El bug funcional reportado por el
usuario (0 paquetes en CachyOS) quedó resuelto y verificado en vivo.

**Recomendación:** proceder con **ST-4 (documentación)** en el Día 6 y dejar para el
Día 7 la decisión sobre ampliar el equipo a 4–5 agentes para Beta 1.
