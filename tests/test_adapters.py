"""
Tests simulados de los 7 adapters de paquetes (debian, arch, fedora, void,
termux, freebsd, pkgsrc) contra salidas reales de cada gestor.
"""

import pytest

from tui_manager.core.debian_adapter import DebianAdapter
from tui_manager.core.arch_adapter import ArchAdapter
from tui_manager.core.fedora_adapter import FedoraAdapter
from tui_manager.core.void_adapter import VoidAdapter
from tui_manager.core.termux_adapter import TermuxAdapter
from tui_manager.core.freebsd_adapter import FreeBSDAdapter
from tui_manager.core.pkgsrc_adapter import PkgsrcAdapter
from tui_manager.core.package_adapter import PackageNotFoundError


# ---------------- Debian / apt ----------------

def test_debian_installed(fake_runner):
    fake_runner.expect(['apt', 'list', '--installed'], stdout=(
        "Listing... Done\n"
        "curl/stable,now 8.5.0-2 amd64 [installed]\n"
        "vim/stable,now 2:9.0.1000-3 amd64 [installed,upgradable to: 2:9.1.0-1]\n"
    ))
    pkgs = DebianAdapter().get_installed_packages()
    assert len(pkgs) == 2
    assert pkgs[0].name == 'curl' and pkgs[0].version == '8.5.0-2'
    assert pkgs[1].name == 'vim' and pkgs[1].version == '2:9.0.1000-3'
    assert all(p.installed for p in pkgs)


def test_debian_search(fake_runner):
    fake_runner.expect(['apt', 'search', 'curl'], stdout=(
        "Sorting... Done\n"
        "Full Text Search... Done\n"
        "curl/stable,now 8.5.0-2 amd64 [installed]\n"
        "  Command line tool for transferring data\n"
        "curlftpfs/stable 0.9.2-9 amd64\n"
        "  filesystem to access FTP hosts\n"
    ))
    pkgs = DebianAdapter().search_packages('curl')
    assert len(pkgs) == 2
    assert pkgs[0].installed is True and 'Command line' in pkgs[0].description
    assert pkgs[1].installed is False


def test_debian_updates(fake_runner):
    fake_runner.expect(['apt', 'list', '--upgradable'], stdout=(
        "Listing... Done\n"
        "vim/stable,now 2:9.0.1000-3 amd64 [upgradable from: 2:9.0.1000-3]\n"
    ))
    pkgs = DebianAdapter().get_updates_available()
    assert len(pkgs) == 1 and pkgs[0].name == 'vim'


def test_debian_info(fake_runner):
    fake_runner.expect(['apt', 'show', 'vim'], stdout=(
        "Package: vim\n"
        "Version: 2:9.0.1000-3\n"
        "Installed-Size: 3,400 kB\n"
        "Depends: vim-runtime (= 2:9.0.1000-3), libgpm2\n"
        "Description: Vi IMproved - enhanced vi editor\n"
    ))
    info = DebianAdapter().get_package_info('vim')
    assert info.version == '2:9.0.1000-3'
    assert 'Vi IMproved' in info.description
    assert any(d.startswith('vim-runtime') for d in info.dependencies)


def test_debian_info_not_found(fake_runner):
    fake_runner.expect(['apt', 'show', 'nope'], rc=100)
    with pytest.raises(PackageNotFoundError):
        DebianAdapter().get_package_info('nope')


def test_debian_install_confirm_false(fake_runner):
    fake_runner.expect(['sudo', 'apt', 'install', '-y', 'curl'], rc=0)
    assert DebianAdapter().install_package('curl', confirm=False) is True


def test_debian_install_failure(fake_runner):
    fake_runner.expect(['sudo', 'apt', 'install', '-y', 'x'], rc=1, stderr='boom')
    assert DebianAdapter().install_package('x', confirm=False) is False


# ---------------- Arch / pacman ----------------

def test_arch_installed(fake_runner):
    fake_runner.expect(['pacman', '-Qi'], stdout=(
        "Name            : bash\n"
        "Version         : 5.2.26-1\n"
        "Description     : The GNU Bourne Again shell\n"
        "Depends On      : glibc, readline\n"
        "\n"
        "Name            : curl\n"
        "Version         : 8.9.1-1\n"
        "Description     : Command line tool and library\n"
        "Depends On      : openssl, zlib\n"
    ))
    pkgs = ArchAdapter().get_installed_packages()
    assert len(pkgs) == 2
    assert pkgs[0].name == 'bash' and pkgs[0].version == '5.2.26-1'
    assert 'GNU Bourne' in pkgs[0].description
    assert pkgs[1].dependencies == ['openssl', 'zlib']


