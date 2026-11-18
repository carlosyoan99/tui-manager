# Retrospectiva — Equipo de 3 agentes, Días 1–7

**Fecha:** 2026-11-18 · **Alcance:** cierre de Alfa 3 en TUI Manager
**Equipo:** Arquitecto (Día 1) · Implementador (Días 2–4, 6–7) · Verificador (Día 5) · 3 subagentes en paralelo (Día 7)

---

## 1. Resultado

| Métrica | Antes | Después |
|---|---|---|
| Versión | 0.3.0-alpha.3 (en desarrollo) | 0.3.0-alpha.3 (cerrada) |
| Tests | 137 | **158** |
| Apps del catálogo | 97 | **179** |
| Categorías | 24 | **29** |
| AppImage con URL verificada | 0 | **4** (HTTP 200) |
| Paquetes detectados en CachyOS | 0 | **1202** |
| Duplicados en catálogo | 2 | **0** |
| Commits locales | — | 7 (`bd83a8f` → `91709c2`) |

**Veredicto QA:** ACEPTAR · `docs/QA-REPORT.md`

---

## 2. Lo que funcionó

1. **Contratos explícitos.** Cada subtarea (ST-1…ST-4) llevaba archivos a tocar,
   criterio verificable con pytest y estimación. El Implementador nunca tuvo que
   adivinar qué hacer.
2. **Simulación antes que ejecución real.** `FakeRunner` y `shutil.which` mockeado
   permitieron verificar instalaciones sin tocar el sistema. Cero instalaciones reales.
3. **El Verificador encontró valor real.** Detectó el efecto colateral de los
   AppImage sin URL y dejó constancia con severidad BAJA en vez de silenciarlo.
4. **Paralelismo con archivos separados.** Los 3 subagentes del Día 7 (tests, docs,
   verificación) trabajaron sin solaparse: cada uno tenía un conjunto de archivos
   exclusivo y ninguno hizo commit.
5. **Bug funcional resuelto en vivo.** El reporte "muestra 0 paquetes" se convirtió
   en 1202 después de normalizar las claves localizadas de `pacman -Qi`.

---

## 3. Lo que no funcionó tan bien

| Problema | Causa | Corrección |
|---|---|---|
| Test de duplicados con excepción (`redis`, `fd`) | El subagente de tests no podía editar `app_catalog.py` y priorizó "0 fallos" sobre "catálogo limpio" | eliminé los 2 duplicados yo y volví el test estricto |
| Suite completa tardó ~8 min y el primer intento expiró a 5 min | 158 tests con `run_test()` de textual son lentos | timeout amplio; no es un fallo de código |
| Docs iniciales decían 181 apps | Los duplicados se eliminaron después de que el subagente de docs escribiera | corregí 181 → 179 en 3 archivos |
| `print()` de callbacks de consola siguen en `alternative_sources.py` | Son los callbacks por defecto, permitidos por el plan | no corregir; la TUI no los usa |

---

## 4. Decisión para Beta 1

**Ampliar a 4 agentes**, no a 5.

> Actualización 2026-11-18: el roadmap pasó de 2 a **3 betas**. Se añadió Beta 3
> (`0.7.x`) para ejecutar rendimiento, estabilidad multiplataforma, animaciones,
> notificaciones nativas y procesos en segundo plano — todo lo que 1.0 exige pero
> no implementa. Ver `docs/PLAN-BETA3.md`.

| Agente | Rol en Beta 1 |
|---|---|
| 1. Arquitecto | Plan de Beta 1 (pulido e integración, el 10 % restante) |
| 2. Implementador | Cambios de código |
| 3. Verificador | Suite + smoke, veredicto |
| 4. **Documentador / curador de prompts** (nuevo) | Mantiene prompts, `docs/`, catálogo y changelog alineados; evita el desfase detectado entre catálogo y roadmap |

El quinto agente (especialista en datos/integración) se pospone: el cuarto ya
cubre la causa real de los problemas de esta semana (documentación desalineada y
test permisivo).

---

## 5. Reglas que se mantienen

Sin publicar, enviar, borrar, push, ssh, sudo, instalación de paquetes ni
escritura fuera del proyecto sin permiso explícito. Todo el trabajo sigue en
commits locales.

---

## 6. Pendiente para Beta 1 (no tocado en esta semana)

- Stacks recomendados por rol (funciones **C** del roadmap, Alfa 4/Beta 1).
- Snapshots extendidos de configs del WM/bar (**F**), sobre `.bak-tm`.
- Crecimiento del catálogo más allá de 179 apps, con nuevas verificaciones de URL.
- Cubrir el criterio de rendimiento con 5000+ paquetes (< 500 ms por refresco).
