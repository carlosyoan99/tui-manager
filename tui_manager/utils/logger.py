"""
Módulo de logging
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = 'TUI-Manager', log_file: str = None) -> logging.Logger:
    """
    Configura el logger principal

    Args:
        name: Nombre del logger
        log_file: Ruta del archivo de log

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Eliminar handlers existentes para evitar duplicados
    logger.handlers = []

    # Manejador de archivo con rotación (10 MB máximo, 5 backups)
    if log_file is None:
        log_file = os.path.expanduser('~/.tui-manager/logs/app.log')

    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)

        # Manejador de consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Formateador
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Añadir handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logger.info(f"Logger inicializado. Log file: {log_file}")

    except Exception as e:
        logger.error(f"Error al inicializar logger: {e}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger específico

    Args:
        name: Nombre del logger

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)