def test_arch_search(fake_runner):
    fake_runner.expect(['pacman', '-Ss', 'curl'], stdout=(
        "core/curl 8.9.1-1 [installed]\n"
        "    Command line tool and library for transferring data\n"
        "extra/curl-free 8.9.0-1\n"
        "    Curl variant\n"
    ))
    pkgs = ArchAdapter().search_packages('curl')
    assert len(pkgs) == 2
    assert pkgs[0].name == 'curl' and pkgs[0].installed is True
    assert pkgs[0].version == '8.9.1-1'
    assert 'Command line' in pkgs[0].description
    assert pkgs[1].name == 'curl-free' and pkgs[1].installed is False


def test_arch_updates(fake_runner):
    fake_runner.expect(['pacman', '-Qu'], stdout=(
        "bash 5.2.26-1 5.2.37-1\n"
        "linux 6.9.1-1 6.9.2-1\n"
    ))
    pkgs = ArchAdapter().get_updates_available()
    assert len(pkgs) == 2 and pkgs[1].version == '6.9.2-1'


def test_arch_info(fake_runner):
    fake_runner.expect(['pacman', '-Si', 'curl'], stdout=(
        "Repository        : core\n"
        "Name              : curl\n"
        "Version           : 8.9.1-1\n"
        "Description       : Command line tool and library\n"
        "Depends On        : openssl, zlib, libpsl\n"
    ))
    info = ArchAdapter().get_package_info('curl')
    assert info.version == '8.9.1-1'
    assert info.dependencies == ['openssl', 'zlib', 'libpsl']


def test_arch_install_remove(fake_runner):
    fake_runner.expect(['sudo', 'pacman', '-S', '--noconfirm', 'git'], rc=0)
    fake_runner.expect(['sudo', 'pacman', '-R', '--noconfirm', 'git'], rc=0)
    adapter = ArchAdapter()
    assert adapter.install_package('git', confirm=False) is True
    assert adapter.remove_package('git', confirm=False) is True


# ---------------- Fedora / dnf ----------------

def test_fedora_installed(fake_runner):
    fake_runner.expect(['dnf', 'list', 'installed'], stdout=(
        "Installed Packages\n"
        "Package Arch Version Repository Size\n"
        "bash.x86_64            5.2.15-1.el9    @baseos\n"
        "curl.x86_64            8.5.0-2.el9     @baseos\n"
        "python3.12.noarch      3.12.1-1.el9    @baseos\n"
    ))
    pkgs = FedoraAdapter().get_installed_packages()
    assert len(pkgs) == 3
    assert pkgs[0].name == 'bash' and pkgs[0].version == '5.2.15-1.el9'
    assert pkgs[2].name == 'python3.12' and pkgs[2].version == '3.12.1-1.el9'


def test_fedora_updates_rc100(fake_runner):
    fake_runner.expect(['dnf', 'check-update'], rc=100, stdout=(
        "Last metadata expiration check: 0:05:00 ago\n"
        "curl.x86_64     8.9.0-1.el9     baseos\n"
    ))
    pkgs = FedoraAdapter().get_updates_available()
    assert len(pkgs) == 1 and pkgs[0].name == 'curl' and pkgs[0].version == '8.9.0-1.el9'


def test_fedora_updates_rc0(fake_runner):
    fake_runner.expect(['dnf', 'check-update'], rc=0, stdout='')
    assert FedoraAdapter().get_updates_available() == []


def test_fedora_search(fake_runner):
    fake_runner.expect(['dnf', 'search', 'curl'], stdout=(
        "===== Name Matched: curl =====\n"
        "Name        : curl\n"
        "Summary     : A utility for getting files\n"
        "Version     : 8.5.0\n"
        "===== Name Matched: curl-minimal =====\n"
        "Name        : curl-minimal\n"
        "Summary     : Minimal curl\n"
    ))
    pkgs = FedoraAdapter().search_packages('curl')
    assert len(pkgs) == 2
    assert pkgs[0].name == 'curl' and 'utility' in pkgs[0].description
    assert pkgs[1].name == 'curl-minimal'


