# PLAN-BETA2 — Portabilidad, distribución y C/D/F (0.6.x)

> **Estado:** propuesto por el Arquitecto · inicio del equipo de 4 agentes.
> **Repo:** `/home/carlosyoan/Documents/Projects/TUI-Manager` · commit base `136beae`.
> **Versión:** `0.5.0-beta.1` → objetivo `0.6.0-beta.2`.
> **Suite base:** 167 tests verdes · catálogo 179 apps / 29 categorías.
> **Origen:** `docs/ROADMAP.md` líneas 138–156, más la resolución del desfase C/D/F (commit `136beae`).

---

## 1. Criterios de salida (del roadmap, líneas 162–166)

1. Instalable en Debian, Arch, Fedora y FreeBSD desde sus canales naturales, sin pasos manuales de dependencias.
2. Toda pantalla responde `?` con ayuda correcta.
3. Cero mensajes de error sin accionable en el checklist manual.
4. Auditoría registra todas las acciones destructivas con timestamp y destino.
5. Stacks por rol instalan en lote y los snapshots restauran configs conservando `.bak-tm` (simulado en Debian y Arch).

---

## 2. Subtareas (archivos separados → paralelas)

### B2-1 — Auditoría de acciones destructivas · ~2 h
- **Archivos:** `tui_manager/core/audit.py` (nuevo), `tui_manager/core/package_manager.py`, `tui_manager/core/process_monitor.py`, `tests/test_audit.py` (nuevo).
- **Objetivo:** registrar toda acción destructiva (install, remove, kill, renice, writes) con `timestamp`, `actor`, `acción`, `destino` y `resultado`. Nunca credenciales.
- **Criterio:** tests simulados verifican que cada acción registra una entrada; `pytest -q tests/test_audit.py` en 0 fallos.

### B2-2 — `--doctor` ampliado y ayuda contextual `?` · ~2 h
- **Archivos:** `tui_manager/main.py`, `tui_manager/ui/screens.py`, `tests/test_cli.py`, `tests/test_ui.py`.
- **Objetivo:** `--doctor` añade versión de CLIs (apt/pacman/dnf/pkg/xbps) y capacidades del entorno; `?` abre ayuda correcta en las 10 pantallas.
- **Criterio:** tests CLI y UI en 0 fallos; ninguna pantalla sin ayuda.

### B2-3 — C · Stacks, D · fwupd, F · Snapshots · ~3 h
- **Archivos:** `tui_manager/core/app_catalog.py`, `tui_manager/core/stacks.py` (nuevo), `tui_manager/core/snapshots.py` (nuevo), `tests/test_stacks.py` (nuevo).
- **Objetivo:** stacks por rol (dev/terminal/web) que instalan en lote vía adapters; detección de `fwupdmgr` como capacidad opcional; backup/restore de configs del WM/bar sobre `.bak-tm`, nunca snapshots de sistema.
- **Criterio:** simulado en Debian y Arch; restore devuelve exactamente el archivo previo y conserva `.bak-tm`.

### B2-4 — Empaquetado y documentación por plataforma · ~2 h
- **Archivos:** `setup.py`, `docs/INSTALL.md`, `docs/API.md`, `packaging/` (nuevo: PKGBUILD, debian/control, rpm spec, FreeBSD pkg).
- **Objetivo:** canales naturales de Debian/Arch/Fedora/FreeBSD sin pasos manuales; INSTALL por plataforma.
- **Criterio:** archivos de empaquetado presentes y sintácticamente válidos; docs sin funcionalidades fantasma.

### B2-5 — Verificación y cierre (yo, Verificador)
- Suite completa, smoke, `--version`/`--doctor`, veredicto en `docs/QA-REPORT.md`.

---

## 3. Contratos

| Agente | Entrega |
|---|---|
| Implementador sistema (B2-1) | commit local + tests de auditoría |
| Implementador UI/CLI (B2-2) | commit local + tests CLI/UI |
| Implementador catálogo (B2-3) | commit local + tests de stacks/snapshots |
| Documentador/packaging (B2-4) | commit local + archivos de empaquetado/docs |
| Verificador | QA report con veredicto |

---

## 4. Reglas

Prohibido sin permiso: publicar, enviar, borrar, `git push`, `ssh`, `sudo`, instalar paquetes, escribir fuera del proyecto. Red solo para revisar URLs (autorizada). `fwupdmgr` se detecta, **nunca se ejecuta** una actualización de firmware.

**Riesgos:** solapes evitados con archivos exclusivos; la integración UI de stacks/snapshots se difiere a un quinto paso para no tocar `screens.py` dos veces.
