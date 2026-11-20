#!/usr/bin/env python3
"""
TUI Manager — punto de entrada.

Uso:
    tui-manager            lanza la interfaz TUI
    tui-manager --version  imprime la versión
    tui-manager --doctor   diagnóstico del entorno (SO, distro, gestor,
                           entorno de escritorio, capacidades, versiones de
                           CLIs, elevación)
    tui-manager --json X   datos estructurados (X=packages|processes|doctor)
                           como JSON a stdout, para scripts y agentes
    tui-manager --quickstart  recorrido guiado por las 10 entradas del menú
    tui-manager --lang es  fuerza el idioma (es|en) para esta ejecución

Inspired: Omarchy Quattro. Portable: Linux, BSD y Termux (limitado).
"""

from __future__ import annotations

import argparse
import logging
import platform
import shutil
import subprocess
import sys

from tui_manager import __version__
from tui_manager.core.config import Config
from tui_manager.core.distribution import DistributionDetector, DistributionError
from tui_manager.core.environment import EnvironmentDetector
from tui_manager.i18n import DEFAULT_LANGUAGE, available_languages, set_language, t
from tui_manager.utils.logger import setup_logger


# Gestores consultados por --doctor: SOLO se invoca `<cli> --version`.
CLI_VERSION_COMMANDS = ('apt', 'pacman', 'dnf', 'pkg', 'xbps-query')


def configure_non_interactive(manager) -> None:
    """Desactiva el hook de elevación en los adapters de una ruta CLI.

    ``--json`` y ``--doctor`` son no interactivos: nunca deben suspender una
    TUI ni pedir una contraseña. Con ``elevator=None`` el adapter usa solo
    ``sudo -n`` (o ``doas -n``) y, si no hay credenciales cacheadas, devuelve
    un mensaje accionable en lugar de lanzar el hook de la interfaz.
    """
    adapter = getattr(manager, 'adapter', None)
    if adapter is None:
        return
    try:
        adapter.elevator = None
    except Exception:  # adapter sine atributos (fake): nada que configurar
        pass


def _cli_version(command: str) -> str:
    """Devuelve la versión de una CLI, o «N/D» si no está disponible.

    Seguridad (B2-2): el único subproceso permitido es `<command> --version`,
    con salida capturada y timeout. Nunca se ejecuta una acción que pueda
    modificar el sistema, y cualquier error se degrada a «N/D».
    """
    try:
        result = subprocess.run(
            [command, '--version'],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return 'N/D'

    if result.returncode != 0:
        return 'N/D'
    output = (result.stdout or result.stderr).strip()
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    # Pacman y otras CLIs anteponen arte ASCII: elegir la línea con dígitos.
    for line in lines:
        if any(char.isdigit() for char in line):
            return line
    return lines[0] if lines else 'N/D'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='tui-manager',
        description='Panel de control portable para la terminal '
                    '(inspirado en Omarchy).')
    parser.add_argument('--version', action='store_true',
                        help='muestra la versión y sale')
    parser.add_argument('--doctor', action='store_true',
                        help='diagnóstico del entorno y sale')
    parser.add_argument('--json', choices=('packages', 'processes', 'doctor'),
                        default=None, metavar='KIND',
                        help='datos estructurados (packages|processes|doctor) '
                             'como JSON en stdout')
    parser.add_argument('--quickstart', action='store_true',
                        help='recorrido guiado por el menú y sale')
    parser.add_argument('--lang', choices=available_languages(), default=None,
                        help='idioma de la interfaz (por defecto: config)')
    return parser