def test_fedora_dependencies(fake_runner):
    fake_runner.expect(
        ['dnf', 'repoquery', '--requires', '--resolve', '--qf', '%{name}', 'curl'],
        stdout="openssl\nzlib\n")
    deps = FedoraAdapter().get_dependencies('curl')
    assert deps == ['openssl', 'zlib']


def test_fedora_info(fake_runner):
    fake_runner.expect(['dnf', 'info', 'curl'], stdout=(
        "Name          : curl\n"
        "Version       : 8.5.0\n"
        "Summary       : A utility for getting files\n"
    ))
    fake_runner.expect(
        ['dnf', 'repoquery', '--requires', '--resolve', '--qf', '%{name}', 'curl'],
        stdout="openssl\n")
    info = FedoraAdapter().get_package_info('curl')
    assert info.version == '8.5.0' and info.dependencies == ['openssl']


# ---------------- Void / xbps ----------------

def test_void_installed(fake_runner):
    fake_runner.expect(['xbps-query', '-l'], stdout=(
        "ii bash-5.2.26_1     The GNU Bourne Again shell\n"
        "ii curl-8.9.1_2      Command line tool and library\n"
        "ii void-repo-nonfree-11_1\n"
    ))
    pkgs = VoidAdapter().get_installed_packages()
    assert len(pkgs) == 3
    assert pkgs[0].name == 'bash' and pkgs[0].version == '5.2.26_1'
    assert 'GNU Bourne' in pkgs[0].description
    assert pkgs[2].name == 'void-repo-nonfree' and pkgs[2].version == '11_1'


def test_void_search(fake_runner):
    fake_runner.expect(['xbps-query', '-Rs', 'curl'], stdout=(
        "[-] curl-8.9.1_2     Command line tool\n"
        "[*] bash-5.2.26_1    The GNU Bourne Again shell\n"
    ))
    pkgs = VoidAdapter().search_packages('curl')
    assert len(pkgs) == 2
    assert pkgs[0].installed is False
    assert pkgs[1].installed is True and pkgs[1].name == 'bash'


def test_void_info(fake_runner):
    fake_runner.expect(['xbps-query', '-S', 'curl'], stdout=(
        "architecture: x86_64\n"
        "version: 8.9.1_2\n"
        "description: Command line tool and library\n"
        "depends: libcurl>=8.9.1_1, openssl, zlib\n"
    ))
    info = VoidAdapter().get_package_info('curl')
    assert info.version == '8.9.1_2'
    assert 'Command line' in info.description
    assert info.dependencies == ['libcurl>=8.9.1_1', 'openssl', 'zlib']


def test_void_updates(fake_runner):
    fake_runner.expect(['xbps-install', '-n'], stdout=(
        "bash-5.2.37_1 update to version 5.2.37_1\n"
        "curl-8.9.2_1 update to version 8.9.2_1\n"
    ))
    pkgs = VoidAdapter().get_updates_available()
    assert len(pkgs) == 2 and pkgs[0].name == 'bash' and pkgs[0].version == '5.2.37_1'


def test_void_install_remove(fake_runner):
    fake_runner.expect(['sudo', 'xbps-install', '-y', 'git'], rc=0)
    fake_runner.expect(['sudo', 'xbps-remove', '-y', 'git'], rc=0)
    adapter = VoidAdapter()
    assert adapter.install_package('git', confirm=False) is True
    assert adapter.remove_package('git', confirm=False) is True


# ---------------- Termux / apt del prefix ----------------

def test_termux_installed(fake_runner):
    fake_runner.expect(
        ['dpkg-query', '-W', '-f=${Package}\\t${Version}\\t${Status}\\n'], stdout=(
        "7zip\t26.01\tinstall ok installed\n"
        "git\t2.51.0\tinstall ok installed\n"
        "apt\t2.9.8\tinstall ok deinstall/config-files\n"
    ))
    pkgs = TermuxAdapter().get_installed_packages()
    assert len(pkgs) == 2  # excluye 'deinstall/config-files'
    assert pkgs[0].name == '7zip' and pkgs[0].version == '26.01'


