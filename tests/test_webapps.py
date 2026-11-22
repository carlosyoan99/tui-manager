"""
Tests de webapps ligeras (función G).

Todo es local y simulado: se inyecta ``base_dir=tmp_path``, se falsifica
``platform.system`` y no se ejecuta ningún navegador ni comando de red.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tui_manager.core import webapps as webapps_module
from tui_manager.core.webapps import (
    WEBAPPS,
    WebApp,
    create_webapp_desktop_entry,
)


WEBAPP_I18N_KEYS = (
    'menu.apps.webapps',
    'webapps.title',
    'webapps.search',
    'webapps.all',
    'webapps.status',
    'webapps.create',
    'webapps.create_confirm',
    'webapps.created',
    'webapps.failed',
    'webapps.open',
    'webapps.opening',
    'webapps.unavailable',
)


def _fake_system(monkeypatch, name: str) -> None:
    """Sustituye solo la referencia de platform en core.webapps."""
    monkeypatch.setattr(webapps_module, 'platform',
                        SimpleNamespace(system=lambda: name))


# --------------------------------------------------------------- catálogo --

def test_webapp_catalog_is_small_and_https_only():
    assert 10 <= len(WEBAPPS) <= 15
    assert len({app.name for app in WEBAPPS}) == len(WEBAPPS)
    for app in WEBAPPS:
        assert isinstance(app, WebApp)
        assert app.name and app.category and app.icon_hint
        assert app.url.startswith('https://')


# ------------------------------------------------------------ generación --

def test_desktop_entry_linux(tmp_path, monkeypatch):
    _fake_system(monkeypatch, 'Linux')
    path = create_webapp_desktop_entry(
        'GitHub', 'https://github.com', browser='firefox', base_dir=tmp_path)

    assert path == tmp_path / 'GitHub.desktop'
    text = path.read_text(encoding='utf-8')
    assert '[Desktop Entry]' in text
    assert 'Type=Application' in text
    assert 'Name=GitHub' in text
    assert 'Exec=firefox https://github.com' in text
    assert 'Terminal=false' in text
    assert 'web-browser' in text
    assert list(tmp_path.iterdir()) == [path]


def test_desktop_entry_freebsd_uses_xdg_open_by_default(tmp_path, monkeypatch):
    _fake_system(monkeypatch, 'FreeBSD')
    path = create_webapp_desktop_entry(
        'Wikipedia', 'https://en.wikipedia.org', base_dir=tmp_path)

    assert path.suffix == '.desktop'
    assert 'Exec=xdg-open https://en.wikipedia.org' in path.read_text(
        encoding='utf-8')


def test_shortcut_windows(tmp_path, monkeypatch):
    _fake_system(monkeypatch, 'Windows')
    path = create_webapp_desktop_entry(
        'YouTube', 'https://www.youtube.com', browser='msedge',
        base_dir=tmp_path)

    assert path == tmp_path / 'YouTube.url'
    text = path.read_text(encoding='utf-8')
    assert '[InternetShortcut]' in text
    assert 'URL=https://www.youtube.com' in text
    assert 'IconFile=msedge' in text
    assert 'Exec=' not in text


def test_applescript_macos_uses_open_a(tmp_path, monkeypatch):
    _fake_system(monkeypatch, 'Darwin')
    path = create_webapp_desktop_entry(
        'Spotify Web', 'https://open.spotify.com', browser='Firefox',
        base_dir=tmp_path)

    assert path == tmp_path / 'Spotify Web.applescript'
    text = path.read_text(encoding='utf-8')
    assert 'open -a' in text
    assert 'Firefox' in text
    assert 'https://open.spotify.com' in text
    assert not any(ord(ch) < 32 and ch != '\n' for ch in text)


def test_desktop_entry_escapes_browser_with_arguments(tmp_path, monkeypatch):
    _fake_system(monkeypatch, 'Linux')
    path = create_webapp_desktop_entry(
        'Notion', 'https://www.notion.so',
        browser="'/opt/My Browser' --new-window", base_dir=tmp_path)

    text = path.read_text(encoding='utf-8')
    exec_line = text.split('Exec=', 1)[1].split('\n', 1)[0]
    assert exec_line == "'/opt/My Browser' --new-window https://www.notion.so"
    assert '\n' not in exec_line


# ------------------------------------------------------------ validación --

@pytest.mark.parametrize('bad_url', [
    'http://example.com',
    'javascript:alert(1)',
    'file:///etc/passwd',
    'https://',
    'https:///sin-host',
    'https://user:pass@example.com',
    'https://exa mple.com',
    'https://example.com/\nX-Evil: 1',
])
def test_rejects_non_https_or_unsafe_urls(tmp_path, monkeypatch, bad_url):
    _fake_system(monkeypatch, 'Linux')
    with pytest.raises(ValueError):
        create_webapp_desktop_entry('GitHub', bad_url, base_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('bad_name', [
    '',
    '   ',
    '.',
    '..',
    '../escape',
    'a/b',
    'a\\b',
    'a\x00b',
    'name?query',
    'name\nExec=rm',
    ' ../otro',
])
def test_rejects_unsafe_names(tmp_path, monkeypatch, bad_name):
    _fake_system(monkeypatch, 'Linux')
    with pytest.raises(ValueError):
        create_webapp_desktop_entry(
            bad_name, 'https://github.com', base_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_rejects_browser_with_newline(tmp_path, monkeypatch):
    _fake_system(monkeypatch, 'Linux')
    with pytest.raises(ValueError):
        create_webapp_desktop_entry(
            'GitHub', 'https://github.com', browser='firefox\nExec=rm',
            base_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_never_writes_outside_injected_dir(tmp_path, monkeypatch):
    _fake_system(monkeypatch, 'Linux')
    base = tmp_path / 'applications'
    base.mkdir()
    with pytest.raises(ValueError):
        create_webapp_desktop_entry(
            '../escape', 'https://example.com', base_dir=base)
    assert not (tmp_path / 'escape.desktop').exists()
    assert list(base.iterdir()) == []

    # Un nombre válido escribe exactamente un archivo dentro del subdirectorio.
    path = create_webapp_desktop_entry(
        'Figma', 'https://www.figma.com', base_dir=base)
    assert path.parent == base
    assert sorted(p.name for p in tmp_path.iterdir()) == ['applications']


# ------------------------------------------------------------------ i18n --

@pytest.mark.parametrize('lang', ['es', 'en'])
def test_webapps_i18n_keys_are_inside_each_dict(lang):
    from tui_manager.i18n import STRINGS

    strings = STRINGS[lang]
    for key in WEBAPP_I18N_KEYS:
        assert key in strings, f'{key} falta en {lang}'


def test_webapps_t_returns_translations():
    from tui_manager.i18n import get_language, set_language, t

    original = get_language()
    try:
        set_language('es')
        assert t('webapps.created', name='GitHub') == (
            'Acceso directo creado: GitHub')
        assert t('webapps.status', n=3, category='todas') == (
            '3 webapps · todas')
        set_language('en')
        assert t('webapps.created', name='GitHub') == (
            'Shortcut created: GitHub')
        assert t('webapps.status', n=3, category='all') == (
            '3 web apps · all')
    finally:
        set_language(original)


# -------------------------------------------------------------- menú 10 ----

def test_menu_keeps_ten_entries_and_numeric_shortcuts():
    from tui_manager.ui.screens import AppsScreen, MainMenuScreen

    assert len(MainMenuScreen.ENTRIES) == 10
    assert [entry[1] for entry in MainMenuScreen.ENTRIES] == [
        'PackagesScreen', 'ProcessesScreen', 'SystemScreen', 'ThemesScreen',
        'UpdatesScreen', 'SettingsScreen', 'HelpScreen', 'AboutScreen',
        'LogsScreen', 'AppsScreen',
    ]
    assert [MainMenuScreen.shortcut(i) for i in range(10)] == [
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

    keys = {(b.key if hasattr(b, 'key') else b[0]):
            (b.action if hasattr(b, 'action') else b[1])
            for b in AppsScreen.BINDINGS}
    assert keys.get('w') == 'webapps'
    assert callable(AppsScreen.action_webapps)


# --------------------------------------------------------------------- UI --

class _MinimalPackageManager:
    def get_installed_packages(self, **kwargs):
        return []


def _services(tmp_path):
    from tui_manager.core.config import Config
    from tui_manager.ui.app import Services

    return Services(
        config=Config(config_file=str(tmp_path / 'config.yaml')),
        package_manager=_MinimalPackageManager(),
    )


@pytest.mark.asyncio
async def test_webapps_screen_lists_filters_and_creates_shortcut(
        tmp_path, monkeypatch):
    from textual.widgets import Input, ListView, LoadingIndicator

    from tui_manager.ui.app import TuiManagerApp
    from tui_manager.ui.screens import ConfirmScreen
    from tui_manager.ui.webapps_screen import WebAppsScreen

    _fake_system(monkeypatch, 'Linux')
    services = _services(tmp_path)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        app.push_screen(WebAppsScreen(services, base_dir=tmp_path))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WebAppsScreen)
        view = screen.query_one('#webapps-list', ListView)
        assert len(view.children) == len(WEBAPPS)
        assert screen.query_one('#webapps-loading', LoadingIndicator).display is False

        screen.query_one('#webapps-search', Input).value = 'github'
        await pilot.pause()
        assert [app.name for app in screen._visible] == ['GitHub']
        assert len(view.children) == 1
        view.focus()
        view.index = 0
        await pilot.pause()

        await pilot.press('enter')
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)

        await pilot.press('y')
        for _ in range(40):
            await pilot.pause(0.02)
            if (tmp_path / 'GitHub.desktop').exists():
                break
        assert (tmp_path / 'GitHub.desktop').exists()
        assert 'https://github.com' in (tmp_path / 'GitHub.desktop').read_text()
        assert screen.query_one('#webapps-loading', LoadingIndicator).display is False
        assert isinstance(app.screen, WebAppsScreen)


@pytest.mark.asyncio
async def test_apps_screen_w_opens_webapps_without_changing_menu(
        tmp_path, monkeypatch):
    from textual.widgets import ListView

    from tui_manager.ui.app import TuiManagerApp
    from tui_manager.ui.screens import AppsScreen
    from tui_manager.ui.webapps_screen import WebAppsScreen

    _fake_system(monkeypatch, 'Linux')
    services = _services(tmp_path)
    app = TuiManagerApp(services)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen.query_one('#menu', ListView), ListView)
        app.push_screen(AppsScreen(services))
        await pilot.pause()
        assert isinstance(app.screen, AppsScreen)
        await pilot.press('w')
        await pilot.pause()
        assert isinstance(app.screen, WebAppsScreen)
