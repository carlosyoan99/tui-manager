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


def test_catalog_growth():
    """El catálogo extendido supera los umbrales e incluye categorías nuevas."""
    assert len(APPS) >= 150
    assert len(CATEGORIES) >= 28
    for category in ('backup', 'monitoring', 'finance', 'writing', 'accessibility'):
        assert category in CATEGORIES


def test_no_duplicate_app_names():
    """El catálogo no debe contener nombres duplicados."""
    from collections import Counter

    names = [app.name for app in APPS]
    duplicates = {name for name, count in Counter(names).items() if count > 1}
    assert not duplicates, f"Nombres duplicados: {sorted(duplicates)}"


def test_all_apps_have_valid_category_y_sources():
    """Toda app pertenece a una categoría y declara fuentes válidas."""
    allowed_sources = {'repo', 'github', 'flatpak', 'snap', 'appimage'}
    for app in APPS:
        assert app.category in CATEGORIES, app.name
        assert app.sources, app.name
        assert set(app.sources) <= allowed_sources, app.name


def test_verified_appimage_urls():
    """Las AppImage verificadas apuntan a un release de GitHub."""
    for name in ('code', 'obsidian', 'joplin', 'keepassxc'):
        app = get_app_by_name(name)
        assert app is not None, name
        url = app.identifiers['appimage']
        assert url.startswith('https://github.com/'), name
        assert '/releases/download/' in url, name


def test_categories_labels_complete():
    """CATEGORIES no tiene ids ni etiquetas vacíos."""
    for key, label in CATEGORIES.items():
        assert key.strip(), 'clave de categoría vacía'
        assert label.strip(), f'etiqueta vacía para {key!r}'


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


# ------------------------------------------- ST-1: validación de fuentes ----

def test_build_sources_uses_shutil_not_subprocess(monkeypatch):
    """Con shutil.which mockeado, build_sources NO llama a subprocess.run."""
    import subprocess
    import tui_manager.core.alternative_sources as mod

    def which(tool, *a, **k):
        return f'/usr/bin/{tool}' if tool in ('pacman', 'flatpak', 'git') else None

    monkeypatch.setattr(mod.shutil, 'which', which)
    monkeypatch.setattr(subprocess, 'run',
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError('subprocess.run no debió llamarse')))

    mgr = AlternativeSourceManager(package_manager='pacman')
    # btop declara repo + github en el catálogo
    assert [s.type for s in mgr.build_sources(get_app_by_name('btop'))] == [
        'repo', 'github']
    # code declara repo + flatpak + snap + appimage; sin snap ni URL de
    # AppImage solo sobreviven repo y flatpak
    assert [s.type for s in mgr.build_sources(get_app_by_name('code'))] == [
        'repo', 'flatpak']


def test_appimage_without_real_url_is_discarded(monkeypatch):
    """Un AppImage con identificador no-URL no se ofrece."""
    import tui_manager.core.alternative_sources as mod
    monkeypatch.setattr(mod.shutil, 'which', lambda t, *a, **k: '/bin/true')

    mgr = AlternativeSourceManager(package_manager='apt')
    app = get_app_by_name('vivaldi')  # tiene 'appimage' sin URL en identifiers
    assert 'appimage' not in app.identifiers
    assert 'appimage' not in [s.type for s in mgr.build_sources(app)]


def test_appimage_with_real_url_is_kept(monkeypatch):
    """Un AppImage con URL http(s) explícita sí se ofrece."""
    import tui_manager.core.alternative_sources as mod
    monkeypatch.setattr(mod.shutil, 'which', lambda t, *a, **k: '/bin/true')

    mgr = AlternativeSourceManager(package_manager='apt')
    source = mod.InstallSource(
        type='appimage', identifier='https://example.com/App.AppImage',
        label='App', command=['wget', 'https://example.com/App.AppImage'],
    )
    assert mgr.validate_sources([source]) == [source]


def test_repo_requires_real_package_manager(monkeypatch):
    """Sin gestor en el PATH no se ofrece la fuente repo."""
    import tui_manager.core.alternative_sources as mod

    class NoManager:
        def get_package_manager(self):
            return 'unknown'

    monkeypatch.setattr(mod.shutil, 'which', lambda t, *a, **k: None)
    mgr = AlternativeSourceManager()
    monkeypatch.setattr(
        'tui_manager.core.distribution.DistributionDetector.get_package_manager',
        NoManager().get_package_manager,
    )
    assert mgr.get_available_tools()['repo'] is False

    monkeypatch.setattr(mod.shutil, 'which',
                        lambda t, *a, **k: '/usr/bin/apt' if t == 'apt' else None)
    mgr2 = AlternativeSourceManager(package_manager='apt')
    assert mgr2.get_available_tools()['repo'] is True


def test_github_needs_git_or_curl(monkeypatch):
    """Sin git ni curl no se ofrece la fuente github."""
    import tui_manager.core.alternative_sources as mod
    monkeypatch.setattr(mod.shutil, 'which', lambda t, *a, **k: None)
    mgr = AlternativeSourceManager(package_manager='apt')
    assert mgr.get_available_tools()['github'] is False


# ------------------------------------------------ ST-2: ejecución segura ----

