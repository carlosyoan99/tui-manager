# Guía de Instalación

## Requisitos Previos

### Sistema Operativo
- Linux (soportado: Debian, Ubuntu, Arch, Fedora, Void, Gentoo, OpenSUSE, Alpine)
- Python 3.10 o superior

### Dependencias del Sistema
Dependiendo de tu distribución, necesitarás instalar los siguientes paquetes:

#### Debian/Ubuntu
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

#### Arch Linux
```bash
sudo pacman -S python python-pip git
```

#### Fedora
```bash
sudo dnf install python3 python3-pip git
```

#### Void Linux
```bash
sudo xbps-install -y python3 python3-pip git
```

#### Gentoo
```bash
sudo emerge --ask --verbose dev-lang/python dev-python/pip git
```

## Instalación desde Fuente

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/TUI-Manager.git
cd TUI-Manager
```

### 2. Crear Entorno Virtual (Recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # En Linux
# o
venv\Scripts\activate  # En Windows
```

### 3. Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Instalar Dependencias del Sistema (Opcional)

Si quieres soporte completo para tu distribución:

**Debian/Ubuntu:**
```bash
sudo apt install -y python3-apt python3-pip
```

**Arch Linux:**
```bash
sudo pacman -S --needed python-pyalpm
```

**Fedora:**
```bash
sudo dnf install -y python3-pydnf
```

**Void Linux:**
```bash
sudo xbps-install -y xbps-python
```

### 5. Configurar el Programa

```bash
# Copiar configuración por defecto
cp config/default.yaml config/config.yaml
```

### 6. Ejecutar el Programa

```bash
python main.py
```

## Instalación en Termux/Android (soporte limitado)

En Termux el soporte es **limitado** por diseño (sin elevación de privilegios, `ps` restringido por Android): paquetes del prefix, procesos propios y temas internos de la TUI.

```bash
# 1. Requisitos de Termux
pkg update
pkg install python git

# 2. Clonar e instalar
git clone https://github.com/tu-usuario/TUI-Manager.git
cd TUI-Manager
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt

# 3. Ejecutar
python -m tui_manager.main   # o: python tui_manager/main.py
```

Notas:
- Detección automática vía `PREFIX`/`TERMUX_VERSION` → el gestor usado es apt del prefix (comando `pkg`, envoltorio de apt con repos de Termux).
- Los nombres de paquetes difieren de Debian (p. ej. `python` en vez de `python3`).
- Opcional: si usás `proot-distro` con una distro completa, el adaptador de esa distro opera dentro del proot.
- El menú Sistema/Temas de escritorio aparece deshabilitado con su motivo (no hay WM en Android).

## Instalación como Sistema (Opcional)

### Crear Enlace Simbólico

```bash
sudo ln -s $(pwd)/tui-manager /usr/local/bin/
```

Ahora puedes ejecutarlo desde cualquier lugar:
```bash
tui-manager
```

## Instalación con Script (Recomendado)

### Script de Instalación

```bash
#!/bin/bash
# install.sh

set -e

echo "=== Instalando TUI Manager ==="

# Detectar distribución
if [ -f /etc/debian_version ]; then
    echo "Detectando Debian/Ubuntu..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv git
elif [ -f /etc/arch-release ]; then
    echo "Detectando Arch Linux..."
    sudo pacman -S --needed python python-pip git
elif [ -f /etc/fedora-release ]; then
    echo "Detectando Fedora..."
    sudo dnf install -y python3 python3-pip git
elif [ -f /etc/void-release ]; then
    echo "Detectando Void Linux..."
    sudo xbps-install -y python3 python3-pip git
else
    echo "Distribución no soportada"
    exit 1
fi

# Clonar repositorio
if [ ! -d "TUI-Manager" ]; then
    git clone https://github.com/tu-usuario/TUI-Manager.git
    cd TUI-Manager
fi

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Instalar dependencias del sistema
if [ -f /etc/debian_version ]; then
    sudo apt install -y python3-apt
elif [ -f /etc/arch-release ]; then
    sudo pacman -S --needed python-pyalpm
elif [ -f /etc/fedora-release ]; then
    sudo dnf install -y python3-pydnf
elif [ -f /etc/void-release ]; then
    sudo xbps-install -y xbps-python
fi

echo "=== Instalación completada ==="
echo "Para ejecutar, usa: python main.py"
```

Hacerlo ejecutable:
```bash
chmod +x install.sh
./install.sh
```

## Desinstalación

### 1. Eliminar el programa

```bash
# Si instalaste con el script
rm -rf TUI-Manager

# Si creaste un enlace simbólico
sudo rm /usr/local/bin/tui-manager
```

### 2. Eliminar configuración

```bash
rm -rf ~/.tui-manager
```

### 3. Desactivar entorno virtual

```bash
deactivate
rm -rf venv
```

## Actualización

```bash
cd TUI-Manager
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Solución de Problemas

### Error: "No module named 'textual'"

```bash
pip install textual
```

> **Nota**: los adaptadores de paquetes usan subprocesos puros. **No se necesitan** bindings nativos (`python-apt`, `pyalpm`, `pydnf`, `xbps-python`) en ninguna distribución.

### Error: "Permission denied"

```bash
# Ejecutar con sudo
sudo python main.py

# O agregar usuario al grupo sudo
sudo usermod -aG sudo $USER
# Necesitas cerrar sesión y volver a entrar
```

### Error: "Distribution not detected"

```bash
# Verificar que el archivo de distribución existe
ls -l /etc/os-release
ls -l /etc/debian_version
# etc.
```

## Verificar Instalación

```bash
python3 -c "import textual; print('textual:', textual.__version__)"
python3 -c "import yaml; print('yaml:', yaml.__version__)"
```

## Siguiente Paso

Una vez instalado, consulta la [Guía de Uso](USAGE.md) para aprender a usar la aplicación.
