"""
Tests simulados de auditoría de acciones destructivas (B2-1).

No se ejecutan comandos reales: los adapters se sustituyen por un stub y
``fake_runner`` simula ``subprocess.run`` para procesos.
"""

import json
from datetime import datetime

from tui_manager.core.audit import AuditEntry, AuditLog
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.process_monitor import ProcessMonitor


class StubAdapter:
    """Adapter en memoria con resultados configurables (sin subprocess)."""

    def __init__(self, install=True, remove=True, clean=True):
        self.install = install
        self.remove = remove
        self.clean = clean
        self.calls = []

    def _resolve(self, value, name):
        self.calls.append(name)
        if isinstance(value, Exception):
            raise value
        return value

    def install_package(self, package_name, confirm=True):
        return self._resolve(self.install, ('install_package', package_name, confirm))

    def remove_package(self, package_name, confirm=True):
        return self._resolve(self.remove, ('remove_package', package_name, confirm))

    def clean_orphans(self, confirm=True):
        return self._resolve(self.clean, ('clean_orphans', confirm))


def _manager(audit, adapter=None):
    pm = PackageManager(distribution='debian', audit_log=audit)
    pm.adapter = adapter or StubAdapter()
    return pm


# ---------------- AuditLog / AuditEntry ----------------

def test_entry_has_required_fields():
    audit = AuditLog(actor='carlos')
    entry = audit.record('install_package', 'curl', True)

    assert isinstance(entry, AuditEntry)
    assert entry.action == 'install_package'
    assert entry.target == 'curl'
    assert entry.result == 'ok'
    assert entry.actor == 'carlos'
    datetime.fromisoformat(entry.timestamp)  # timestamp ISO válido
    assert audit.get_entries() == [entry]


def test_result_normalization():
    audit = AuditLog(actor='qa')
    assert audit.record('remove_package', 'vim', False).result == 'error'
    assert audit.record('kill_process', '1234', 'error').result == 'error'
    assert audit.record('renice_process', '1234', 'success').result == 'ok'


def test_actor_taken_from_environment(monkeypatch):
    monkeypatch.setenv('USER', 'tester')
    entry = AuditLog().record('write', '/tmp/archivo', True)
    assert entry.actor == 'tester'


def test_get_entries_returns_a_copy():
    audit = AuditLog(actor='qa')
    audit.record('install_package', 'curl', True)

    copy = audit.get_entries()
    copy.clear()
    assert len(audit.get_entries()) == 1
    assert audit.get_entries(as_dicts=True)[0]['action'] == 'install_package'


def test_no_credentials_or_full_stdout():
    secret = 'SUPERSECRETO123'
    stdout = (
        'Instalando paquete...\n'
        f'password={secret}\n'
        'Authorization: Bearer abcdef1234567890\n'
        + ('linea de salida ' * 100)
    )
    entry = AuditLog(actor='qa').record(
        'install_package', 'curl', True, detail=stdout,
    )
    serialized = json.dumps(entry.to_dict(), ensure_ascii=False)

    assert secret not in serialized
    assert 'abcdef1234567890' not in serialized
    assert '\n' not in entry.detail
    assert len(entry.detail) <= 201
    assert '[REDACTADO]' in entry.detail


def test_jsonl_persistence(tmp_path):
    path = tmp_path / 'registros' / 'audit.jsonl'
    audit = AuditLog(path=path, actor='ci')
    audit.record('install_package', 'curl', True)
    audit.record('remove_package', 'curl', False)

    lines = path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])['target'] == 'curl'

    reloaded = AuditLog.from_path(path)
    assert [e.action for e in reloaded.get_entries()] == [
        'install_package', 'remove_package',
    ]
    assert reloaded.get_entries()[1].result == 'error'


def test_record_write_uses_write_action(tmp_path):
    target = tmp_path / 'config.toml'
    audit = AuditLog(actor='qa')
    audit.record_write(target, True)

    entry = audit.get_entries()[0]
    assert entry.action == 'write'
    assert entry.target == str(target)
    assert entry.result == 'ok'


# ---------------- PackageManager ----------------

def test_package_manager_audits_install_ok_and_error():
    audit = AuditLog(actor='qa')
    adapter = StubAdapter(install=True)
    pm = _manager(audit, adapter)

    assert pm.install_package('curl') is True
    adapter.install = RuntimeError('falló la instalación')
    assert pm.install_package('curl') is False

    assert [(e.action, e.target, e.result) for e in audit.get_entries()] == [
        ('install_package', 'curl', 'ok'),
        ('install_package', 'curl', 'error'),
    ]
    assert all(e.actor == 'qa' for e in audit.get_entries())


def test_package_manager_audits_remove_and_clean_orphans():
    audit = AuditLog(actor='qa')
    adapter = StubAdapter(remove=True, clean=False)
    pm = _manager(audit, adapter)

    assert pm.remove_package('vim') is True
    assert pm.clean_orphans() is False

    assert [(e.action, e.result) for e in audit.get_entries()] == [
        ('remove_package', 'ok'),
        ('clean_orphans', 'error'),
    ]
    assert audit.get_entries()[0].target == 'vim'


def test_package_manager_without_audit_keeps_behavior():
    pm = PackageManager(distribution='debian')
    pm.adapter = StubAdapter()

    assert pm.audit_log is None
    assert pm.install_package('curl') is True
    assert pm.remove_package('vim') is True
    assert pm.clean_orphans() is True


# ---------------- ProcessMonitor ----------------

def test_process_monitor_audits_kill(fake_runner):
    audit = AuditLog(actor='qa')
    monitor = ProcessMonitor(audit_log=audit)
    fake_runner.expect(['kill', '-s', '15', '4242'], rc=0)
    fake_runner.expect(['kill', '-s', '9', '4242'], rc=1, stderr='no such process')

    assert monitor.kill_process(4242) is True
    assert monitor.kill_process(4242, signal=9) is False

    assert [(e.action, e.target, e.result) for e in audit.get_entries()] == [
        ('kill_process', '4242', 'ok'),
        ('kill_process', '4242', 'error'),
    ]


def test_process_monitor_audits_renice(fake_runner):
    audit = AuditLog(actor='qa')
    monitor = ProcessMonitor(audit_log=audit)
    fake_runner.expect(['renice', '5', '-p', '4242'], rc=0)
    fake_runner.expect(['renice', '-20', '-p', '99'], rc=1, stderr='denied')

    assert monitor.renice_process(4242, 5) is True
    assert monitor.renice_process(99, -20) is False

    assert [(e.action, e.target, e.result) for e in audit.get_entries()] == [
        ('renice_process', '4242', 'ok'),
        ('renice_process', '99', 'error'),
    ]


def test_process_monitor_without_audit_keeps_behavior(fake_runner):
    fake_runner.expect(['kill', '-s', '15', '4242'], rc=0)
    fake_runner.expect(['renice', '5', '-p', '4242'], rc=0)
    monitor = ProcessMonitor()

    assert monitor.audit_log is None
    assert monitor.kill_process(4242) is True
    assert monitor.renice_process(4242, 5) is True
