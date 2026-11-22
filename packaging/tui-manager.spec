# Descriptor RPM para Fedora. Version 2.0.1 (estable).
# Antes de construir: verificar que el tag v%{version} existe.
# No se ejecutó rpmbuild; este archivo solo es un descriptor.

Name:           tui-manager
Version:        2.0.1
Release:        1%{?dist}
Summary:        Panel de control portable para la terminal
License:        MIT
URL:            https://github.com/carlosyoan99/tui-manager
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel

# Dependencias de ejecución generadas desde install_requires en setup.py
# (textual, pyyaml, python-json-logger). Se usa la forma python3dist() para
# no depender de nombres de paquetes concretos del repositorio Fedora.
Requires:       python3dist(textual) >= 0.40.0
Requires:       python3dist(pyyaml) >= 6.0.1
Requires:       python3dist(python-json-logger) >= 2.0.7

%description
Panel de control portable para la terminal: paquetes, procesos, sistema
y temas, con degradación elegante según las capacidades del entorno.
Soporta Linux, BSD y Termux (limitado).

%prep
%autosetup -n tui-manager-%{version}

%build
%py3_build

%install
%py3_install

# La suite de tests requiere los extras de desarrollo; no se ejecuta aqui.
# %check
# %{__python3} -m pytest -q

%files
# El arbol no incluye archivo LICENSE; la licencia MIT se declara en setup.py.
%doc README.md CHANGELOG.md
%{_bindir}/tui-manager
%{python3_sitelib}/tui_manager/
%{python3_sitelib}/tui_manager-*.dist-info/

%changelog
* Wed Nov 18 2026 Carlos Yoan (GitHub: carlosyoan99) - 2.0.1-1
- Release 2.0.1 (estable).
