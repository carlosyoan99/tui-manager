"""
Tests 100% simulados de los adapters de macOS (Homebrew) y Windows
(winget / scoop / choco). No se ejecuta ningún gestor real en estos hosts:
subprocess.run se sustituye por ``fake_runner`` y shutil.which por un stub.
"""

import os
import platform
import shutil
import subprocess

import pytest

from tui_manager.core.macos_adapter import MacOSAdapter
from tui_manager.core.windows_adapter import WindowsAdapter
from tui_manager.core.package_adapter import PackageNotFoundError
from tui_manager.core.distribution import DistributionDetector
from tui_manager.core.package_manager import PackageManager


@pytest.fixture
def only_which(monkeypatch):
    """Simula qué gestores de Windows están presentes en PATH."""
    def _set(*available):
        def which(cmd, *args, **kwargs):
            return f'C:\\Tools\\{cmd}.exe' if cmd in available else None
        monkeypatch.setattr(shutil, 'which', which)
    return _set


def _isolated_detect(monkeypatch, system):
    """Aísla detect() de /etc/*, lsb_release y variables de Termux."""
    monkeypatch.delenv('TERMUX_VERSION', raising=False)
    monkeypatch.setenv('PREFIX', '/usr')
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    monkeypatch.setattr(platform, 'system', lambda: system)

    def no_run(*args, **kwargs):
        raise FileNotFoundError('lsb_release')
    monkeypatch.setattr(subprocess, 'run', no_run)


# ---------------- macOS / Homebrew ----------------

def test_macos_installed(fake_runner):
    fake_runner.expect(['brew', 'list', '--formula', '--versions'], stdout=(
        "curl 8.4.0\n"
        "git 2.42.0\n"
        "python@3.12 3.12.0\n"
    ))
    pkgs = MacOSAdapter().get_installed_packages()
    assert [p.name for p in pkgs] == ['curl', 'git', 'python@3.12']
    assert [p.version for p in pkgs] == ['8.4.0', '2.42.0', '3.12.0']
    assert all(p.installed for p in pkgs)
    assert fake_runner.calls == [('brew', 'list', '--formula', '--versions')]


def test_macos_installed_name_only(fake_runner):
    """brew list --formula sin --versions también es parseable."""
    fake_runner.expect(['brew', 'list', '--formula', '--versions'],
                       stdout="curl\ngit\n")
    pkgs = MacOSAdapter().get_installed_packages()
    assert [p.name for p in pkgs] == ['curl', 'git']
    assert all(p.version == '' for p in pkgs)


def test_macos_installed_error(fake_runner):
    fake_runner.expect(['brew', 'list', '--formula', '--versions'],
                       rc=1, stderr='Error: no formula')
    assert MacOSAdapter().get_installed_packages() == []


def test_macos_search(fake_runner):
    fake_runner.expect(['brew', 'search', 'curl'], stdout=(
        "==> Formulae\n"
        "curl\n"
        "curlftpfs\n"
        "\n"
        "==> Casks\n"
        "curl\n"
    ))
    pkgs = MacOSAdapter().search_packages('curl')
    assert [p.name for p in pkgs] == ['curl', 'curlftpfs', 'curl']
    assert all(not p.installed for p in pkgs)


def test_macos_info_and_dependencies(fake_runner):
    fake_runner.expect(['brew', 'info', 'curl'], stdout=(
        "curl: stable 8.4.0 (bottled), HEAD\n"
        "Get a file from an HTTP, HTTPS or FTP server\n"
        "https://curl.se\n"
        "==> Dependencies\n"
        "Required: brotli ✔, libssh2 ✔, openssl@3 ✔\n"
        "Build: pkg-config ✔\n"
    ))
    adapter = MacOSAdapter()
    info = adapter.get_package_info('curl')
    assert info.name == 'curl'
    assert info.version == '8.4.0'
    assert 'Get a file' in info.description
    assert info.dependencies == ['brotli', 'libssh2', 'openssl@3', 'pkg-config']
    assert adapter.get_dependencies('curl') == info.dependencies
    assert fake_runner.calls == [('brew', 'info', 'curl')] * 2


