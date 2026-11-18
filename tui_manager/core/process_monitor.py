"""
Monitor de procesos en tiempo real
"""

import subprocess
import logging
from typing import List, Optional
from dataclasses import dataclass

from .audit import AuditLog
from .perf import paginate

logger = logging.getLogger(__name__)


@dataclass
class Process:
    """Modelo de datos para procesos"""
    pid: int
    user: str
    cpu: float
    mem: float
    vsz: int
    rss: int
    nice: int
    start: str
    time: str
    command: str

    def get_memory_usage_mb(self) -> float:
        """Retorna uso de memoria en MB"""
        return self.rss / 1024

    def get_virtual_memory_mb(self) -> float:
        """Retorna memoria virtual en MB"""
        return self.vsz / 1024

    def get_status(self) -> str:
        """Obtiene el estado del proceso"""
        try:
            with open(f'/proc/{self.pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('State:'):
                        return line.split(':')[1].strip()
        except FileNotFoundError:
            return 'unknown'

    def get_ppid(self) -> int:
        """Obtiene el PID del proceso padre"""
        try:
            with open(f'/proc/{self.pid}/stat', 'r') as f:
                parts = f.read().split()
                return int(parts[3])
        except FileNotFoundError:
            return 0

    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'pid': self.pid,
            'user': self.user,
            'cpu': self.cpu,
            'mem': self.mem,
            'vsz': self.vsz,
            'rss': self.rss,
            'nice': self.nice,
            'start': self.start,
            'time': self.time,
            'command': self.command
        }


class ProcessNotFoundError(Exception):
    """Proceso no encontrado"""
    pass


