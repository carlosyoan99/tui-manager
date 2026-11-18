# PLAN-BETA3 — Rendimiento, estabilidad y experiencia (0.7.x)

> **Estado:** plan del Arquitecto, listo para ejecutar al cerrar Beta 2.
> **Objetivo:** ejecutar los criterios de rendimiento y robustez que 1.0 solo declara.
> **Regla:** no añade funciones nuevas; optimiza, estabiliza y mide.
> **Origen:** `docs/ROADMAP.md` «Fase Beta 3» (agregada 2026-11-18 a petición del usuario).

---

## 1. Criterios de salida (del roadmap)

1. Arranque < 2 s y refresco de procesos < 500 ms medidos en hardware modesto (≤ 8 GB RAM), con test automatizado de regresión.
2. Lista de 5000+ paquetes navegable con paginación y respuesta inmediata.
3. Ninguna llamada a subprocess bloquea el hilo de la UI (verificado con tests).
4. Animaciones y notificaciones degradan limpiamente si el entorno no las soporta.
5. Checklist ejecutado sin errores en ≥ 5 plataformas y ≥ 3 WMs; CI verde en Linux + FreeBSD.

---

## 2. Subtareas (archivos separados → paralelas)

### B3-1 — Medición y optimización de rendimiento · ~3 h
- **Archivos:** `tui_manager/core/perf.py` (nuevo), `tui_manager/core/package_manager.py`, `tui_manager/core/process_monitor.py`, `tests/test_perf.py` (nuevo).
- **Objetivo:** caché de `get_installed_packages()` con invalidación, paginación de listas (ventana de filas), benchmarks de arranque/refresco y test de regresión <500 ms con 5000 paquetes simulados.
- **Criterio:** tests con `time.perf_counter()` y fakes; sin subprocess reales.

### B3-2 — Procesos en segundo plano y no bloqueantes · ~2 h
- **Archivos:** `tui_manager/ui/app.py`, `tui_manager/ui/screens.py`, `tests/test_ui.py`.
- **Objetivo:** todo I/O largo ya corre en `@work(thread=True)`; auditar que ningún handler síncrono llame a subprocess; sondeo de procesos pausable y con intervalo configurable.
- **Criterio:** test que falla si un handler directo invoca `subprocess.run`.

### B3-3 — Animaciones, progreso y notificaciones nativas · ~2 h
- **Archivos:** `tui_manager/ui/notifications.py` (nuevo), `tui_manager/ui/screens.py`, `tests/test_notifications.py` (nuevo).
- **Objetivo:** `notify-send` si existe, fallback a notify de textual; `LoadingIndicator` en toda acción con I/O; transiciones suaves; respeto a `prefers-reduced-motion` (variable de entorno).
- **Criterio:** tests con `shutil.which` mockeado; 0 subprocess cuando la herramienta no existe.

### B3-4 — Estabilidad multiplataforma y CI · ~2 h
- **Archivos:** `.github/workflows/ci.yml` (nuevo), `tests/manual-checklist.md`, `docs/INSTALL.md`.
- **Objetivo:** CI en Linux + FreeBSD; checklist ampliado con mediciones; matriz de distros/WMs documentada.
- **Criterio:** workflow sintácticamente válido; checklist con casillas de rendimiento.

### B3-5 — Verificación y cierre
- Suite completa, smoke, medición real de arranque en esta notebook, veredicto en `docs/QA-REPORT.md`.

---

## 3. Reglas

Prohibido sin permiso: publicar, enviar, borrar, `git push`, `ssh`, `sudo`, instalar paquetes, escribir fuera del proyecto. Las notificaciones nativas solo se **detectan**, nunca se instalan. Ningún test debe medir tiempo real contra subprocess reales.

**Riesgo principal:** optimizar sin medir. Por eso B3-1 entrega benchmarks antes de tocar código de producción.
