"""
Registro de auditoría de acciones destructivas.

Cada entrada contiene únicamente: timestamp ISO 8601, actor (usuario),
acción, destino (paquete, PID o archivo) y resultado (``ok``/``error``).
Opcionalmente se conserva un detalle corto y sanitizado: nunca credenciales
ni la salida completa de un comando.

El registro vive en memoria por defecto. Si se inyecta ``path``, cada entrada
se añade también a un archivo JSONL (una entrada por línea). No se escribe
ninguna ruta por defecto: la decide quien construye el ``AuditLog`` (los tests
deben usar un ``tmp_path``).
"""

from __future__ import annotations

import getpass
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)

RESULT_OK = 'ok'
RESULT_ERROR = 'error'

_OK_VALUES = {'ok', 'success', 'succeeded', 'true', '1', 'yes', 'correcto'}
_ERROR_VALUES = {'error', 'fail', 'failed', 'false', '0', 'no', 'fallo'}

_SENSITIVE_KEYS = (
    'password', 'passwd', 'pwd', 'passphrase', 'secret', 'token',
    'apikey', 'api_key', 'api-key', 'authorization', 'credential',
)
_SECRET_ASSIGNMENT = re.compile(
    r'(?i)\b(' + '|'.join(re.escape(k) for k in _SENSITIVE_KEYS) + r')\s*[:=]\s*\S+'
)
_AUTH_HEADER = re.compile(r'(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+')
_MAX_DETAIL = 200


def _sanitize_detail(detail: Optional[str]) -> str:
    """Convierte un detalle en texto de una línea, sin secretos ni stdout largo."""
    if detail is None:
        return ''
    text = str(detail).replace('\r', ' ').replace('\n', ' ')
    text = _AUTH_HEADER.sub(r'\1=[REDACTADO]', text)
    text = _SECRET_ASSIGNMENT.sub(r'\1=[REDACTADO]', text)
    text = ' '.join(text.split())
    if len(text) > _MAX_DETAIL:
        text = text[:_MAX_DETAIL] + '…'
    return text


def _normalize_result(result: Union[bool, str]) -> str:
    """Acepta bool o texto y devuelve siempre ``ok``/``error``."""
    if isinstance(result, bool):
        return RESULT_OK if result else RESULT_ERROR
    value = str(result).strip().lower()
    if value in _OK_VALUES:
        return RESULT_OK
    if value in _ERROR_VALUES:
        return RESULT_ERROR
    return value[:_MAX_DETAIL] or RESULT_ERROR


def _resolve_actor(override: Optional[str]) -> str:
    """Usuario que ejecuta la acción, sin depender de un sistema concreto."""
    if override:
        return str(override)
    for key in ('USER', 'LOGNAME', 'USERNAME'):
        value = os.environ.get(key)
        if value:
            return value
    try:
        return getpass.getuser()
    except Exception:  # pragma: no cover - entornos sin usuario del sistema
        return 'unknown'


@dataclass(frozen=True)
class AuditEntry:
    """Una entrada inmutable del registro de auditoría."""

    timestamp: str
    actor: str
    action: str
    target: str
    result: str
    detail: str = ''

    @classmethod
    def create(
        cls,
        action: str,
        target: Union[str, int],
        result: Union[bool, str] = True,
        *,
        actor: Optional[str] = None,
        timestamp: Optional[str] = None,
        detail: Optional[str] = '',
    ) -> 'AuditEntry':
        """Crea una entrada con timestamp ISO UTC y datos sanitizados."""
        return cls(
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            actor=_resolve_actor(actor),
            action=str(action),
            target=str(target),
            result=_normalize_result(result),
            detail=_sanitize_detail(detail),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'AuditEntry':
        """Reconstruye una entrada desde JSON, tolerando claves extra."""
        names = {f.name for f in fields(cls)}
        values = {k: v for k, v in dict(data).items() if k in names}
        values.setdefault('detail', '')
        return cls(**values)


class AuditLog:
    """Registro de auditoría append-only, en memoria y/o en JSONL."""

    def __init__(
        self,
        path: Optional[Union[str, os.PathLike]] = None,
        actor: Optional[str] = None,
    ) -> None:
        """
        Args:
            path: Ruta JSONL opcional; ``None`` → sólo memoria.
            actor: Usuario forzado; ``None`` → se detecta del entorno.
        """
        self.path = Path(path).expanduser() if path is not None else None
        self._actor_override = actor
        self._entries: List[AuditEntry] = []

    def record(
        self,
        action: str,
        target: Union[str, int],
        result: Union[bool, str] = True,
        *,
        actor: Optional[str] = None,
        timestamp: Optional[str] = None,
        detail: Optional[str] = '',
    ) -> AuditEntry:
        """Añade una entrada y la persiste si se inyectó una ruta JSONL."""
        entry = AuditEntry.create(
            action, target, result,
            actor=actor or self._actor_override,
            timestamp=timestamp,
            detail=detail,
        )
        self._entries.append(entry)

        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open('a', encoding='utf-8') as handle:
                    handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + '\n')
            except OSError as e:
                logger.error(f"Error al persistir auditoría en {self.path}: {e}")

        # Sólo metadatos: jamás credenciales ni salida de comandos.
        if entry.result == RESULT_OK:
            logger.info(
                f"AUDITORÍA ok: {entry.action} → {entry.target} (actor: {entry.actor})"
            )
        else:
            logger.error(
                f"AUDITORÍA error: {entry.action} → {entry.target} (actor: {entry.actor})"
            )
        return entry

    def record_write(
        self,
        path: Union[str, os.PathLike],
        result: Union[bool, str] = True,
        **kwargs,
    ) -> AuditEntry:
        """Atajo para registrar escrituras en archivos u otros destinos."""
        return self.record('write', str(path), result, **kwargs)

    def get_entries(self, as_dicts: bool = False) -> List[Union[AuditEntry, dict]]:
        """Devuelve una copia de las entradas (no el almacén interno)."""
        if as_dicts:
            return [e.to_dict() for e in self._entries]
        return list(self._entries)

    @staticmethod
    def read_path(path: Union[str, os.PathLike]) -> List[AuditEntry]:
        """Lee un JSONL existente; devuelve [] si la ruta no existe."""
        source = Path(path)
        if not source.exists():
            return []
        entries: List[AuditEntry] = []
        with source.open('r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(AuditEntry.from_dict(json.loads(line)))
                except (ValueError, TypeError) as e:
                    logger.error(f"Entrada de auditoría inválida en {source}: {e}")
        return entries

    @classmethod
    def from_path(
        cls,
        path: Union[str, os.PathLike],
        actor: Optional[str] = None,
    ) -> 'AuditLog':
        """Construye un log ya cargado con las entradas del JSONL indicado."""
        log = cls(path=path, actor=actor)
        log._entries = cls.read_path(path)
        return log