def test_macos_info_not_found(fake_runner):
    fake_runner.expect(['brew', 'info', 'nope'], rc=1, stderr='Error: no formula')
    with pytest.raises(PackageNotFoundError):
        MacOSAdapter().get_package_info('nope')
    assert MacOSAdapter().get_dependencies('nope') == []


def test_macos_updates(fake_runner):
    fake_runner.expect(['brew', 'outdated'], stdout=(
        "curl (8.4.0) < 8.5.0\n"
        "git (2.42.0) < 2.43.0\n"
    ))
    pkgs = MacOSAdapter().get_updates_available()
    assert [p.name for p in pkgs] == ['curl', 'git']
    assert [p.version for p in pkgs] == ['8.5.0', '2.43.0']
    assert all(p.installed for p in pkgs)


def test_macos_mutations_are_sudo_free(fake_runner):
    fake_runner.expect(['brew', 'install', 'curl'], rc=0)
    fake_runner.expect(['brew', 'uninstall', 'curl'], rc=0)
    fake_runner.expect(['brew', 'update'], rc=0)
    fake_runner.expect(['brew', 'upgrade'], rc=0)
    adapter = MacOSAdapter()
    assert adapter.install_package('curl', confirm=False) is True
    assert adapter.remove_package('curl', confirm=False) is True
    assert adapter.update_cache() is True
    assert adapter.upgrade_all() is True
    assert fake_runner.calls == [
        ('brew', 'install', 'curl'), ('brew', 'uninstall', 'curl'),
        ('brew', 'update'), ('brew', 'upgrade'),
    ]
    assert all('sudo' not in call for call in fake_runner.calls)


def test_macos_failed_mutation(fake_runner):
    fake_runner.expect(['brew', 'install', 'x'], rc=1, stderr='boom')
    assert MacOSAdapter().install_package('x', confirm=False) is False


def test_macos_orphans_cleanup_services(fake_runner):
    fake_runner.expect(['brew', 'autoremove', '--dry-run'], stdout=(
        "==> Would uninstall:\n"
        "  cmake\n"
        "  openssl@3\n"
    ))
    fake_runner.expect(['brew', 'autoremove'], rc=0)
    fake_runner.expect(['brew', 'cleanup'], rc=0)
    fake_runner.expect(['brew', 'services', 'list'], stdout=(
        "Name  Status  User\n"
        "nginx started carlos\n"
    ))
    adapter = MacOSAdapter()
    assert [p.name for p in adapter.get_orphans()] == ['cmake', 'openssl@3']
    assert adapter.clean_orphans(confirm=False) is True
    assert adapter.cleanup() is True
    services = adapter.get_services()
    assert services[0].name == 'nginx' and services[0].description == 'started'


def test_macos_ignores_sudo_flag(fake_runner):
    fake_runner.expect(['brew', 'list', '--formula', '--versions'],
                       stdout="curl 8.4.0\n")
    rc, stdout, stderr = MacOSAdapter().execute_command(
        ['brew', 'list', '--formula', '--versions'], sudo=True)
    assert rc == 0 and 'curl' in stdout
    assert fake_runner.calls == [('brew', 'list', '--formula', '--versions')]


# ---------------- Windows / gestores ----------------

def test_windows_detect_manager_precedence(only_which):
    only_which('winget', 'scoop', 'choco')
    assert WindowsAdapter().manager == 'winget'
    only_which('scoop', 'choco')
    assert WindowsAdapter().manager == 'scoop'
    only_which('choco')
    assert WindowsAdapter().manager == 'choco'


def test_windows_defaults_to_winget_and_allows_override(only_which):
    only_which()
    assert WindowsAdapter().manager == 'winget'
    assert WindowsAdapter(manager='choco').manager == 'choco'
    with pytest.raises(ValueError):
        WindowsAdapter(manager='npm')


