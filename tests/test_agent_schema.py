"""
Tests del esquema agéntico (función H del roadmap).

El esquema y el validador no ejecutan subprocess: todos los documentos se
construyen con managers y monitor simulados.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from tui_manager import cli_json
from tui_manager import main as main_module
from tui_manager.core import agent_schema
from tui_manager.core.agent_schema import (
    AGENT_SCHEMA,
    BLOCK_COMMANDS,
    COMMANDS,
    SCHEMA_VERSION,
    validate_document,
)
from tui_manager.core.package_adapter import Package
from tui_manager.core.process_monitor import Process


class _FakePackageManager:
    def __init__(self, packages):
        self._packages = list(packages)

    def get_installed_packages(self, *args, **kwargs):
        return list(self._packages)


class _FakeProcessMonitor:
    def __init__(self, processes):
        self._processes = list(processes)

    def get_processes(self, *args, **kwargs):
        return list(self._processes)


@pytest.fixture
def valid_docs(monkeypatch):
    """Documentos reales (con fuentes simuladas) para los cuatro comandos."""
    pkg = Package(name='htop', version='3.2.2', description='Monitor',
                  installed=True, size='300 kB', category='system',
                  dependencies=['libc6'], recommends=[])
    proc = Process(pid=42, user='root', cpu=1.5, mem=0.2, vsz=1000, rss=200,
                   nice=0, start='10:00', time='0:01', command='python')
    monkeypatch.setattr(cli_json, 'PackageManager',
                        lambda distribution=None: _FakePackageManager([pkg]))
    monkeypatch.setattr(cli_json, 'ProcessMonitor',
                        lambda: _FakeProcessMonitor([proc]))
    monkeypatch.setattr(
        main_module, 'collect_doctor_data',
        lambda: {
            'distribution': 'debian',
            'rows': [{'key': 'doctor.os', 'value': 'Linux', 'warn': False},
                     {'key': 'apt', 'value': 'N/D', 'warn': True}],
            'suggestions': ['doctor.fix.cli'],
        })
    return {command: cli_json.build_document(command, distribution='debian')
            for command in COMMANDS}


# --------------------------------------------------------------------------
# El esquema expuesto.
# --------------------------------------------------------------------------

def test_schema_is_json_serializable_and_versioned():
    payload = json.dumps(AGENT_SCHEMA, ensure_ascii=False, indent=2)
    schema = json.loads(payload)

    assert schema == AGENT_SCHEMA
    assert schema['schema_version'] == SCHEMA_VERSION == '1.0'
    assert set(schema['commands']) == set(COMMANDS)
    assert set(BLOCK_COMMANDS) == {'packages', 'processes', 'doctor'}
    assert set(schema['document']) == {
        'schema_version', 'command', 'version', 'distribution', 'items',
    }


def test_schema_documents_every_item_field():
    fields = {cmd: AGENT_SCHEMA['commands'][cmd]['items']['fields']
              for cmd in BLOCK_COMMANDS}

    assert {'name', 'version', 'installed'} <= set(fields['packages'])
    assert {'pid', 'user', 'cpu', 'mem', 'command'} <= set(fields['processes'])
    assert {'type', 'key', 'value', 'warn'} <= set(fields['doctor'])

    # Todos los campos documentados tienen tipo y descripción.
    for command, command_fields in fields.items():
        for name, spec in command_fields.items():
            assert spec.get('type'), f'{command}.{name} sin tipo'
            assert spec.get('description'), f'{command}.{name} sin descripción'

    all_items = AGENT_SCHEMA['commands']['all']['items']
    assert all_items['type'] == 'object'
    assert set(all_items['properties']) == set(BLOCK_COMMANDS)
    assert set(all_items['required']) == set(BLOCK_COMMANDS)


def test_agent_schema_has_no_third_party_dependencies():
    """Sin dependencias nuevas: solo ``__future__``."""
    source = Path(agent_schema.__file__).read_text(encoding='utf-8')
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module)
    assert imports <= {'__future__'}, imports


# --------------------------------------------------------------------------
# Validación de documentos generados.
# --------------------------------------------------------------------------

@pytest.mark.parametrize('command', COMMANDS)
def test_validate_accepts_generated_documents(valid_docs, command):
    assert validate_document(valid_docs[command], command) == []


@pytest.mark.parametrize('command', COMMANDS)
@pytest.mark.parametrize('key', ('schema_version', 'command', 'version',
                                 'distribution', 'items'))
def test_validate_reports_missing_document_keys(valid_docs, command, key):
    doc = copy.deepcopy(valid_docs[command])
    del doc[key]
    errors = validate_document(doc, command)
    assert any(key in error for error in errors), errors


def test_validate_rejects_wrong_schema_version_and_command(valid_docs):
    doc = copy.deepcopy(valid_docs['packages'])
    doc['schema_version'] = '2.0'
    doc['command'] = 'doctor'
    errors = validate_document(doc, 'packages')
    assert any('schema_version' in e for e in errors)
    assert any('command' in e for e in errors)


def test_validate_rejects_wrong_document_types(valid_docs):
    doc = copy.deepcopy(valid_docs['packages'])
    doc['version'] = 2
    doc['distribution'] = 123
    errors = validate_document(doc, 'packages')
    assert any('version' in e for e in errors)
    assert any('distribution' in e for e in errors)


def test_validate_rejects_non_dict_document():
    assert validate_document([], 'packages')
    assert validate_document(None, 'doctor')


def test_validate_rejects_unknown_command():
    assert validate_document({}, 'no-existe')


def test_items_of_blocks_must_be_arrays(valid_docs):
    doc = copy.deepcopy(valid_docs['packages'])
    doc['items'] = {'name': 'htop'}
    assert any('items' in e for e in validate_document(doc, 'packages'))


def test_items_validate_required_fields_and_types(valid_docs):
    doc = copy.deepcopy(valid_docs['packages'])
    del doc['items'][0]['installed']
    doc['items'][0]['version'] = 42
    doc['items'][0]['sorpresa'] = True
    errors = validate_document(doc, 'packages')
    assert any('installed' in e for e in errors)
    assert any('version' in e for e in errors)
    assert any('sorpresa' in e for e in errors)


def test_doctor_warn_must_be_boolean(valid_docs):
    doc = copy.deepcopy(valid_docs['doctor'])
    doc['items'][0]['warn'] = 'sí'
    errors = validate_document(doc, 'doctor')
    assert any('warn' in e for e in errors)


def test_doctor_type_is_an_enum(valid_docs):
    doc = copy.deepcopy(valid_docs['doctor'])
    doc['items'][0]['type'] = 'otro'
    assert any('type' in e for e in validate_document(doc, 'doctor'))


def test_all_validates_each_block(valid_docs):
    doc = copy.deepcopy(valid_docs['all'])
    del doc['items']['processes'][0]['pid']
    errors = validate_document(doc, 'all')
    assert any('items.processes' in e and 'pid' in e for e in errors), errors

    del doc['items']['doctor']
    assert any('items' in e and 'doctor' in e
               for e in validate_document(doc, 'all'))
