#!/usr/bin/env python3
"""
TUI Manager - Gestor de Paquetes y Procesos TUI para Linux

Interfaz de usuario terminal para gestionar paquetes, instalar/desinstalar
aplicaciones y monitorear procesos en tiempo real.

Inspiration: Omarchy Quattro
"""

import sys
import os
import logging
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tui_manager.core.distribution import DistributionDetector
from tui_manager.core.package_manager import PackageManager
from tui_manager.core.process_monitor import ProcessMonitor
from tui_manager.core.theme_manager import ThemeManager
from tui_manager.core.config import Config
from tui_manager.ui.screens import ScreenManager
from tui_manager.utils.logger import setup_logger


def main():
    """Punto de entrada principal de la aplicación"""

    # Configurar logging
    logger = setup_logger('TUI-Manager')

    try:
        # Verificar versión de Python
        if sys.version_info < (3, 10):
            print("Error: TUI Manager requiere Python 3.10 o superior")
            print(f"Versión actual: {sys.version}")
            sys.exit(1)

        logger.info("Iniciando TUI Manager")

        # Detectar distribución
        logger.info("Detectando distribución...")
        distribution = DistributionDetector.detect()
        logger.info(f"Distribución detectada: {distribution}")

        # Verificar si la distribución es soportada
        if not DistributionDetector.is_supported():
            logger.warning("Tu distribución no es soportada")
            logger.warning("Distribuciones soportadas: Debian, Ubuntu, Arch, Fedora, Void, Gentoo, OpenSUSE, Alpine")
            print("\n" + "="*60)
            print("⚠️  ADVERTENCIA")
            print("="*60)
            print("Tu distribución no es soportada.")
            print("Las siguientes distribuciones están soportadas:")
            print("  • Debian y derivados (Ubuntu, Linux Mint, etc.)")
            print("  • Arch Linux y derivados (Manjaro, EndeavourOS, etc.)")
            print("  • Fedora y derivados (RHEL, CentOS Stream, etc.)")
            print("  • Void Linux")
            print("  • Gentoo")
            print("  • OpenSUSE")
            print("  • Alpine Linux")
            print("\n" + "="*60)
            input("Presiona Enter para continuar o Ctrl+C para salir...")

        # Crear instancias de los módulos principales
        logger.info("Inicializando componentes...")
        package_manager = PackageManager(distribution=distribution)
        process_monitor = ProcessMonitor()
        theme_manager = ThemeManager()
        config = Config()
        screen_manager = ScreenManager()

        # Mostrar pantalla de bienvenida
        print("\n" + "="*60)
        print("🚀 TUI Manager v0.1.0")
        print("="*60)
        print(f"Distribución: {distribution}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Tema: {theme_manager.get_current_theme()}")
        print("="*60 + "\n")

        # Iniciar la interfaz
        logger.info("Iniciando interfaz TUI")
        screen_manager.run()

    except KeyboardInterrupt:
        logger.info("Aplicación cerrada por el usuario")
        print("\n\nSaliendo...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error crítico: {e}", exc_info=True)
        print("\n" + "="*60)
        print("❌ ERROR CRÍTICO")
        print("="*60)
        print(f"Ocurrió un error: {e}")
        print("="*60 + "\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
