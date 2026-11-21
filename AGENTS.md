# AGENTS.md — guía para agentes de IA en TUI Manager

Este archivo es para **agentes de IA** (OpenCode, Claude Code, subagentes) que trabajen en este repo. Para documentación de usuario, ver [README.md](README.md).

## 1. Qué es este proyecto

TUI Manager 2.0.0: panel de control terminal inspirado en Omarchy, portable (Linux, BSD, macOS, Windows, Termux), escrito en Python + textual. Objetivo: un menú que unifique paquetes, procesos, sistema, temas, actualizaciones y catálogo de apps, con degradación elegante por capacidades.

**Principio rector:** conducta de Omarchy, portabilidad de adapter. Omarchy está atado a Arch+Hyprland; aquí cada SO/entorno tiene su adapter y las funciones no soportadas se desactivan con el motivo, nunca se fingen.

## 2. Reglas de oro (permisos)

El usuario dio permiso explícito para **revisar URLs** y **copiar/testear en sus hosts** (`ssh laptop`, `ssh void`, `ssh movil`). Todo lo demás requiere **pedir permiso antes**:

- ❌ Publicar, enviar, `git push`, `gh repo`/Actions, borrar, `rm -rf`.
- ❌ `sudo`, instalar paquetes, comandos de red no autorizados.
- ❌ Escribir fuera de `/home/carlosyoan/Documents/Projects/TUI-Manager/`.
- ✅ Pedir confirmación antes de cualquiera de esas acciones.

Excepción conocida: el usuario autorizó borrar la antigua `~/.tui-manager/` en los 4 hosts (ya ejecutado y verificado).

## 3. Arquitectura

```
UI (textual) → Core (servicios inyectados) → Plano de SO (PackageAdapter por distro)
                                          → Plano de entorno (EnvironmentAdapter por DE/WM)
```

- `tui_manager/ui/app.py`: `TuiManagerApp` + `Services` (inyección para tests). Aquí se inyecta el hook `elevator` (sudo/doas).
- `tui_manager/ui/screens.py`: las 10 pantallas + modales clicables. `MainMenuScreen.ENTRIES` es la fuente única del menú y sus atajos `[1]`–`[9]`/`[0]`.
- `tui_manager/core/*_adapter.py`: un adapter por gestor (ver `package_manager.py`). Todos derivan de `PackageAdapter`.
- `tui_manager/core/environment.py`: adapters de entorno con `Capability`. `EnvironmentDetector.detect()` elige por WMs/DE/SO.
- `tui_manager/core/system_control.py`: acciones de sistema con `availability()` y degradación.
- `tui_manager/core/paths.py`: **única fuente de rutas XDG** (config, state/logs, data/snapshots) con fallback legacy.
- `tui_manager/core/audit.py`: `AuditLog` para acciones destructivas.
- `tui_manager/core/perf.py`: caché y paginación (arranque <2 s, refresco <500 ms).
- `tui_manager/core/alternative_sources.py` + `sources_adapter.py` + `stacks.py` + `snapshots.py`: fuentes externas, stacks por rol y backups.
- `tui_manager/core/theme_mutagen.py` (en `ui/`): paleta dinámica desde `~/.config/opencode/themes/matugen.json`.
- `tui_manager/main.py`: CLI (`--version`, `--doctor`, `--quickstart`, `--json`, `--lang`). `collect_doctor_data()` es la fuente única del doctor; `run_doctor()` solo formatea.

### Contratos importantes

- `--doctor` reporta **solo la CLI relevante de la distro** (`CLI_BY_DISTRO`/`relevant_cli()`). No listar apt/dnf en Arch ni sugerir instalar una CLI ya presente.
- `PackageAdapter.execute_command`: si no es root, comprueba `<tool> -n true`; con caché usa `-n`; si no, invoca `self.elevator` (la UI suspend la TUI y corre `<tool> -v` en el TTY real). Nunca guardar contraseñas ni pasarlas por argumento.
- `App.elevate()` **debe llamar a `suspend()` desde el hilo principal** vía `call_from_thread` (crítico bajo SSH).
- Los comandos de solo lectura no llevan sudo/doas.

## 4. Convenciones de código

