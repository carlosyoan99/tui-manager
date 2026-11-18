# Empaquetado

Descriptores por plataforma para TUI Manager. Todos usan la versión `0.5.0`,
que corresponde a la release `0.5.0-beta.1` (`0.5.0b1` en PEP 440), y el
nombre `tui-manager`, igual que el paquete PyPI y el ejecutable de la CLI.

| Plataforma | Archivos | Canal |
|---|---|---|
| Arch Linux | `PKGBUILD` | AUR (`makepkg -si` desde este directorio; publicación en AUR pendiente) |
| Debian/Ubuntu | `debian/control`, `debian/rules`, `debian/changelog` | `.deb` construible con `dpkg-buildpackage` |
| Fedora | `tui-manager.spec` | `.rpm` construible con `rpmbuild` |
| FreeBSD | `freebsd/Makefile`, `freebsd/pkg-descr` | port (`make install`) / paquete `pkg` resultante |

Las dependencias de ejecución son las reales de `requirements.txt`: `textual`,
`pyyaml` y `python-json-logger`. Los adaptadores de gestores de paquetes usan
subprocesos, así que **no** se declaran bindings nativos (`python-apt`,
`pyalpm`, `pydnf`, `xbps-python`).

Antes de construir o publicar cualquiera de estos descriptores hay que:

1. Confirmar que el tag `v0.5.0` existe en el repositorio (los `source`/`Source0`
   y `GH_TAGNAME` apuntan a él) y que los nombres de paquetes declarados siguen
   vigentes en el repositorio de cada sistema.
2. Sustituir `sha256sums=('SKIP')` del PKGBUILD por la suma real (`makepkg -g`).
3. Generar `freebsd/distinfo` con `make makesum` (no incluido: requiere red).

En esta entrega **no se ejecutó ningún build** (`makepkg`, `dpkg-buildpackage`,
`rpmbuild` ni `make`): solo se escribieron los descriptores. Las funciones de
stacks, fwupd y snapshots están **en Beta 2** (B2-3) y no se presentan aquí como
funcionalidades terminadas.