def test_termux_search(fake_runner):
    fake_runner.expect(['pkg', 'search', 'curl'], stdout=(
        "curl/stable 8.9.1-1\n"
        "git/stable 2.51.0\n"
    ))
    pkgs = TermuxAdapter().search_packages('curl')
    assert len(pkgs) == 2 and pkgs[0].name == 'curl'


def test_termux_no_sudo(fake_runner):
    """Termux nunca antepone sudo, ni aunque el método lo pida por defecto."""
    fake_runner.expect(['apt', 'update'], rc=0)
    adapter = TermuxAdapter()
    assert adapter.update_cache() is True
    assert all('sudo' not in cmd for cmd in fake_runner.calls)


# ---------------- FreeBSD / pkg ----------------

def test_freebsd_installed(fake_runner):
    fake_runner.expect(['pkg', 'info', '-a'], stdout=(
        "bash-5.2.26_1                  The GNU Project's Bourne Again SHell\n"
        "curl-8.9.1_2                   Command line tool\n"
    ))
    pkgs = FreeBSDAdapter().get_installed_packages()
    assert len(pkgs) == 2
    assert pkgs[0].name == 'bash' and pkgs[0].version == '5.2.26_1'
    assert 'Bourne' in pkgs[0].description


def test_freebsd_updates(fake_runner):
    fake_runner.expect(['pkg', 'upgrade', '-n'], stdout=(
        "All repositories are up-to-date.\n"
        "The following 2 package(s) will be affected:\n"
        "\n"
        "Installed packages to be UPGRADED:\n"
        "\tbash: 5.2.26 -> 5.2.37\n"
        "\tcurl: 8.9.1 -> 8.9.2\n"
    ))
    pkgs = FreeBSDAdapter().get_updates_available()
    assert len(pkgs) == 2
    assert pkgs[0].name == 'bash' and pkgs[0].version == '5.2.37'


def test_freebsd_info(fake_runner):
    fake_runner.expect(['pkg', 'info', 'curl'], stdout=(
        "curl-8.9.1_2:\n"
        "Name           : curl\n"
        "Version        : 8.9.1_2\n"
        "Description    : Command line tool\n"
        "Depends on:\n"
        "\tca_root_nss-3.93\n"
        "\tlibssh2-1.11.0_1,3\n"
    ))
    info = FreeBSDAdapter().get_package_info('curl')
    assert info.version == '8.9.1_2'
    assert info.dependencies == ['ca_root_nss-3.93', 'libssh2-1.11.0_1,3']


# ---------------- pkgsrc / pkgin ----------------

def test_pkgsrc_installed(fake_runner):
    fake_runner.expect(['pkgin', 'list'], stdout=(
        "bash-5.2.26 has been installed\n"
        "curl-8.9.1 has been installed\n"
    ))
    pkgs = PkgsrcAdapter().get_installed_packages()
    assert len(pkgs) == 2
    assert pkgs[0].name == 'bash' and pkgs[0].version == '5.2.26'


def test_pkgsrc_search(fake_runner):
    fake_runner.expect(['pkgin', 'search', 'bash'], stdout=(
        "bash-5.2.26      The GNU Bourne Again shell\n"
    ))
    pkgs = PkgsrcAdapter().search_packages('bash')
    assert len(pkgs) == 1 and pkgs[0].name == 'bash' and pkgs[0].version == '5.2.26'


def test_pkgsrc_updates(fake_runner):
    fake_runner.expect(['pkgin', '-n', 'install'], stdout=(
        "bash-5.2.37\n"
        "curl-8.9.2\n"
    ))
    pkgs = PkgsrcAdapter().get_updates_available()
    assert len(pkgs) == 2 and pkgs[0].version == '5.2.37'


# ---------------- Alfa 2: entorno real canned (hyprctl/swaymsg/i3-msg) ------

HYPRLAND_CLIENTS = """[
 {"pid": 1234, "class": "firefox", "title": "GitHub - mozilla"},
 {"pid": 2222, "class": "alacritty", "title": "zsh"}
]"""

SWAY_TREE = """{
 "type": "root", "name": "root", "nodes": [
   {"type": "output", "name": "eDP-1", "nodes": [
     {"type": "workspace", "name": "1", "nodes": [
        {"type": "con", "name": "editor vim", "app_id": "alacritty",
         "pid": 321, "window_properties": {"class": "Alacritty"}}
     ]}
   ]}
 ],
 "floating_nodes": []
}"""


