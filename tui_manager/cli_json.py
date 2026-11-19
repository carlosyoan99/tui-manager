"""
Salida ``--json`` de TUI Manager para scripts y agentes.

Contrato estable (independiente del tipo solicitado)::

    {
      "version": "1.1.0",
      "distribution": "debian",
      "items": [ ... ]
    }

Garantías:

* JSON válido y sin colores en stdout (``indent=2``, ``ensure_ascii=False``).
* Errores en stderr con exit code 1; nunca un traceback ni logs en stdout.
* Durante la recolección se silencia ``logging`` de forma temporal para que
  ningún handler ajeno (p. ej. el ``StreamHandler(sys.stdout)`` instalado por
  ``setup_logger``) contamine el documento JSON.
* Los datos se obtienen reutilizando los componentes existentes:
  ``PackageManager``, ``ProcessMonitor`` y la recolección compartida del
  doctor en ``main.collect_doctor_data`` (sin duplicar lógica de subprocess).
"""

from __future__ import annotations

import json
import logging
import sys

from tui_manager import __version__
from tui_manager.core.distribution import DistributionDetector
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.process_monitor import ProcessMonitor

#: Valores aceptados por ``--json`` (mantener sincronizados con main.py).
JSON_KINDS = ('packages', 'processes', 'doctor')


class JsonOutputError(Exception):
    """Error al construir el documento JSON."""


# --------------------------------------------------------------------------
# Serializadores: esquemas explícitos y estables por elemento.
# --------------------------------------------------------------------------

def _package_to_dict(package) -> dict:
    return {
        'name': package.name,
        'version': package.version,
        'description': package.description,
        'installed': bool(package.installed),
        'size': package.size,
        'category': package.category,
        'dependencies': list(package.dependencies or []),
        'recommends': list(package.recommends or []),
    }


def _process_to_dict(process) -> dict:
    # Process.to_dict() ya define el esquema estable del proceso.
    return process.to_dict()


def _doctor_items(data: dict) -> list:
    from tui_manager.i18n import t

    items = []
    for row in data['rows']:
        items.append({
            'type': 'diagnostic',
            'key': row['key'],
            'label': t(row['key']),
            'value': row['value'],
            'warn': row['warn'],
        })
    for key in data['suggestions']:
        items.append({
            'type': 'suggestion',
            'key': key,
            'label': t(key),
            'value': t(key),
            'warn': False,
        })
    return items


# --------------------------------------------------------------------------
# Construcción del documento.
# --------------------------------------------------------------------------

def _detect_distribution():
    try:
        return DistributionDetector.detect()
    except Exception:
        return None


def build_document(kind: str, distribution=None) -> dict:
    """Construye el documento ``{version, distribution, items}``.

    ``kind`` debe estar en :data:`JSON_KINDS`. Si se proporciona
    ``distribution`` se usa tal cual (evita detectarla dos veces).
    """
    if kind not in JSON_KINDS:
        raise JsonOutputError(f'tipo JSON desconocido: {kind!r}')

    if kind == 'doctor':
        # Import diferido: main.py importa cli_json desde main(); hacerlo aquí
        # arriba crearía un ciclo. Reutilizamos la recolección existente.
        from tui_manager.main import collect_doctor_data
        data = collect_doctor_data()
        if distribution is None:
            distribution = data['distribution']
        items = _doctor_items(data)
    else:
        if distribution is None:
            distribution = _detect_distribution()
        if kind == 'packages':
            manager = PackageManager(distribution=distribution)
            items = [_package_to_dict(p)
                     for p in manager.get_installed_packages()]
        else:  # kind == 'processes'
            monitor = ProcessMonitor()
            items = [_process_to_dict(p) for p in monitor.get_processes()]

    return {
        'version': __version__,
        'distribution': distribution,
        'items': items,
    }


def emit_json(kind: str, stream=None, err_stream=None) -> int:
    """Serializa el documento a ``stream`` (stdout por defecto).

    Devuelve 0 si todo va bien; en caso de error escribe el mensaje en
    ``err_stream`` (stderr por defecto), deja stdout intacto y devuelve 1.
    """
    stream = stream if stream is not None else sys.stdout
    err_stream = err_stream if err_stream is not None else sys.stderr

    # Silenciar logging globalmente evita que cualquier handler configurado
    # (FileHandler, StreamHandler(sys.stdout), ...) interleave líneas de log
    # con el documento. Se restaura el estado previo en `finally`.
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        try:
            document = build_document(kind)
            payload = json.dumps(document, ensure_ascii=False, indent=2)
        except Exception as exc:  # cualquier fallo se reporta por stderr
            err_stream.write(f'{type(exc).__name__}: {exc}\n')
            return 1
    finally:
        logging.disable(previous_disable)

    stream.write(payload + '\n')
    return 0