def test_winget_installed(fake_runner, only_which):
    only_which('winget')
    fake_runner.expect(['winget', 'list'], stdout=(
        "Name                    Id                      Version      Available   Source\n"
        "--------------------------------------------------------------------------------\n"
        "Microsoft Edge          Microsoft.Edge          127.0.2651   128.0.2739  winget\n"
        "7-Zip                   7zip.7zip               23.01                    winget\n"
    ))
    pkgs = WindowsAdapter().get_installed_packages()
    assert [p.name for p in pkgs] == ['Microsoft Edge', '7-Zip']
    assert [p.version for p in pkgs] == ['127.0.2651', '23.01']
    assert all(p.installed for p in pkgs)


def test_winget_search_and_info(fake_runner, only_which):
    only_which('winget')
    fake_runner.expect(['winget', 'search', 'curl'], stdout=(
        "Name              Id                Version   Match              Source\n"
        "-----------------------------------------------------------------------\n"
        "curl              curl.curl         8.4.0     curl               winget\n"
    ))
    pkgs = WindowsAdapter().search_packages('curl')
    assert len(pkgs) == 1
    assert pkgs[0].name == 'curl' and pkgs[0].version == '8.4.0'
    assert 'curl' in pkgs[0].description and not pkgs[0].installed

    fake_runner.expect(['winget', 'show', 'Microsoft.Edge'], stdout=(
        "Found package(s): 1\n"
        "\n"
        "Name            : Microsoft Edge\n"
        "Id              : Microsoft.Edge\n"
        "Version         : 127.0.2651.74\n"
        "Description     : The Microsoft Edge browser\n"
        "Dependencies    : Microsoft.EdgeWebView2, VC++ 2022\n"
    ))
    info = WindowsAdapter().get_package_info('Microsoft.Edge')
    assert info.name == 'Microsoft Edge'
    assert info.version == '127.0.2651.74'
    assert 'Microsoft Edge browser' in info.description
    assert info.dependencies == ['Microsoft.EdgeWebView2', 'VC++ 2022']


def test_winget_info_not_found(fake_runner, only_which):
    only_which('winget')
    fake_runner.expect(['winget', 'show', 'nope'], rc=1,
                       stderr='No package found')
    with pytest.raises(PackageNotFoundError):
        WindowsAdapter().get_package_info('nope')


def test_winget_updates(fake_runner, only_which):
    only_which('winget')
    fake_runner.expect(['winget', 'upgrade'], stdout=(
        "Name            Id                   Version   Available   Source\n"
        "------------------------------------------------------------------\n"
        "Microsoft Edge  Microsoft.Edge       127.0     128.0       winget\n"
    ))
    pkgs = WindowsAdapter().get_updates_available()
    assert pkgs[0].name == 'Microsoft Edge' and pkgs[0].version == '128.0'


def test_scoop_installed_info_and_updates(fake_runner, only_which):
    only_which('scoop')
    fake_runner.expect(['scoop', 'list'], stdout=(
        "Name       Version   Source\n"
        "----       -------   ------\n"
        "7zip       23.01     main\n"
    ))
    pkgs = WindowsAdapter().get_installed_packages()
    assert pkgs[0].name == '7zip' and pkgs[0].version == '23.01'

    fake_runner.expect(['scoop', 'info', '7zip'], stdout=(
        "Name: 7zip\n"
        "Version: 23.01\n"
        "Description: 7-Zip file archiver\n"
    ))
    info = WindowsAdapter().get_package_info('7zip')
    assert info.version == '23.01' and 'archiver' in info.description

    fake_runner.expect(['scoop', 'status'], stdout=(
        "Name     Installed   Latest   Age\n"
        "7zip     23.01       23.02    3d\n"
    ))
    updates = WindowsAdapter().get_updates_available()
    assert updates[0].name == '7zip' and updates[0].version == '23.02'