def test_hyprland_list_windows_and_focus(fake_runner):
    from tui_manager.core.environment import HyprlandAdapter
    fake_runner.expect(['hyprctl', '-j', 'clients'], stdout=HYPRLAND_CLIENTS)
    fake_runner.expect(['hyprctl', 'dispatch', 'focuswindow', 'class:firefox'], rc=0)
    env = HyprlandAdapter()
    windows = env.list_windows()
    assert windows[0]['class'] == 'firefox'
    assert env.focus_window('x', cls='firefox') is True


def test_sway_list_windows_and_focus(fake_runner):
    from tui_manager.core.environment import SwayAdapter
    fake_runner.expect(['swaymsg', '-t', 'get_tree', '-r'], stdout=SWAY_TREE)
    fake_runner.expect(['swaymsg', '[class="Alacritty"]', 'focus'], rc=0)
    env = SwayAdapter()
    windows = env.list_windows()
    assert windows[0]['class'] == 'alacritty'
    assert env.focus_window('editor', cls='Alacritty') is True


def test_i3_bspwm_generic_focus(fake_runner, monkeypatch):
    import shutil
    from tui_manager.core.environment import I3Adapter, BspwmAdapter, GenericDEAdapter
    fake_runner.expect(['i3-msg', '[title="Vim"]', 'focus'], rc=0)
    assert I3Adapter().focus_window('Vim') is True
    fake_runner.expect(['bspc', 'node', '-f', 'class=Foo'], rc=0)
    assert BspwmAdapter().focus_window('x', cls='Foo') is True
    # GenericDE necesita wmctrl en el PATH (mockeado)
    monkeypatch.setattr(shutil, 'which',
                        lambda t, *a, **k: '/usr/bin/wmctrl' if t == 'wmctrl' else None)
    fake_runner.expect(['wmctrl', '-l'], rc=0)
    fake_runner.expect(['wmctrl', '-a', 'Nota'], rc=0)
    de = GenericDEAdapter('xfce')
    assert de.list_windows() == []  # salida vacía: lista vacía
    assert de.focus_window('Nota') is True


def test_launch_or_focus_paths(fake_runner):
    from tui_manager.core.environment import launch_or_focus, Capability

    class Env:
        name = 'fake'
        def __init__(self, windows, focus_ok=True, launch_ok=True):
            self.windows = windows
            self.focus_ok = focus_ok
            self.launch_ok = launch_ok
        def capabilities(self):
            caps = {Capability.LAUNCH_APP}
            if self.windows is not None:
                caps.add(Capability.LIST_WINDOWS)
            return caps
        def supports(self, cap):
            return cap in self.capabilities()
        def list_windows(self):
            return self.windows
        def focus_window(self, title, cls=None):
            return self.focus_ok
        def launch_app(self, command):
            return self.launch_ok

    # ya corre → focused
    res = launch_or_focus(Env([{'pid': 1, 'class': 'firefox', 'title': 'X'}]), 'firefox')
    assert res['action'] == 'focused'
    # no corre → launched
    res = launch_or_focus(Env([{'pid': 1, 'class': 'other', 'title': 'X'}]), 'firefox')
    assert res['action'] == 'launched'
    # sin LIST_WINDOWS → launched directo
    res = launch_or_focus(Env(None), 'firefox')
    assert res['action'] == 'launched'
    # focus falla → reintenta como launch
    res = launch_or_focus(Env([{'pid': 1, 'class': 'firefox', 'title': 'X'}],
                              focus_ok=False), 'firefox')
    assert res['action'] == 'launched'
    # nada funciona → failed
    res = launch_or_focus(Env([], launch_ok=False), 'firefox')
    assert res['action'] == 'failed'


