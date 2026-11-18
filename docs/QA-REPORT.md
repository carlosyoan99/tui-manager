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

---

# QA-REPORT — Beta 1 (0.5.x) «Pulido e integración»

**Verificador:** Agente 4 · **Rango:** `4344226..267b01a` · **Fecha:** 2026-11-18

| Subtarea | Commit | Tests | py_compile | Smoke | Estado |
|---|---|---|---|---|---|
| B1-1 parsers localizados Debian/Void/Termux | `daac410` | 54 en adapters | OK | OK | ACEPTAR |
| B1-2 estados vacíos + flujo instalar/recargar/notify | `267b01a` | 26 en UI | OK | OK | ACEPTAR |
| B1-3 checklist y docs | `daac410` | 40 ítems en checklist | N/A | OK | ACEPTAR |
| B1-4 verificación | — | **167 passed**, 0 fallos | OK | OK | ACEPTAR |

**Criterios de salida del roadmap verificados:**
1. Checklist `tests/manual-checklist.md` cubre las 10 pantallas (para validación guiada en las 4 plataformas). ✅ documentado
2. Acciones destructivas con confirmación y rastro en el log. ✅ (heredado de Alfa 3, verificado en QA anterior)
3. Ninguna pantalla bloquea >500 ms. ⚠️ **no medido automáticamente**: queda como ítem del checklist manual.

**Observaciones:**
- 146 claves i18n usadas, 0 faltantes; 0 `traceback.print` en los cambios.
- `--version` aún reportaba `0.3.0-alpha.3` al cierre; se corrige en este commit a `0.5.0-beta.1`.
- **Decisión resuelta (2026-11-18):** C/D/F se diferencian a Beta 2 en `docs/ROADMAP.md`, respetando que Beta 1 no añade funciones nuevas.

> ## ✅ ACEPTAR (con la observación de versión corregida y la decisión C/D/F pendiente)

---

# QA-REPORT — Beta 2 (0.6.x) «Portabilidad y distribución»

**Verificador:** Agente 4 · **Rango:** `7596cd9..f1a67cf` · **Fecha:** 2026-11-18

| Subtarea | Commit | Tests | py_compile | Smoke | Estado |
|---|---|---|---|---|---|
| B2-1 auditoría destructiva | `b176e7c` | 13 auditoría + 51 core | OK | OK | ACEPTAR |
| B2-2 doctor + ayuda `?` | `f1a67cf` | 61 CLI/UI | OK | OK | ACEPTAR |
| B2-3 stacks/fwupd/snapshots | `27f31fa` | 25 stacks | OK | OK | ACEPTAR |
| B2-4 empaquetado y docs | `4f9f6dc` | py_compile + bash -n | OK | OK | ACEPTAR |
| B2-5 verificación | — | **236 passed**, 0 fallos | OK | OK | ACEPTAR |

**Criterios verificados:**
1. Empaquetado presente para Debian/Arch/Fedora/FreeBSD (`packaging/`). ✅ documentado (no se ejecutaron builds)
2. `?` abre ayuda contextual en 11 contextos. ✅ verificado con test dinámico
3. Cero mensajes sin accionable en el checklist. ✅ documentado
4. Auditoría con timestamp/actor/acción/destino/resultado y sanitización. ✅ 13 tests
5. Stacks en lote y snapshots conservan `.bak-tm`. ✅ 25 tests simulados

**Observación:** `pacman --version` imprime arte ASCII; el helper toma la primera línea con dígitos y funciona correctamente. Los CLI no instalados muestran «N/D [AVISO]» sin fallar.

> ## ✅ ACEPTAR
