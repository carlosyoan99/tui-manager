# Investigación — qué falta para consolidarse como aplicación de mercado

> **Fecha:** 2026-11-19 · **Contexto:** TUI Manager 1.0.0, 333 tests en 4 hosts, 82 % cobertura.
> **Fuentes:** el propio repo (`ROADMAP.md`, `QA-REPORT.md`, `RETROSPECTIVA.md`), las decisiones de Omarchy adoptadas (A–I), y el estado real del ecosistema TUI (btop, lazygit, yazi, fastfetch, micro). No es promoción: es una lista de brechas accionables.

> **Nota de estado (2026-11-20):** este documento refleja el diagnóstico de 1.0.
> Las brechas «CI solo escrita, no ejecutada», «Sin onboarding guiado»,
> «Sin salida para scripts/agentes», «Comunidad» (sección 2) y el punto 6 de
> la sección 4 **ya están resueltas en 1.2**: `tm --quickstart` (1.2-A),
> `--json` para `packages`/`processes`/`doctor` (1.2-B),
> CONTRIBUTING/SECURITY/CODE_OF_CONDUCT (1.2-C) y workflow de CI (1.2-D).
> La CI de GitHub está **verificada en verde** en Linux 3.10–3.13 y FreeBSD
> 13.4/14.2 (antes solo estaba escrita; `137db1d`, `5a3ef7f` y `3906866`
> corrigieron la matriz). Sigue pendiente y requiere permiso explícito la
> **publicación** en PyPI/AUR/copr.

---

## 1. Diferenciador actual (ya lo tenemos)

Hay un ángulo claro y defendible: **"panel de control portable estilo Omarchy en la terminal"**. Omarchy está atado a Arch + Hyprland + Quickshell; TUI Manager corre en Debian, Arch, Fedora, Void, BSD y Termux con degradación elegante. Eso es una propuesta de valor real, no un clon. El README ya lo dice bien; hay que amplificarlo, no cambiarlo.

## 2. Brechas que bloquean "producto" (prioridad alta)

| Brecha | Por qué importa | Acción concreta |
|---|---|---|
| **No está publicado** | Sin PyPI/AUR/deb/rpm, el usuario debe clonar y crear venv. Los descriptores existen en `packaging/` pero no se han publicado. | Publicar en PyPI (`python -m build && twine upload dist/*`), AUR y copr. Requiere tu OK. |
| **CI solo escrita, no ejecutada** | El workflow `.github/workflows/ci.yml` existe pero no corre en GitHub. Un badge verde es prueba social. | Habilitar Actions en el repo y ejecutar la matriz Linux + FreeBSD. |
| **Sin onboarding guiado** | `tm` abre un menú de 10 entradas sin explicación. | Añadir `tm quickstart` (asistente interactivo) y una pantalla "Primeros pasos" en la ayuda. |
| **Sin salida para scripts/agentes** | La función H (integración agéntica) está en post-1.0. Hoy solo hay TUI + `--doctor`. | Modo `--json`/`--format json` para listar paquetes/procesos y ejecutar acciones; útil para dotfiles y agentes. |
| **Documentación sin demostración visual** | Un TUI se vende viéndolo. | Grabar un cast con `vhs`/asciinema del menú y ponerlo arriba del README. |

## 3. Calidad percibida (prioridad media)

| Brecha | Acción |
|---|---|
| Navegación solo teclado ya funciona, pero no se anuncia | Añadir badge "keyboard-first" y tabla de atajos en el README (ya existe en USAGE). |
| Catalógo de 179 apps es bueno pero estático | Añadir `tm update-catalog` que refresque URLs verificadas (scripts con curl, con permiso). |
| Ausencia de perfiles de configuración | Perfiles `~/.config/tui-manager/profiles/*.yaml` (`minimal`, `dev`, `streaming`) con un `Select` en Ajustes. |
| Sin feedback de "qué hace este comando" | Cada confirmación debería mostrar el comando exacto a ejecutar (auditabilidad + confianza). |
| Idiomas solo es/en | Ya es suficiente para empezar; no ampliar hasta que haya demanda. |

## 4. Recherche rápida: qué hace que un TUI se consolide

Patrones observables en btop, lazygit, yazi, fastfetch:
1. **Arranque inmediato y salida limpia** — ya medimos 160–186 ms.
2. **Una sola cerveza, bien hecha** — btop es monitor, lazygit es git. TUI Manager es más amplio; el riesgo es parecer difuso. Mitigación: el menú jerárquico y el `tm --doctor` como entrada.
3. **Config como código** — archivo YAML legible y versionable. Ya existe `~/.config/tui-manager/config.yaml`.
4. **Temas y personalización** — el punto 5 del usuario (theme mutagen) va justo aquí.
5. **Salida de datos** — `btop` tiene export; nosotros deberíamos tener `--json`.
6. **Comunidad** — CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, plantillas de issues. Hoy no existen; son baratos y aumentan confianza.

## 5. Tema dinámico: aclaración importante

El usuario pide "replicar el tema **mutagen** que usa OpenCode y otras apps para el dinámico que genera Noctalia". Lo más probable es **matugen** (generador de esquemas a partir del wallpaper, muy usado en el ecosistema Hyprland/Noctalia), no "mutagen".

**No hay referencias a matugen/mutagen en el repo ni en el vault**, así que el formato exacto (ruta del archivo de colores, si es JSON/TOML/YAML, si OpenCode expone una variable de entorno) **debe verificarse en las notebooks** antes de programar. Plan:

1. En CachyOS (las 3 laptops), localizar el esquema generado por Noctalia/matugen: mirar `~/.config/quickshell`, `~/.cache/matugen`, variables de entorno del proceso de Noctalia y la config de OpenCode (`~/.config/opencode`).
2. Documentar el formato real en una nota del vault.
3. Recién entonces implementar `theme_source: mutagen` en `ui/theme_mutagen.py` (1.1-E).

Mientras tanto, el plan 1.1 aclara que el `Select` de tema es **de la TUI** y que el tema del escritorio lo sigue haciendo Noctalia.

## 6. Sugerencia de prioridad para 1.1 y 1.2

- **1.1**: los 6 puntos del usuario (UI, Termux, lote, orden, tema, Acerca de).
- **1.2**: onboarding (`tm quickstart`), `--json`, PUBLICACIÓN (PyPI/AUR), CI ejecutada, CONTRIBUTING/SECURITY, cast de demostración.

No publicar ni ejecutar CI sin permiso explícito. Todo lo demás es documentación y código dentro del repo.