class ProcessMonitor:
    """Monitor de procesos"""

    def __init__(self, refresh_interval: int = 2,
                 audit_log: Optional[AuditLog] = None):
        """
        Inicializa el monitor de procesos

        Args:
            refresh_interval: Intervalo de actualización en segundos
            audit_log: Registro de auditoría opcional. Si es None no se registran
                       acciones (comportamiento por defecto sin cambios).
        """
        self.refresh_interval = refresh_interval
        self.audit_log = audit_log
        logger.info(f"ProcessMonitor inicializado con intervalo de {refresh_interval}s")

    def _audit(self, action: str, target: str, result: bool) -> None:
        """Registra una acción destructiva si se inyectó un AuditLog."""
        if self.audit_log is not None:
            self.audit_log.record(action, target, result)

    def get_processes(self, filters: dict = None, offset: int = 0,
                      limit: Optional[int] = None) -> List[Process]:
        """
        Obtiene la lista de procesos

        Args:
            filters: Diccionario con filtros opcionales:
                     - user: Filtrar por usuario
                     - name: Filtrar por nombre de comando
                     - min_cpu: CPU mínimo (porcentaje)
                     - max_cpu: CPU máximo (porcentaje)
                     - min_mem: Memoria mínima (MB)
                     - max_mem: Memoria máxima (MB)
                     - pid: Filtrar por PID
            offset: Fila inicial de la ventana paginada (0 por defecto).
            limit: Número máximo de filas de la ventana (None = todas).

        Returns:
            Lista de objetos Process
        """
        cmd = ['ps', 'aux']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            logger.error(f"Error al obtener procesos: {e}")
            return []

        processes = []
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if not line.strip():
                continue

            # Columnas reales de `ps aux`:
            # USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            parts = line.split(None, 10)
            if len(parts) >= 11:
                try:
                    process = Process(
                        pid=int(parts[1]),
                        user=parts[0],
                        cpu=float(parts[2]),
                        mem=float(parts[3]),
                        vsz=int(parts[4]),
                        rss=int(parts[5]),
                        # `ps aux` no reporta NI: nice=0 (TTY en parts[6], STAT en parts[7])
                        nice=0,
                        start=parts[8],
                        time=parts[9],
                        command=parts[10] if len(parts) > 10 else ''
                    )
                    processes.append(process)
                except (ValueError, IndexError) as e:
                    logger.debug(f"Error al parsear línea: {line} ({e})")
                    continue

        # Aplicar filtros
        if filters:
            processes = self._apply_filters(processes, filters)

        return paginate(processes, offset, limit)

    def get_process_by_pid(self, pid: int) -> Process:
        """
        Obtiene información de un proceso específico

        Args:
            pid: ID del proceso

        Returns:
            Objeto Process con información del proceso

        Raises:
            ProcessNotFoundError: Si el proceso no existe
        """
        processes = self.get_processes({'pid': pid})
        if not processes:
            raise ProcessNotFoundError(f"Proceso con PID {pid} no encontrado")
        return processes[0]

    def kill_process(self, pid: int, signal: int = 15) -> bool:
        """
        Termina un proceso

        Args:
            pid: ID del proceso
            signal: Señal a enviar (15=SIGTERM, 9=SIGKILL)

        Returns:
            True si el proceso fue terminado, False en caso contrario
        """
        cmd = ['kill', '-s', str(signal), str(pid)]
        success = False
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode == 0:
                logger.info(f"Proceso {pid} terminado con señal {signal}")
                success = True
                return True
            else:
                logger.error(f"Error al terminar proceso {pid}: {completed.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error al enviar señal: {e}")
            return False
        finally:
            self._audit('kill_process', str(pid), success)

    def renice_process(self, pid: int, nice: int) -> bool:
        """
        Cambia la prioridad de un proceso

        Args:
            pid: ID del proceso
            nice: Valor de prioridad (-20 a 19)

        Returns:
            True si la prioridad fue cambiada, False en caso contrario
        """
        cmd = ['renice', str(nice), '-p', str(pid)]
        success = False
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode == 0:
                logger.info(f"Proceso {pid} prioridad cambiada a {nice}")
                success = True
                return True
            else:
                logger.error(f"Error al cambiar prioridad: {completed.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error al cambiar prioridad: {e}")
            return False
        finally:
            self._audit('renice_process', str(pid), success)

    def get_total_cpu_usage(self) -> float:
        """
        Obtiene el uso total de CPU del sistema

        Returns:
            Porcentaje de CPU usado
        """
        processes = self.get_processes()
        return sum(p.cpu for p in processes)

    def get_total_memory_usage(self) -> dict:
        """
        Obtiene el uso total de memoria del sistema

        Returns:
            Diccionario con:
            - total: Memoria total (MB)
            - used: Memoria usada (MB)
            - free: Memoria libre (MB)
            - available: Memoria disponible (MB)
            - percentage: Porcentaje usado
        """
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_info = {}
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_info['total'] = int(line.split()[1]) / 1024  # MB
                    elif line.startswith('MemFree:'):
                        mem_info['free'] = int(line.split()[1]) / 1024  # MB
                    elif line.startswith('MemAvailable:'):
                        mem_info['available'] = int(line.split()[1]) / 1024  # MB

            if 'total' in mem_info:
                mem_info['used'] = mem_info['total'] - mem_info.get('free', 0)
                mem_info['available'] = mem_info.get('available', mem_info['used'])
                mem_info['percentage'] = (mem_info['used'] / mem_info['total']) * 100
                return mem_info

        except Exception as e:
            logger.error(f"Error al obtener memoria: {e}")

        return {
            'total': 0,
            'used': 0,
            'free': 0,
            'available': 0,
            'percentage': 0
        }

    def get_top_processes(self, count: int = 10, by: str = 'cpu') -> List[Process]:
        """
        Obtiene los procesos más consumidoros

        Args:
            count: Número de procesos a retornar
            by: 'cpu' o 'mem' para ordenar por CPU o memoria

        Returns:
            Lista de procesos ordenados
        """
        processes = self.get_processes()

        if by == 'cpu':
            sorted_processes = sorted(processes, key=lambda p: p.cpu, reverse=True)
        else:
            sorted_processes = sorted(processes, key=lambda p: p.get_memory_usage_mb(), reverse=True)

        return sorted_processes[:count]

    def _apply_filters(self, processes: List[Process], filters: dict) -> List[Process]:
        """
        Aplica filtros a la lista de procesos

        Args:
            processes: Lista de procesos
            filters: Diccionario con filtros

        Returns:
            Lista de procesos filtrados
        """
        filtered = processes

        if 'user' in filters and filters['user']:
            filtered = [p for p in filtered if p.user == filters['user']]

        if 'name' in filters and filters['name']:
            filtered = [p for p in filtered if filters['name'].lower() in p.command.lower()]

        if 'min_cpu' in filters and filters['min_cpu']:
            filtered = [p for p in filtered if p.cpu >= filters['min_cpu']]

        if 'max_cpu' in filters and filters['max_cpu']:
            filtered = [p for p in filtered if p.cpu <= filters['max_cpu']]

        if 'min_mem' in filters and filters['min_mem']:
            filtered = [p for p in filtered if p.get_memory_usage_mb() >= filters['min_mem']]

        if 'max_mem' in filters and filters['max_mem']:
            filtered = [p for p in filtered if p.get_memory_usage_mb() <= filters['max_mem']]

        if 'pid' in filters and filters['pid']:
            filtered = [p for p in filtered if p.pid == filters['pid']]

        return filtered
