"""Esquema público de la CLI estructurada (``--json``) para agentes de IA.

Este módulo es la única fuente de verdad del contrato legible por máquina:

* :data:`AGENT_SCHEMA` se imprime con ``tui-manager --schema`` y describe
  los comandos disponibles, la forma del documento y los campos de cada
  elemento de ``items``.
* :func:`validate_document` comprueba que un documento generado cumple ese
  contrato y devuelve una lista de errores (vacía si es válido).

No añade dependencias y no ejecuta subprocess: es solo una descripción
declarativa más un validador de tipos JSON.
"""

from __future__ import annotations

#: Versión del contrato. Cambiarla solo con un cambio incompatible del
#: documento (nuevas claves obligatorias, tipos distintos, etc.).
SCHEMA_VERSION = '1.0'

#: Comandos aceptados por ``--json``. ``all`` devuelve los tres bloques.
COMMANDS = ('packages', 'processes', 'doctor', 'all')

#: Bloques individuales que componen ``--json all``.
BLOCK_COMMANDS = ('packages', 'processes', 'doctor')


def _field(type_, description, **extra):
    """Construye la descripción de un campo del documento."""
    spec = {'type': type_, 'description': description}
    spec.update(extra)
    return spec


# Campos devueltos por cada serializador de cli_json.py. `required` marca
# los imprescindibles; el resto está documentado pero es opcional para el
# validador (así se puede ampliar el documento sin romper consumidores).
_PACKAGE_FIELDS = {
    'name': _field('string', 'Nombre identificador del paquete.'),
    'version': _field('string', 'Versión instalada del paquete.'),
    'installed': _field('boolean', 'True si el paquete está instalado.'),
    'description': _field('string', 'Descripción breve del paquete.'),
    'size': _field('string', 'Tamaño instalado en formato legible.'),
    'category': _field('string', 'Categoría del paquete.'),
    'dependencies': _field('array', 'Nombres de dependencias.',
                           items={'type': 'string'}),
    'recommends': _field('array', 'Nombres de paquetes recomendados.',
                         items={'type': 'string'}),
}

_PROCESS_FIELDS = {
    'pid': _field('integer', 'Identificador del proceso.'),
    'user': _field('string', 'Usuario propietario del proceso.'),
    'cpu': _field('number', 'Porcentaje de uso de CPU.'),
    'mem': _field('number', 'Porcentaje de uso de memoria.'),
    'command': _field('string', 'Comando con el que se ejecutó el proceso.'),
    'vsz': _field('integer', 'Memoria virtual en KiB.'),
    'rss': _field('integer', 'Memoria residente en KiB.'),
    'nice': _field('integer', 'Prioridad (valor nice) del proceso.'),
    'start': _field('string', 'Hora de inicio del proceso.'),
    'time': _field('string', 'Tiempo acumulado de CPU del proceso.'),
}

_DOCTOR_FIELDS = {
    'type': _field('string', 'Tipo de entrada: diagnóstico o sugerencia.',
                   enum=['diagnostic', 'suggestion']),
    'key': _field('string', 'Clave estable (p. ej. ``doctor.os``).'),
    'value': _field('string', 'Valor medido o texto de la sugerencia.'),
    'warn': _field('boolean', 'True si la entrada requiere atención.'),
    'label': _field('string', 'Etiqueta traducida de la clave.'),
}

_REQUIRED_FIELDS = {
    'packages': ['name', 'version', 'installed'],
    'processes': ['pid', 'user', 'cpu', 'mem', 'command'],
    'doctor': ['type', 'key', 'value', 'warn'],
}

_FIELDS_BY_COMMAND = {
    'packages': _PACKAGE_FIELDS,
    'processes': _PROCESS_FIELDS,
    'doctor': _DOCTOR_FIELDS,
}

_DESCRIPTIONS = {
    'packages': 'Paquetes instalados conocidos por el gestor de la distro.',
    'processes': 'Procesos del sistema en el momento de la consulta.',
    'doctor': 'Filas de diagnóstico y sugerencias del entorno.',
}


def _items_spec(command):
    """Devuelve la forma de ``items`` para un bloque individual."""
    return {
        'type': 'array',
        'description': f'Lista de entradas de {command}.',
        'fields': _FIELDS_BY_COMMAND[command],
        'required': list(_REQUIRED_FIELDS[command]),
    }


_ITEMS_BY_BLOCK = {command: _items_spec(command)
                   for command in BLOCK_COMMANDS}


