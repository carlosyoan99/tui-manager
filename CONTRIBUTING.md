# Contribuir a TUI Manager

Gracias por tu interés en mejorar TUI Manager. Este documento explica cómo
preparar el entorno, cómo se organiza el proyecto y qué se espera de una
contribución. El repositorio oficial es
[carlosyoan99/tui-manager](https://github.com/carlosyoan99/tui-manager).

Al participar aceptas el [Código de Conducta](CODE_OF_CONDUCT.md). **GitHub es
el único canal oficial** del proyecto: usa
[GitHub Issues / Discussions](https://github.com/carlosyoan99/tui-manager/issues)
para bugs y preguntas. Para problemas de seguridad, abre un
[GitHub Security Advisory (privado)](https://github.com/carlosyoan99/tui-manager/security/advisories/new)
y sigue [SECURITY.md](SECURITY.md) en vez de abrir un issue público. No se
aceptan reportes por correo electrónico.

## Preparar el entorno

Requisitos: Python 3.10 o superior y un terminal compatible con
[textual](https://textual.textualize.io/). No se necesitan bindings nativos de
gestores de paquetes: los adaptadores usan subprocesos.

```bash
git clone https://github.com/carlosyoan99/tui-manager.git
cd tui-manager
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest-asyncio
python -m pip install -e .
```

Comprobación rápida de que el entorno está listo:

```bash
tui-manager --version
tui-manager --doctor
python -m compileall -q tui_manager
```

## Ejecutar los tests

```bash
python -m pytest -q
```

La referencia es la suite completa (361 tests en la versión 1.1.0). La CI de
GitHub ejecuta la misma suite en Python 3.10, 3.11, 3.12 y 3.13 sobre Linux, y
en FreeBSD 13.4 y 14.2 dentro de una VM. Los tests son simulados: no deben
instalar paquetes reales ni depender de red. Si tu cambio añade una
funcionalidad, añade también su test; si la suite no pasa en todos los hosts,
el cambio no está listo para revisión.

## Organización del código

| Ruta | Contenido |
|---|---|
| `tui_manager/main.py` | Punto de entrada, CLI (`--version`, `--doctor`, `--lang`) |
| `tui_manager/core/` | Detección de SO/entorno, paquetes, procesos, temas, configuración, eventos |
| `tui_manager/ui/` | Pantallas y menús textual (`app.py`, `screens.py`) |
| `tui_manager/i18n.py` | Textos en español e inglés |
| `config/` | `default.yaml` y packs de temas |
| `docs/` | Guías de instalación, uso, API y planes de trabajo |
| `tests/` | Suite simulada multi-SO, UI y CLI |

Un nuevo sistema operativo o gestor de ventanas se añade como **adaptador**,
no cambiando el resto del código. Mantén el principio de degradación elegante:
una capacidad no soportada debe aparecer deshabilitada con su motivo, nunca
romper en tiempo de uso.

## Estilo y convenciones

- Código legible, PEP 8, 4 espacios y docstrings en las funciones públicas.
- Sin colores ni texto decorativo en la salida de datos que puedan consumir
  scripts; los errores van a stderr con un código de salida coherente.
- Los textos visibles van en `tui_manager/i18n.py` (es/en), no hardcoded en las
  pantallas.
- **No cambies los atajos ni el menú existente** sin una razón explícita: los
  atajos `1`–`9` y `0`, `?`, `Esc` y `q` forman parte de la interfaz conocida.
- Los subprocesos están restringidos: `--doctor` solo invoca el flag
  `--version` de una lista fija de ejecutables. No introduzcas ejecución arbitraria de
  comandos ni interpolaciones de texto del usuario en `shell=True`.
- Antes de modificar archivos de configuración del sistema, haz copia de
  seguridad, como hace ya el código de temas y ventanas.
- No incluyas en el commit artefactos generados: `.coverage`, `__pycache__/`,
  `.pytest_cache/`, `*.egg-info/`, `build/`, `dist/` ni entornos virtuales.

## Proponer un cambio

1. Haz un fork y crea una rama descriptiva desde `main` (por ejemplo
   `fix/processes-sort` o `docs/demo`).
2. Haz commits pequeños con mensajes en imperativo que expliquen el *por qué*;
   si hay un issue relacionado, menciónalo.
3. Ejecuta los tests y `python -m compileall -q tui_manager` antes de abrir el
   PR.
4. Abre el pull request contra `main` contando qué cambia, cómo se probó y qué
   sistemas afecta. Adjunta la salida de `tui-manager --doctor` si el cambio
   toca detección de SO, entorno o gestores.
5. Atiende los comentarios de revisión en la misma rama; no hagas push a `main`
   ni crees etiquetas. La publicación de versiones la decide el maintainer.

## Informar de errores

Abre un issue en
[GitHub Issues](https://github.com/carlosyoan99/tui-manager/issues) e incluye:

- Versión (`tui-manager --version`) y sistema (Linux/BSD/Termux, distro, WM/DE).
- Salida de `tui-manager --doctor`.
- Pasos para reproducir, comportamiento esperado y comportamiento real.
- Si es posible, captura o grabación corta; la guía
  [demo](docs/DEMO.md) explica cómo grabar una sin ejecutar acciones reales.

Para vulnerabilidades de seguridad, **no** uses issues públicos: abre un
[GitHub Security Advisory (privado)](https://github.com/carlosyoan99/tui-manager/security/advisories/new)
y consulta [SECURITY.md](SECURITY.md). GitHub es el único canal de contacto.

## Licencia

TUI Manager se distribuye bajo licencia [MIT](https://opensource.org/licenses/MIT).
Al enviar una contribución aceptas que se publique bajo esa misma licencia.