def test_choco_installed_info_and_updates(fake_runner, only_which):
    only_which('choco')
    fake_runner.expect(['choco', 'list', '--local-only'], stdout=(
        "Chocolatey v2.2.0\n"
        "7zip 23.01.0.2301\n"
        "curl 8.4.0\n"
        "2 packages installed.\n"
    ))
    pkgs = WindowsAdapter().get_installed_packages()
    assert [p.name for p in pkgs] == ['7zip', 'curl']
    assert pkgs[0].version == '23.01.0.2301'

    fake_runner.expect(['choco', 'info', '7zip'], stdout=(
        "7zip 23.01.0.2301\n"
        "Description: 7-Zip archiver\n"
    ))
    info = WindowsAdapter().get_package_info('7zip')
    assert info.version == '23.01.0.2301' and 'archiver' in info.description

    fake_runner.expect(['choco', 'outdated'], stdout=(
        "7zip|23.01.0.2301|23.02.0.2301\n"
        "curl|8.4.0|8.5.0\n"
    ))
    updates = WindowsAdapter().get_updates_available()
    assert [p.version for p in updates] == ['23.02.0.2301', '8.5.0']


@pytest.mark.parametrize('manager,install,remove,cache,upgrade', [
    ('winget',
     ['winget', 'install', '--id', 'curl', '-e',
      '--accept-package-agreements', '--accept-source-agreements'],
     ['winget', 'uninstall', '--id', 'curl'],
     ['winget', 'source', 'update'],
     ['winget', 'upgrade', '--all',
      '--accept-package-agreements', '--accept-source-agreements']),
    ('scoop',
     ['scoop', 'install', 'curl'], ['scoop', 'uninstall', 'curl'],
     ['scoop', 'update'], ['scoop', 'update', '*']),
    ('choco',
     ['choco', 'install', 'curl', '-y'],
     ['choco', 'uninstall', 'curl', '-y'],
     ['choco', 'update'], ['choco', 'upgrade', 'all', '-y']),
])
def test_windows_mutations_are_sudo_free(
        fake_runner, only_which, manager, install, remove, cache, upgrade):
    only_which(manager)
    for command in (install, remove, cache, upgrade):
        fake_runner.expect(command, rc=0)
    adapter = WindowsAdapter()
    assert adapter.install_package('curl', confirm=False) is True
    assert adapter.remove_package('curl', confirm=False) is True
    assert adapter.update_cache() is True
    assert adapter.upgrade_all() is True
    assert fake_runner.calls == [tuple(c) for c in
                                 (install, remove, cache, upgrade)]
    assert all('sudo' not in call for call in fake_runner.calls)


def test_windows_failed_mutation(fake_runner, only_which):
    only_which('scoop')
    fake_runner.expect(['scoop', 'install', 'x'], rc=1, stderr='boom')
    assert WindowsAdapter().install_package('x', confirm=False) is False


def test_windows_ignores_sudo_flag(fake_runner, only_which):
    only_which('winget')
    fake_runner.expect(['winget', 'list'], stdout="7-Zip  23.01\n")
    rc, stdout, stderr = WindowsAdapter().execute_command(
        ['winget', 'list'], sudo=True)
    assert rc == 0 and '7-Zip' in stdout
    assert fake_runner.calls == [('winget', 'list')]


# ---------------- Detección y selección ----------------

@pytest.mark.parametrize('system,distro,pm', [
    ('Darwin', 'darwin', 'brew'),
    ('Windows', 'windows', 'winget'),
])
def test_detect_macos_windows(monkeypatch, system, distro, pm):
    _isolated_detect(monkeypatch, system)
    assert DistributionDetector.detect() == distro
    assert DistributionDetector.get_package_manager() == pm
    assert DistributionDetector.is_supported() is True


def test_supported_includes_macos_windows():
    supported = DistributionDetector.get_supported_distributions()
    assert {'darwin', 'macos', 'windows'} <= set(supported)


def test_package_manager_maps_macos_windows():
    from tui_manager.core.distribution import DistributionDetector as DD
    assert DD._PACKAGE_MANAGERS['darwin'] == 'brew'
    assert DD._PACKAGE_MANAGERS['macos'] == 'brew'
    assert DD._PACKAGE_MANAGERS['windows'] == 'winget'


@pytest.mark.parametrize('distro,adapter_class', [
    ('darwin', MacOSAdapter),
    ('macos', MacOSAdapter),
    ('windows', WindowsAdapter),
])
def test_package_manager_selects_new_adapters(distro, adapter_class, only_which):
    only_which('winget')
    pm = PackageManager(distribution=distro)
    assert type(pm.adapter) is adapter_class
