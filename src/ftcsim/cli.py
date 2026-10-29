"""Installed command line entry point."""
import argparse
import logging
from pathlib import Path
from aiohttp import web
from rich.console import Console
from rich.logging import RichHandler
from . import __version__
from . import wizard
from .server import create_app


def port(value):
    result = int(value)
    if not 1 <= result <= 65535:
        raise argparse.ArgumentTypeError('Port must be between 1 and 65535')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='ftcsim',
        description='Run the simulator server, or configure an FTC project with --wizard.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Examples:\n  ftcsim                         Start the simulator\n'
               '  ftcsim --dev                   Use the npm Driver Station dev server\n'
               '  ftcsim --port 9016             Use a different simulator port\n'
               '  ftcsim --wizard                Configure the current project\n'
               '  ftcsim -w --project /path/to/robot --dry-run',
    )
    parser._optionals.title = 'General options'
    parser.add_argument('--version', action='version', version=f'ftcsim {__version__}')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging in either mode')
    simulator_options = parser.add_argument_group('Simulator options', 'Used when --wizard is omitted.')
    simulator_options.add_argument('--port', type=port, default=None, help='HTTP/WebSocket port (default: 9015)')
    simulator_options.add_argument('--dev', action='store_true', help='Run simulator APIs without serving the bundled Driver Station (use npm run dev)')
    wizard_options = parser.add_argument_group('Wizard options', 'Configure a project; setup flags require --wizard.')
    wizard_options.add_argument('-w', '--wizard', action='store_true', help='Run the project setup wizard instead of the simulator')
    wizard.add_arguments(wizard_options)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(message)s', handlers=[RichHandler(show_path=False)])
    if args.wizard:
        if args.port is not None:
            parser.error('--port is a simulator option and cannot be used with --wizard')
        if args.dev:
            parser.error('--dev is a simulator option and cannot be used with --wizard')
        return wizard.run(args)
    if any((args.sdk, args.copy_sdk, args.opmode, args.kotlin_version, args.dry_run, args.yes, args.force)) or args.project != Path.cwd():
        parser.error('Project setup options require --wizard')
    if args.port is None:
        args.port = 9015
    try:
        logger = logging.getLogger('ftcsim')
        if args.dev:
            logger.info('Simulator APIs: http://localhost:%s/sim (development mode)', args.port)
            logger.info('Run npm run dev in driver-station/ and open http://127.0.0.1:5173/ds/')
        else:
            logger.info('Driver Station: http://localhost:%s/ds', args.port)
        web.run_app(create_app(dev=args.dev), host='127.0.0.1', port=args.port,
                    shutdown_timeout=1, print=None)
    except OSError as error:
        Console(stderr=True).print(f'Cannot start simulator: {error}', style='red', markup=False)
        return 1
    return 0