- Python 3.10+, `from __future__ import annotations`, dataclasses para modelos (`Package`, `Process`, `InstallResult`, `AuditEntry`).
- `typing` en firmas; parámetros nuevos **al final con default** para no romper callers.
- `logger` del módulo (`logging`), nunca `print()` en producción salvo callbacks de consola.
- i18n: toda cadena visible pasa por `t('clave')` con clave en **es y en** dentro de `tui_manager/i18n.py`. Si agregás claves, verificá que queden **dentro** de cada dict (error histórico: quedaron fuera y `t()` devolvía la clave).
- Nuevos SO: añadir adapter en `core/`, registrarlo en `package_manager.py`, y rutas de doctor en `main.py`.

## 5. Tests (obligatorio)

```bash
.venv/bin/python -m pytest -q
```

- **469 tests**, 100 % simulados. `tests/conftest.py` → `FakeRunner` (cualquier comando no simulado falla), simula `sudo` y fuerza `geteuid=1000` para que los tests sean portables (el runner FreeBSD es root).
- Nunca ejecutar `sudo`, `pacman`, `brew`, `winget`, `powershell` ni red en tests. Usar `monkeypatch` de `platform.system`, `shutil.which` y `subprocess.run`.
- Los tests UI usan `run_test()` de textual con `Services` fakes. Al cambiar `screens.py`, verificar que sigan los 8 estados vacíos, los `LoadingIndicator`, el guardia AST de subprocess en handlers y la ayuda `?`.

## 6. Flujo de trabajo con agentes (aprendido en 1.1–2.0)

1. **Arquitecto** escribe un `docs/PLAN-*.md` con subtareas, archivos a tocar y criterio verificable con pytest.
2. **Implementadores** trabajan en paralelo con **archivos exclusivos** (nunca dos agentes en el mismo archivo). Cada uno entrega commit local + diff + salida de pytest.
3. **Documentador** mantiene docs y changelog alineados (evita el desfase catálogo↔roadmap que ocurrió en Alfa 3).
4. **Verificador** corre suite completa + smoke + `--doctor`, y escribe veredicto en `docs/QA-REPORT.md`.
5. **Cierre**: versión en `__init__.py`/`setup.py` + entrada en `CHANGELOG.md` + README/QA, push (con permiso) y **replicación a los 4 hosts** con `tar | ssh` (excluyendo `.venv`, `__pycache__`, `.pytest_cache`, `*.pyc`).

## 7. Los 4 hosts de prueba

| Host | Acceso | Shell | Python |
|---|---|---|---|
| Notebook | local (CachyOS) | fish | 3.14 |
| Laptop | `ssh laptop` (CachyOS) | fish | 3.14 |
| Void-Laptop | `ssh void` | fish | 3.14 |
| Móvil | `ssh movil` (Termux) | zsh | 3.13 (sin venv; usa Python global) |

Comando `tm` disponible en los 4. **2.0 no se cierra hasta que pasen los 4 hosts y la CI.**

## 8. CI

`.github/workflows/ci.yml`: Linux Python 3.10/3.11/3.12/3.13 + FreeBSD 13.4/14.2. Instala **solo runtime + pytest** (nunca `requirements.txt` completo: `mypy→maturin` rompe FreeBSD), usa `python3` + `ensurepip` (no `py311-pip`), y corre `compileall` + pytest. Verificada en verde en el commit `170492a`.

## 9. Errores históricos — no repetir

- `call_from_thread(set.clear)` → envolver en lambda (3.10/3.11 no inspects builtins).
- `capture_output=True` con sudo → sin TTY para la contraseña; usar el flujo `-n`/`elevator`.
- `suspend()` desde worker → falla bajo SSH; delegar al hilo principal.
- Tests que asumen Linux (`platform.system`), root (`geteuid`) o sudo instalado → mockear.
- Claves i18n fuera del dict → `t()` devuelve la clave.
- Duplicados en `app_catalog.py` (`redis`, `fd`) → hay test estricto.
- AppImage sin URL real → se descarta; solo URLs http(s) verificadas.

## 10. Referencia

Historia completa y decisiones: [CHANGELOG.md](CHANGELOG.md), [docs/ROADMAP.md](docs/ROADMAP.md), [docs/RETROSPECTIVA.md](docs/RETROSPECTIVA.md), [docs/PLAN-2.0-BETAS.md](docs/PLAN-2.0-BETAS.md). Idea original: [docs/especificaciones_tui_app.md](docs/especificaciones_tui_app.md).
