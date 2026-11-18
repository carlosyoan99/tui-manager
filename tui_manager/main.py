#!/usr/bin/env python3
"""
TUI Manager — punto de entrada.

Uso:
    tui-manager            lanza la interfaz TUI
    tui-manager --version  imprime la versión
    tui-manager --doctor   diagnóstico del entorno (SO, distro, gestor,
                           entorno de escritorio, capacidades, elevación)
    tui-manager --lang es  fuerza el idioma (es|en) para esta ejecución

Inspired: Omarchy Quattro. Portable: Linux, BSD y Termux (limitado).
"""

from __future__ import annotations

import argparse
import logging
import platform
import shutil
import sys

from tui_manager import __version__
from tui_manager.core.config import Config
from tui_manager.core.distribution import DistributionDetector, DistributionError
from tui_manager.core.environment import EnvironmentDetector
from tui_manager.i18n import DEFAULT_LANGUAGE, available_languages, set_language, t
from tui_manager.utils.logger import setup_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='tui-manager',
        description='Panel de control portable para la terminal '
                    '(inspirado en Omarchy).')
    parser.add_argument('--version', action='store_true',
                        help='muestra la versión y sale')
    parser.add_argument('--doctor', action='store_true',
                        help='diagnóstico del entorno y sale')
    parser.add_argument('--lang', choices=available_languages(), default=None,
                        help='idioma de la interfaz (por defecto: config)')
    return parser


def run_doctor() -> str:
    """Devuelve el informe de diagnóstico como texto multi-línea."""
    config = Config()
    lines = [f'{t("app.title")} — {t("doctor.title")}']

    def add(label, value, warn=False):
        state = t('doctor.warn') if warn else t('doctor.ok')
        lines.append(f'{label:<22} {value}  [{state}]')

    add(t('doctor.os'), f'{platform.system()} {platform.release()} '
        f'({platform.machine()})')
    try:
        distro = DistributionDetector.detect()
        add(t('doctor.distro'), distro)
    except DistributionError as exc:
        add(t('doctor.distro'), str(exc), warn=True)
        distro = None

    if distro:
        try:
            from tui_manager.core.package_manager import PackageManager
            pm = PackageManager(distribution=distro)
            add(t('doctor.pm'), f'{distro} → {type(pm.adapter).__name__}')
        except Exception as exc:
            add(t('doctor.pm'), str(exc), warn=True)

    try:
        env = EnvironmentDetector.detect()
        caps = ', '.join(sorted(c.name.lower() for c in env.capabilities())) or '—'
        add(t('doctor.env'), type(env).__name__)
        add(t('doctor.caps'), caps)
    except Exception as exc:
        add(t('doctor.env'), str(exc), warn=True)

    add(t('doctor.sudo'), shutil.which('sudo') or 'no (root directo/termux)',
        warn=shutil.which('sudo') is None and platform.system() == 'Linux'
        and not _is_termux())
    add(t('doctor.python'), sys.version.split()[0])

    try:
        import textual
        add(t('doctor.textual'), textual.__version__)
    except Exception as exc:
        add(t('doctor.textual'), str(exc), warn=True)

    exists = __import__('os').path.exists(config.config_file)
    add(t('doctor.cfg'), f'{config.config_file} '
        f'({"sí" if exists else "no (defaults)"})')
    return '\n'.join(lines)


def _is_termux() -> bool:
    return bool(__import__('os').environ.get('TERMUX_VERSION'))


def main(argv=None) -> int:
    """Punto de entrada; devuelve el código de salida."""
    args = build_parser().parse_args(argv)

    if args.version:
        print(f'tui-manager {__version__}')
        return 0

    config = Config()
    set_language(args.lang or config.get('language', DEFAULT_LANGUAGE))

    if args.doctor:
        setup_logger('TUI-Manager')
        print(run_doctor())
        return 0

    # Arranque normal de la TUI
    logger = setup_logger('TUI-Manager')
    try:
        from tui_manager.ui.app import Services, TuiManagerApp

        if sys.version_info < (3, 10):
            print('Error: TUI Manager requiere Python 3.10 o superior')
            return 1

        logger.info('Iniciando TUI Manager %s', __version__)
        services = Services.detect(config=config)
        logger.info('Distribución: %s | Entorno: %s',
                    services.distribution,
                    type(services.environment).__name__)
        TuiManagerApp(services).run()
        return 0

    except DistributionError as exc:
        print(f'{t("common.error")}: distribución no soportada ({exc})')
        print('Soportadas: debian, arch, fedora, void, freebsd, pkgsrc, termux')
        return 1
    except KeyboardInterrupt:
        logger.info('Cerrado por el usuario')
        return 0
    except Exception:
        logger.exception('Error crítico')
        print(f'{t("common.error")}: revisa el log de la aplicación')
        return 1


if __name__ == '__main__':
    sys.exit(main())