#: Esquema expuesto por ``--schema`` y consumido por :func:`validate_document`.
AGENT_SCHEMA = {
    'schema_version': SCHEMA_VERSION,
    'description': 'Contrato JSON de la CLI de TUI Manager para scripts y '
                   'agentes de IA. Ninguna ruta ``--json``/``--schema`` '
                   'ejecuta comandos con elevación.',
    'usage': {
        'schema': 'tui-manager --schema',
        'json': 'tui-manager --json packages|processes|doctor|all',
        'note': '``all`` devuelve en ``items`` un objeto con las tres claves '
                'de bloque; los demás comandos devuelven una lista.',
    },
    'document': {
        'schema_version': _field('string', 'Versión de este contrato.'),
        'command': _field('string', 'Comando que generó el documento.',
                          enum=list(COMMANDS)),
        'version': _field('string', 'Versión de TUI Manager.'),
        'distribution': _field(['string', 'null'],
                               'Distro detectada, o null si no se pudo '
                               'determinar.'),
        'items': _field(['array', 'object'],
                        'Datos solicitados; su forma depende de ``command`` '
                        '(véase ``commands[command].items``).'),
    },
    'commands': {
        command: {
            'description': _DESCRIPTIONS[command],
            'items': _ITEMS_BY_BLOCK[command],
        }
        for command in BLOCK_COMMANDS
    },
}

AGENT_SCHEMA['commands']['all'] = {
    'description': 'Los tres bloques en un único documento.',
    'items': {
        'type': 'object',
        'description': 'Mapa ``packages``/``processes``/``doctor`` → lista '
                       'de entradas de ese bloque.',
        'properties': {
            command: _ITEMS_BY_BLOCK[command] for command in BLOCK_COMMANDS
        },
        'required': list(BLOCK_COMMANDS),
    },
}


# --------------------------------------------------------------------------
# Validación.
# --------------------------------------------------------------------------

def _type_matches(value, expected) -> bool:
    """Comprueba un tipo JSON (o una lista de tipos alternativos)."""
    names = expected if isinstance(expected, (list, tuple)) else (expected,)
    for name in names:
        if name == 'null' and value is None:
            return True
        if name == 'boolean' and isinstance(value, bool):
            return True
        if name == 'integer' and isinstance(value, int) and not isinstance(value, bool):
            return True
        if name == 'number' and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if name == 'string' and isinstance(value, str):
            return True
        if name == 'array' and isinstance(value, list):
            return True
        if name == 'object' and isinstance(value, dict):
            return True
    return False


def _expected_name(expected) -> str:
    if isinstance(expected, (list, tuple)):
        return '/'.join(expected)
    return str(expected)


def _check_value(value, spec: dict, path: str, errors: list) -> None:
    """Valida recursivamente ``value`` contra un fragmento del esquema."""
    expected = spec.get('type')
    if not _type_matches(value, expected):
        errors.append(
            f'{path}: se esperaba {_expected_name(expected)}, '
            f'se obtuvo {type(value).__name__}')
        return

    if 'enum' in spec and value not in spec['enum']:
        errors.append(f'{path}: valor no permitido {value!r}')

    fields = spec.get('fields') or {}
    properties = spec.get('properties') or {}

    if isinstance(value, dict):
        for key in spec.get('required', ()):
            if key not in value:
                errors.append(f'{path}: falta el campo obligatorio {key!r}')
        for key, item_value in value.items():
            location = f'{path}.{key}'
            if key in properties:
                _check_value(item_value, properties[key], location, errors)
            elif key in fields:
                _check_value(item_value, fields[key], location, errors)
            elif 'fields' in spec or 'properties' in spec:
                errors.append(f'{path}: campo desconocido {key!r}')
    elif isinstance(value, list):
        for index, entry in enumerate(value):
            location = f'{path}[{index}]'
            if 'items' in spec:
                _check_value(entry, spec['items'], location, errors)
            elif 'fields' in spec:
                # `required` se aplica a cada entrada, no a la lista.
                _check_value(entry, {
                    'type': 'object',
                    'fields': fields,
                    'required': spec.get('required', ()),
                }, location, errors)


def validate_document(doc, command: str) -> list[str]:
    """Valida un documento generado por ``--json``.

    Devuelve una lista de mensajes de error; vacía si el documento cumple el
    esquema de ``command``. Nunca lanza excepciones por datos mal formados.
    """
    errors = []
    if command not in AGENT_SCHEMA['commands']:
        return [f'comando desconocido: {command!r}']
    if not isinstance(doc, dict):
        return ['el documento debe ser un objeto JSON']

    for key, spec in AGENT_SCHEMA['document'].items():
        if key == 'items':
            continue  # su forma depende del comando
        if key not in doc:
            errors.append(f'falta la clave obligatoria {key!r}')
            continue
        _check_value(doc[key], spec, key, errors)

    if 'schema_version' in doc and doc['schema_version'] != SCHEMA_VERSION:
        errors.append(
            f'schema_version: se esperaba {SCHEMA_VERSION!r}, '
            f'se obtuvo {doc["schema_version"]!r}')
    if 'command' in doc and doc['command'] != command:
        errors.append(
            f'command: se esperaba {command!r}, se obtuvo {doc["command"]!r}')

    _check_value(doc.get('items'),
                 AGENT_SCHEMA['commands'][command]['items'],
                 'items', errors)
    return errors
