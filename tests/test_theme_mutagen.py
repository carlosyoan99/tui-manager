"""
Tests del tema dinámico matugen (subtarea 1.1-E).

Todo se simula en ``tmp_path``: no se toca el HOME real ni se usa red.
"""

import json

from tui_manager.ui.theme_mutagen import load_matugen_theme, to_textual_palette
from tui_manager.core.config import Config


MATUGEN_JSON = {
    "name": "matugen",
    "defs": {
        "primary": "#06207a",
        "on_primary": "#f9fafa",
        "secondary": "#21056b",
        "on_secondary": "#f9fafa",
        "surface": "#cfd9fc",
        "on_surface": "#18191b",
        "background": "#cfd9fc",
        "on_background": "#18191b",
        "error": "#fd4663",
        "on_error": "#f9fafa",
        "outline": "#6b7aaa",
    },
    "theme": {
        "primary": {"dark": "primary", "light": "primary"},
        "text": {"dark": "on_surface", "light": "on_surface"},
    },
}


def _write_theme(tmp_path, data=MATUGEN_JSON):
    path = tmp_path / 'matugen.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


def test_load_matugen_theme_from_path(tmp_path):
    """Carga correcta de un JSON matugen simulado."""
    path = _write_theme(tmp_path)
    theme = load_matugen_theme(str(path))
    assert theme is not None
    assert theme['defs']['primary'] == '#06207a'
    assert theme['theme']['text']['dark'] == 'on_surface'


def test_to_textual_palette_maps_defs():
    """Los defs se traducen a nombres de estilo de textual."""
    palette = to_textual_palette(MATUGEN_JSON['defs'])

    assert palette['primary'] == '#06207a'
    assert palette['secondary'] == '#21056b'
    assert palette['surface'] == '#cfd9fc'
    assert palette['background'] == '#cfd9fc'
    assert palette['text'] == '#18191b'  # on_surface
    assert palette['error'] == '#fd4663'
    # warning/success derivados de secondary cuando no están en defs
    assert palette['warning'] == '#21056b'
    assert palette['success'] == '#21056b'


def test_palette_detects_light_and_dark_from_background():
    """La luminosidad del fondo decide el flag `dark`."""
    defs = dict(MATUGEN_JSON['defs'])

    defs['background'] = '#101010'
    assert to_textual_palette(defs)['dark'] is True

    defs['background'] = '#fafafa'
    assert to_textual_palette(defs)['dark'] is False


def test_invalid_defs_do_not_raise():
    """Una entrada inválida devuelve una paleta usable, nunca falla."""
    palette = to_textual_palette(None)
    assert isinstance(palette, dict)
    assert {'primary', 'secondary', 'text', 'error'} <= set(palette)


def test_load_missing_file_returns_none(tmp_path):
    """Fallo graceful si el archivo no existe."""
    assert load_matugen_theme(str(tmp_path / 'no-existe.json')) is None


def test_load_invalid_json_returns_none(tmp_path):
    """Fallo graceful con JSON corrupto o con un tipo inesperado."""
    bad = tmp_path / 'malo.json'
    bad.write_text('{ esto no es json', encoding='utf-8')
    assert load_matugen_theme(str(bad)) is None

    not_dict = tmp_path / 'lista.json'
    not_dict.write_text('[1, 2, 3]', encoding='utf-8')
    assert load_matugen_theme(str(not_dict)) is None


def test_theme_source_config_default_and_persisted(tmp_path):
    """La opción theme_source se guarda y se relee de config.yaml."""
    config_file = str(tmp_path / 'config.yaml')
    cfg = Config(config_file=config_file)
    assert cfg.get_theme_source() == 'manual'

    cfg.set_theme_source('mutagen')
    assert cfg.get_theme_source() == 'mutagen'

    cfg2 = Config(config_file=config_file)
    assert cfg2.get('theme_source') == 'mutagen'
    assert cfg2.get_theme_source() == 'mutagen'

    # Un valor inválido cae de vuelta a manual.
    cfg2.set_theme_source('raro')
    assert cfg2.get_theme_source() == 'manual'


def test_end_to_end_load_and_map(tmp_path):
    """Del JSON simulado a la paleta textual, sin archivos reales."""
    path = _write_theme(tmp_path)
    theme = load_matugen_theme(str(path))
    palette = to_textual_palette(theme['defs'])
    assert palette['primary'] == '#06207a'
    assert palette['dark'] is False  # background #cfd9fc es claro
