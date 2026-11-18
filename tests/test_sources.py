"""
Tests del catálogo de apps y gestor de fuentes alternativas (Alfa 3).
"""

import pytest

from tui_manager.core.app_catalog import (
    APPS, CATEGORIES, get_app_by_name, search_apps,
    get_apps_by_category, get_all_categories,
)
from tui_manager.core.alternative_sources import (
    AlternativeSourceManager, InstallSource, InstallationCancelled,
)
from tui_manager.core.sources_adapter import SourcesAdapter


# ------------------------------------------------------------- catálogo ----

def test_catalog_has_many_apps_and_categories():
    assert len(APPS) >= 70
    assert len(CATEGORIES) >= 20
    assert 'development' in CATEGORIES and 'ai' in CATEGORIES
    assert 'fonts' in CATEGORIES and 'themes' in CATEGORIES


def test_get_app_by_name():
    app = get_app_by_name('firefox')
    assert app is not None and app.category == 'web'
    assert 'flatpak' in app.sources
    assert get_app_by_name('no-existe-xyz') is None


def test_search_apps():
    results = search_apps('editor')
    assert results
    assert any(a.name == 'code' for a in results) or any('neovim' == a.name for a in results)


def test_get_apps_by_category():
    web = get_apps_by_category('web')
    assert web and all(a.category == 'web' for a in web)
    assert get_apps_by_category('all') is APPS
    assert get_all_categories()['web'] == 'Navegadores y Web'


def test_apps_with_alternative_sources():
    """Varias apps deben tener fuentes no oficiales declaradas."""
    alternatives = [a for a in APPS if any(s != 'repo' for s in a.sources)]
    assert len(alternatives) >= 20
    code = get_app_by_name('code')
    assert set(code.sources) >= {'repo', 'flatpak', 'snap', 'appimage'}


# ------------------------------------------------------------- fuentes ----

def _manager(tools, prefs=None):
    """Crea un manager con herramientas y preferencias simuladas."""
    class FakeConfig:
        def get(self, key, default=None):
            return prefs.get(key, default) if prefs else default
        def set(self, key, value):
            if prefs is not None:
                prefs[key] = value
    mgr = AlternativeSourceManager(config=FakeConfig())
    mgr.get_available_tools = lambda: tools
    return mgr


def test_build_sources_respects_available_tools():
    mgr = _manager({'repo': True, 'flatpak': True, 'snap': False,
                    'github': False, 'appimage': False})
    sources = mgr.build_sources(get_app_by_name('firefox'))
    types = [s.type for s in sources]
    assert types == ['repo', 'flatpak']


def test_select_source_single_official_no_confirmation():
    mgr = _manager({'repo': True, 'flatpak': False, 'snap': False,
                    'github': False, 'appimage': False})
    sources = mgr.build_sources(get_app_by_name('git'))
    chosen = mgr.select_source(get_app_by_name('git'))
    assert chosen.type == 'repo'


def test_select_source_prefers_configured_format(monkeypatch):
    mgr = _manager({'repo': True, 'flatpak': True, 'snap': False,
                    'github': False, 'appimage': False},
                   prefs={'preferred_install_method': 'flatpak'})
    confirmed = []
    mgr.confirm_callback = lambda msg: confirmed.append(msg) or True
    chosen = mgr.select_source(get_app_by_name('firefox'))
    assert chosen.type == 'flatpak'
    assert confirmed


def test_select_source_asks_when_multiple(monkeypatch):
    mgr = _manager({'repo': True, 'flatpak': True, 'snap': True,
                    'github': True, 'appimage': True})
    mgr.select_callback = lambda msg, opts: opts[0]
    mgr.confirm_callback = lambda msg: True
    chosen = mgr.select_source(get_app_by_name('code'))
    assert chosen is not None
    assert chosen.type == 'repo'


def test_alternative_source_requires_confirmation():
    """Una fuente no oficial debe pedir confirmación y poder cancelarse."""
    mgr = _manager({'repo': True, 'flatpak': True, 'snap': False,
                    'github': False, 'appimage': False})
    mgr.select_callback = lambda msg, opts: opts[1]  # flatpak
    mgr.confirm_callback = lambda msg: False
    assert mgr.select_source(get_app_by_name('firefox')) is None


def test_source_summary_and_has_alternatives():
    mgr = _manager({'repo': True, 'flatpak': True, 'snap': False,
                    'github': False, 'appimage': False})
    app = get_app_by_name('firefox')
    assert 'repo' in mgr.get_source_summary(app)
    assert mgr.has_alternative_sources(app) is True


# ------------------------------------------------------------- adaptador ----

def test_sources_adapter_list_and_sources():
    class FakeConfig:
        def get(self, key, default=None):
            return 'auto'
        def set(self, key, value):
            pass
    adapter = SourcesAdapter(FakeConfig())
    apps = adapter.list_apps('web')
    assert apps and all(a.category == 'web' for a in apps)
    filtered = adapter.list_apps('all', 'firefox')
    assert any(a.name == 'firefox' for a in filtered)
    srcs = adapter.sources_for(get_app_by_name('firefox'))
    assert srcs
    assert adapter.has_alternatives(get_app_by_name('code')) is True
    assert adapter.preferred_format() == 'auto'