def test_execute_install_captures_output_and_timeout(monkeypatch, caplog):
    """_execute_install usa capture_output=True y un timeout explícito."""
    import logging
    import subprocess
    from types import SimpleNamespace
    from tui_manager.core.alternative_sources import InstallSource

    caplog.set_level(logging.DEBUG)
    calls = []

    def spy(cmd, **kwargs):
        calls.append((tuple(cmd), kwargs))
        return SimpleNamespace(returncode=0, stdout='ok', stderr='')

    monkeypatch.setattr(subprocess, 'run', spy)
    mgr = AlternativeSourceManager()
    source = InstallSource('github', 'x/y', 'x',
                           ['git', 'clone', 'https://github.com/x/y.git'])

    assert bool(mgr._execute_install(get_app_by_name('btop'), source)) is True
    assert len(calls) == 1
    assert calls[0][1]['capture_output'] is True
    assert calls[0][1]['text'] is True
    assert calls[0][1]['timeout'] == mgr.INSTALL_TIMEOUT
    assert 'instalacion_ok' in caplog.text
    for field in ('app=btop', 'source=github', 'returncode=0',
                  'duracion_ms=', 'exit_code=0'):
        assert field in caplog.text


def test_execute_install_logs_failure_with_tail(monkeypatch, caplog):
    """Un fallo registra returncode/error acotado, sin print de producción."""
    import logging
    import subprocess
    from types import SimpleNamespace
    from tui_manager.core.alternative_sources import InstallSource

    caplog.set_level(logging.DEBUG)
    stderr = '\n'.join(f'línea {i}' for i in range(40))

    def spy(cmd, **kwargs):
        return SimpleNamespace(returncode=7, stdout='', stderr=stderr)

    monkeypatch.setattr(subprocess, 'run', spy)
    mgr = AlternativeSourceManager()
    source = InstallSource('flatpak', 'org.x.Y', 'x',
                           ['flatpak', 'install', '-y', 'org.x.Y'])

    assert bool(mgr._execute_install(get_app_by_name('firefox'), source)) is False
    assert 'instalacion_fallo' in caplog.text
    assert 'returncode=7' in caplog.text
    assert 'exit_code=1' in caplog.text
    assert 'línea 39' in caplog.text      # última línea conservada
    assert 'línea 0' not in caplog.text   # las 20 primeras se descartan


def test_requires_sudo_alias_backwards_compatible():
    """El alias Requires_sudo sigue devolviendo el valor de requires_sudo."""
    from tui_manager.core.alternative_sources import InstallSource
    s = InstallSource('repo', 'apt', 'apt', ['apt'], requires_sudo=True)
    assert s.requires_sudo is True
    assert s.Requires_sudo is True


# ------------------------------------------------ ST-3: InstallResult ----

@pytest.mark.parametrize('src_type,command', [
    ('repo', ['apt', 'install', '-y', 'foo']),
    ('github', ['git', 'clone', 'https://github.com/x/foo.git']),
    ('flatpak', ['flatpak', 'install', '-y', 'org.x.Foo']),
    ('snap', ['snap', 'install', 'foo']),
    ('appimage', ['wget', 'https://example.com/Foo.AppImage']),
])
def test_install_result_on_failure_for_every_source(monkeypatch, src_type, command,
                                                    tmp_path):
    """Fallo simulado en cada fuente: ok False, error y returncode correctos."""
    import subprocess
    from types import SimpleNamespace
    from tui_manager.core.alternative_sources import InstallSource, InstallResult

    monkeypatch.chdir(tmp_path)

    def spy(cmd, **kwargs):
        return SimpleNamespace(returncode=9, stdout='', stderr='fallo simulado')

    monkeypatch.setattr(subprocess, 'run', spy)
    mgr = AlternativeSourceManager()
    source = InstallSource(src_type, 'foo', 'foo', command)

    result = mgr._execute_install(get_app_by_name('firefox'), source)
    assert isinstance(result, InstallResult)
    assert result.ok is False and bool(result) is False
    assert result.returncode == 9
    assert result.error
    assert result.source == src_type
    # rollback conservador: nunca deja directorios creados por el fallo
    assert not any(tmp_path.iterdir())


def test_install_result_on_success_has_actions(monkeypatch, tmp_path):
    """Éxito: ok True, actions con la ejecución registrada."""
    import subprocess
    from types import SimpleNamespace
    from tui_manager.core.alternative_sources import InstallSource, InstallResult

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        subprocess, 'run',
        lambda cmd, **kw: SimpleNamespace(returncode=0, stdout='ok', stderr=''))

    mgr = AlternativeSourceManager()
    source = InstallSource('flatpak', 'org.x.Foo', 'foo',
                           ['flatpak', 'install', '-y', 'org.x.Foo'])
    result = mgr._execute_install(get_app_by_name('firefox'), source)
    assert isinstance(result, InstallResult)
    assert result.ok is True and bool(result) is True
    assert result.returncode == 0
    assert len(result.actions) >= 1
    assert result.error == ''


def test_install_result_bool_keeps_existing_callers():
    """Los callers que hacen `if ok:` siguen funcionando."""
    from tui_manager.core.alternative_sources import InstallResult
    ok = InstallResult(True, 'app', 'repo', 0)
    bad = InstallResult(False, 'app', 'repo', 1, error='x')
    assert ok and not bad


def test_repo_available_with_alternative_manager_binary(monkeypatch):
    """Void tiene xbps-query, no xbps: la fuente repo debe seguir disponible."""
    import tui_manager.core.alternative_sources as mod
    monkeypatch.setattr(
        mod.shutil, 'which',
        lambda tool, *a, **k: '/usr/bin/xbps-query' if tool == 'xbps-query' else None)

    mgr = AlternativeSourceManager(package_manager='xbps')
    assert mgr.get_available_tools()['repo'] is True
    sources = mgr.build_sources(get_app_by_name('firefox'))
    assert any(s.type == 'repo' for s in sources)