def collect_doctor_data() -> dict:
    """Recoge el diagnóstico en forma estructurada (única fuente de verdad).

    Tanto el informe de texto (:func:`run_doctor`) como la salida
    ``--json doctor`` consumen esta función. Así la lógica de subprocess
    (``_cli_version``: solo ``<cli> --version``) y la detección de entorno no
    se duplican: hay una sola implementación compartida.

    Devuelve un dict con:
      * ``distribution``: distro detectada o ``None`` si falló.
      * ``rows``: lista de ``{'key', 'value', 'warn'}`` en orden de informe.
      * ``suggestions``: claves i18n de sugerencias (únicas, orden estable).
    """
    config = Config()
    rows = []

    def add(key, value, warn=False):
        rows.append({'key': key, 'value': str(value), 'warn': bool(warn)})

    add('doctor.os', f'{platform.system()} {platform.release()} '
        f'({platform.machine()})')
    try:
        distro = DistributionDetector.detect()
        add('doctor.distro', distro)
    except DistributionError as exc:
        add('doctor.distro', str(exc), warn=True)
        distro = None

    if distro:
        try:
            from tui_manager.core.package_manager import PackageManager
            pm = PackageManager(distribution=distro)
            configure_non_interactive(pm)
            add('doctor.pm', f'{distro} → {type(pm.adapter).__name__}')
        except Exception as exc:
            add('doctor.pm', str(exc), warn=True)

    try:
        env = EnvironmentDetector.detect()
        caps = ', '.join(sorted(c.name.lower() for c in env.capabilities())) or '—'
        add('doctor.env', type(env).__name__)
        add('doctor.caps', caps)
    except Exception as exc:
        add('doctor.env', str(exc), warn=True)

    # Versiones de CLIs (B2-2): únicamente `<cli> --version`, sin efectos
    # en el sistema. Las ausentes se degradan a «N/D» con estado de aviso.
    cli_versions = {}
    for cli in CLI_VERSION_COMMANDS:
        version = _cli_version(cli)
        cli_versions[cli] = version
        add(cli, version, warn=version == 'N/D')

    add('doctor.sudo', shutil.which('sudo') or 'no (root directo/termux)',
        warn=shutil.which('sudo') is None and platform.system() == 'Linux'
        and not _is_termux())
    add('doctor.python', sys.version.split()[0])

    try:
        import textual
        add('doctor.textual', textual.__version__)
    except Exception as exc:
        add('doctor.textual', str(exc), warn=True)

    exists = __import__('os').path.exists(config.config_file)
    add('doctor.cfg', f'{config.config_file} '
        f'({"sí" if exists else "no (defaults)"})')

    # Criterio 15 de 1.0: además de informar, sugerir el fix concreto.
    suggestions = []
    if distro is None:
        suggestions.append('doctor.fix.distro')
    for cli in CLI_VERSION_COMMANDS:
        if cli_versions.get(cli) == 'N/D':
            suggestions.append('doctor.fix.cli')
            break
    try:
        import textual  # noqa: F401
    except Exception:
        suggestions.append('doctor.fix.textual')

    seen = set()
    unique_suggestions = []
    for key in suggestions:
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(key)

    return {
        'distribution': distro,
        'rows': rows,
        'suggestions': unique_suggestions,
    }


def run_doctor() -> str:
    """Devuelve el informe de diagnóstico como texto multi-línea."""
    data = collect_doctor_data()
    lines = [f'{t("app.title")} — {t("doctor.title")}']

    for row in data['rows']:
        state = t('doctor.warn') if row['warn'] else t('doctor.ok')
        label = t(row['key'])
        lines.append(f'{label:<22} {row["value"]}  [{state}]')

    if data['suggestions']:
        lines.append('')
        lines.append(t('doctor.fix.title'))
        for key in data['suggestions']:
            lines.append(f'  - {t(key)}')
    return '\n'.join(lines)


def run_quickstart() -> str:
    """Devuelve el recorrido guiado del menú como texto multi-línea.

    La lógica vive en ``screens.quickstart_text`` para reutilizar la lista de
    entradas y los atajos de ``MainMenuScreen`` como única fuente de verdad.
    No inicia la TUI y no ejecuta subprocesos: solo compone texto plano con
    claves i18n existentes (``menu.*``) y las nuevas ``quickstart.*``.
    """
    from tui_manager.ui.screens import quickstart_text
    return quickstart_text()


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

    if args.json:
        # Import diferido para evitar importación circular con main.py.
        # La ruta JSON NO configura el logger: su StreamHandler(sys.stdout)
        # mezclaría logs con el JSON. cli_json silencia logging de forma
        # temporal y escribe errores en stderr con exit code 1.
        # Ruta no interactiva: los adapters creados aquí no reciben el hook
        # `elevator` de la TUI, por lo que solo usan `sudo -n` y degradan con
        # un mensaje accionable si no hay credenciales cacheadas.
        from tui_manager.cli_json import emit_json
        return emit_json(args.json)

    if args.doctor:
        setup_logger('TUI-Manager')
        print(run_doctor())
        return 0

    if args.quickstart:
        print(run_quickstart())
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