def test_hyprland_launch_or_focus_real_flow(fake_runner):
    """Flujo completo A con salidas reales canned de hyprctl."""
    from tui_manager.core.environment import HyprlandAdapter, launch_or_focus
    # firefox ya corre → focus; 'zathura' no → exec
    fake_runner.expect(['hyprctl', '-j', 'clients'], stdout=HYPRLAND_CLIENTS)
    fake_runner.expect(['hyprctl', 'dispatch', 'focuswindow', 'class:firefox'], rc=0)
    assert launch_or_focus(HyprlandAdapter(), 'firefox')['action'] == 'focused'
    fake_runner.expect(['hyprctl', '-j', 'clients'], stdout=HYPRLAND_CLIENTS)
    fake_runner.expect(['hyprctl', 'dispatch', 'exec', 'zathura manual.pdf'], rc=0)
    assert launch_or_focus(HyprlandAdapter(), 'zathura manual.pdf')['action'] == 'launched'


# ---------------- Alfa 3: huérfanos por distro ----------------------------

def test_debian_orphans(fake_runner):
    fake_runner.expect(['apt-get', 'autoremove', '--dry-run'], stdout=(
        "Reading package lists... Done\n"
        "Building dependency tree... Done\n"
        "The following packages will be REMOVED:\n"
        "  libfoo libbar\n"
        "0 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.\n"
        "Remv libfoo [1.2.3]\n"
        "Remv libbar [4.5.6]\n"
    ))
    fake_runner.expect(['sudo', 'apt-get', 'autoremove', '-y'], rc=0,
                        stdout="Removing libfoo...\n")
    adapter = DebianAdapter()
    orphans = adapter.get_orphans()
    assert [p.name for p in orphans] == ['libfoo', 'libbar']
    assert adapter.clean_orphans(confirm=False) is True
    assert ('sudo', 'apt-get', 'autoremove', '-y') in fake_runner.calls


def test_arch_orphans(fake_runner):
    fake_runner.expect(['pacman', '-Qtdq'], stdout="libfoo\nlibbar\n")
    fake_runner.expect(['sudo', 'pacman', '-Rns', '--noconfirm',
                        'libfoo', 'libbar'], rc=0)
    adapter = ArchAdapter()
    assert [p.name for p in adapter.get_orphans()] == ['libfoo', 'libbar']
    assert adapter.clean_orphans(confirm=False) is True


def test_arch_orphans_none(fake_runner):
    fake_runner.expect(['pacman', '-Qtdq'], rc=1)  # rc 1 = sin huérfanos
    adapter = ArchAdapter()
    assert adapter.get_orphans() == []
    assert adapter.clean_orphans(confirm=False) is True  # nada que hacer


def test_fedora_orphans(fake_runner):
    fake_runner.expect(['dnf', 'repoquery', '--unneeded', '--qf', '%{name}'],
                       stdout="libfoo\nlibbar\n")
    fake_runner.expect(['sudo', 'dnf', 'autoremove', '-y'], rc=0)
    adapter = FedoraAdapter()
    assert [p.name for p in adapter.get_orphans()] == ['libfoo', 'libbar']
    assert adapter.clean_orphans(confirm=False) is True


def test_void_orphans(fake_runner):
    fake_runner.expect(['xbps-remove', '-o', '-n'],
                       stdout="libfoo-1.2_1\nlibbar-4.5_1\n")
    fake_runner.expect(['sudo', 'xbps-remove', '-o', '-y'], rc=0)
    adapter = VoidAdapter()
    orphans = adapter.get_orphans()
    assert [(p.name, p.version) for p in orphans] == [
        ('libfoo', '1.2_1'), ('libbar', '4.5_1')]
    assert adapter.clean_orphans(confirm=False) is True


def test_freebsd_orphans(fake_runner, monkeypatch):
    monkeypatch.setattr(FreeBSDAdapter, '_elevator', lambda self: 'sudo')
    fake_runner.expect(['sudo', 'pkg', 'autoremove', '-n'], stdout=(
        "Checking for extra packages...\n"
        "libfoo-1.2.3\n"
        "libbar-4.5\n"
    ))
    fake_runner.expect(['sudo', 'pkg', 'autoremove', '-y'], rc=0)
    adapter = FreeBSDAdapter()
    orphans = adapter.get_orphans()
    assert [p.name for p in orphans] == ['libfoo', 'libbar']
    assert adapter.clean_orphans(confirm=False) is True


def test_base_adapter_orphans_noop():
    """Un adapter sin soporte devuelve vacío y no falla."""
    from tui_manager.core.package_adapter import PackageAdapter
    base = PackageAdapter()
    assert base.get_orphans() == []
    assert base.clean_orphans() is False
