# Guía de instalación

**TUI Manager** (`tui-manager`) — versión `2.0.1`. Panel de control
portable para la terminal: paquetes, procesos, sistema y temas, con un catálogo
de 179 aplicaciones en 29 categorías.

## Requisitos

- Python **3.10 o superior**.
- Dependencias de Python: `textual>=0.40.0`, `pyyaml>=6.0.1` y
  `python-json-logger>=2.0.7`. Los canales descritos abajo las instalan
  automáticamente.
- **No** se necesitan bindings nativos (`python-apt`, `pyalpm`, `pydnf`,
  `xbps-python`): los adaptadores de paquetes llaman a los gestores del sistema
  mediante subprocesos.

El ejecutable se instala como `tui-manager`. También puede lanzarse con
`python3 -m tui_manager.main`.

> **Estado Beta 2:** la auditoría de acciones destructivas (B2-1) y los stacks
> por rol, la detección opcional de `fwupdmgr` y los snapshots de configuración
> (B2-3) están **en Beta 2**; no se describen aquí como funciones terminadas.
> El rollback de una instalación fallida **nunca borra archivos del usuario**:
> solo revierte directorios vacíos creados por el propio comando.

> **Beta 3 — verificación multiplataforma:** la comprobación en las
> distribuciones y gestores de ventanas objetivo se ejecuta durante Beta 3.
> La **CI corre en Linux y FreeBSD** (`.github/workflows/ci.yml`); las
> mediciones de arranque y refresco se registran en `tests/manual-checklist.md`.
> Esto no implica paquetes publicados para todas esas plataformas.

---

## Debian / Ubuntu

**Canal natural: PyPI** (recomendado, sin paquetes del sistema adicionales):

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
python3 -m pip install --user tui-manager
```

Añade `~/.local/bin` al `PATH` si aún no está (cierra y abre la terminal):

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Paquete `.deb` construible** — el descriptor está en `packaging/debian/`:

```bash
sudo apt install -y build-essential debhelper dh-python python3-all python3-setuptools
cp -r packaging/debian ./debian
dpkg-buildpackage -us -uc -b
sudo apt install ../tui-manager_2.0.1-1_all.deb
```

Las dependencias de ejecución se derivan de `setup.py` mediante `dh_python3`;
no hay que instalarlas a mano.

## Arch Linux y derivados

**Canal natural: AUR** mediante el `PKGBUILD` de `packaging/PKGBUILD`:

```bash
sudo pacman -S --needed base-devel git
cd packaging && makepkg -si
```

El `PKGBUILD` declara `python`, `python-textual`, `python-pyyaml` y
`python-json-logger`, así que `makepkg` resuelve las dependencias. Antes de
publicarlo en AUR hay que verificar el tag `2.0.1` y sustituir
`sha256sums=('SKIP')` por la suma real. Mientras el paquete no esté en AUR,
usa PyPI:

```bash
sudo pacman -S --needed python python-pip
python -m pip install --user tui-manager
```

## Fedora

**Canal natural: RPM construible** desde `packaging/tui-manager.spec`:

```bash
sudo dnf install -y rpm-build rpmdevtools python3-devel python3-setuptools python3-wheel
rpmdev-setuptree
cp packaging/tui-manager.spec ~/rpmbuild/SPECS/
spectool -g -R ~/rpmbuild/SPECS/tui-manager.spec
rpmbuild -ba ~/rpmbuild/SPECS/tui-manager.spec
sudo dnf install ~/rpmbuild/RPMS/noarch/tui-manager-2.0.1-1.*.noarch.rpm
```

El spec genera las dependencias desde `install_requires` (`python3dist(...)`
de `textual`, `pyyaml` y `python-json-logger`). Verifica antes que el tag
`v0.5.0` exista. Alternativamente, desde PyPI:

```bash
sudo dnf install -y python3 python3-pip
python3 -m pip install --user tui-manager
```

## Void Linux

Void no tiene un descriptor propio en esta entrega; el canal natural es PyPI:

```bash
sudo xbps-install -Su
sudo xbps-install -y python3 python3-pip git
python3 -m pip install --user tui-manager
```

Añade `~/.local/bin` al `PATH` si es necesario.

## FreeBSD

**Canal natural: port / paquete `pkg`**. El esqueleto está en
`packaging/freebsd/`:

```bash
sudo pkg install -y python git
cd packaging/freebsd
make makesum          # genera distinfo; comprueba antes el tag 2.0.1
sudo make install clean
```

El port declara los ports `py-*` equivalentes a `textual`, `pyyaml` y
`python-json-logger`, por lo que no hay pasos manuales de dependencias. Si
prefieres PyPI:

```bash
python -m pip install --user tui-manager
```

## Termux / Android (soporte limitado)

Sin elevación de privilegios: paquetes del prefix, procesos propios y temas
internos de la TUI. La detección usa `PREFIX`/`TERMUX_VERSION` y el menú de
temas de escritorio aparece deshabilitado con su motivo.

```bash
pkg update && pkg upgrade
pkg install -y python git
python -m pip install tui-manager
tui-manager --version
```

En Termux no se usa `sudo` ni `--user`: `pip` instala dentro de `$PREFIX`.
Los nombres de paquetes difieren de Debian (p. ej. `python`, no `python3`).

---

## Instalación desde el código fuente (cualquier plataforma)

```bash
git clone https://github.com/carlosyoan/TUI-Manager.git
cd tui-manager
python3 -m venv .venv
. .venv/bin/activate          # en Termux: . .venv/bin/activate (con `python`)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
tui-manager --version
```

La configuración se lee desde `~/.config/tui-manager/config.yaml` (XDG; logs en `~/.local/state/tui-manager/` y snapshots en `~/.local/share/tui-manager/`); puedes
partir de `config/default.yaml` del repositorio si quieres personalizarla.

## Verificación

```bash
tui-manager --version    # 2.0.1
tui-manager --doctor     # SO, distro, gestor, entorno y capacidades
tui-manager --lang es    # fuerza el idioma (es|en) para esta ejecución
```

## Desinstalación

```bash
python3 -m pip uninstall tui-manager      # instalación desde PyPI o fuente
```

Si instalaste un paquete nativo, usa el gestor correspondiente:
`sudo apt remove tui-manager` (Debian/Ubuntu), `pacman -R tui-manager` (Arch),
`sudo dnf remove tui-manager` (Fedora), `sudo xbps-remove -R tui-manager`
(Void) o `sudo pkg remove tui-manager` (FreeBSD).

## Solución de problemas

- **`No module named 'textual'`** → reinstala las dependencias:
  `python3 -m pip install -r requirements.txt`.
- **`tui-manager: command not found`** → añade `~/.local/bin` al `PATH` (o
  activa el entorno virtual creado desde fuente).
- **Permisos insuficientes para gestionar paquetes** → no lances la TUI con
  `sudo`: usa la elevación que la propia aplicación solicita (`sudo`/`doas`)
  solo para la acción concreta.
- **Distro no detectada** → revisa `/etc/os-release` (o `uname` en BSD); en
  Termux comprueba que `PREFIX`/`TERMUX_VERSION` estén definidos.

Consulta después la [guía de uso](USAGE.md) y la
[documentación de la API](API.md#empaquetado).
