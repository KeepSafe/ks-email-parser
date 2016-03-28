"""
Handles command line and calls the email parser with corrent options.
"""

import argparse
import logging
from collections import namedtuple

from . import placeholder

logger = logging.getLogger()

ShortenerSettings = namedtuple('ShortenerSettings', [
    'name',
    'properties'
])

Settings = namedtuple('Settings', [
    'source',
    'destination',
    'templates',
    'images',
    'pattern',
    'right_to_left',
    'strict',
    'force',
    'verbose',
    'shortener',
    'exclusive',
    'default_locale',
    'workers_pool',
    'local_images',
    'save',  # Shell script to be called on save from gui
    'cms_service_host'
])


def default_settings():
    return Settings(
        verbose=False,
        strict=True,
        force=False,
        source='src',
        destination='target',
        templates='templates_html',
        images='http://www.getkeepsafe.com/emails/img',
        right_to_left=['ar', 'he'],
        pattern='{locale}/{name}.xml',
        shortener={},
        exclusive=None,
        default_locale='en',
        workers_pool=10,
        local_images='templates_html/img',
        save=None,
        cms_service_host="http://localhost:5001"
    )


def read_args(argsargs=argparse.ArgumentParser):
    settings = default_settings()
    logger.debug('reading arguments list')
    args = argsargs(epilog='Brought to you by KeepSafe - www.getkeepsafe.com')

    args.add_argument('-s', '--source', help='args\'s source folder, default: %s' % settings.source)
    args.add_argument(
        '-e', '--exclusive', help='Exclusive path of subset emails to compile, default: %s' % settings.exclusive)
    args.add_argument('-d', '--destination',
                      help='args\'s destination folder, default: %s' % settings.destination)
    args.add_argument('-t', '--templates', help='Templates folder, default: %s' % settings.templates)
    args.add_argument('-rtl', '--right-to-left',
                      help='Comma separated list of RTL language codes, default: %s' % settings.right_to_left)
    args.add_argument('-i', '--images', help='Images base directory, default: %s' % settings.images)
    args.add_argument('-p', '--pattern', help='Email file search pattern, default: %s' % settings.pattern)

    args.add_argument('-nst', '--not-strict',
                      help='Disable strict mode, allow templates with unfilled parameters',
                      action='store_false')
    args.add_argument('-f', '--force', help='Generate emails despite errors', action='store_true')
    args.add_argument('-wp', '--workers-pool',
                      help='Number of workers, default: %s' % settings.workers_pool, type=int)
    args.add_argument('-vv', '--verbose', help='Generate emails despite errors', action='store_true')
    args.add_argument('-v', '--version', help='Show version', action='store_true')

    subparsers = args.add_subparsers(help='Parser additional commands', dest='command')

    template_parser = subparsers.add_parser('client')
    template_parser.add_argument('client', help='Provider name')
    template_parser.add_argument('email_name',
                                 help='Name of the email to generate the template for')

    config_parser = subparsers.add_parser('config')
    config_parser.add_argument('config_name', help='Name of config to generate')

    gui_parser = subparsers.add_parser('gui')
    gui_parser.add_argument('-P', '--port', type=int, help='Port to serve on', default=8080)
    gui_parser.add_argument('-I', '--local-images', type=str, help='Server image directory',
                            default='templates_html/img')
    gui_parser.add_argument('--save', type=str, help='Shell script to call after save action')
    gui_parser.add_argument('-s', '--cms-service-host', type=str, help='email-service\'s URL')

    return args.parse_args()


def read_settings(args):
    args = vars(args)
    settings = default_settings()._asdict()
    for k in settings:
        if k in args and args[k] is not None:
            settings[k] = args[k]
    return Settings(**settings)


def print_version():
    import pkg_resources
    version = pkg_resources.require('ks-email-parser')[0].version
    print(version)
    return True


def generate_config(args):
    if args.config_name == 'placeholders':
        logger.info('generating config for placeholders')
        settings = read_settings(args)
        placeholder.generate_config(settings)
        return True
    return False


def execute_command(args):
    if args.command == 'config':
        return generate_config(args)
    elif args.command == 'gui':
        from .gui.gui import serve
        serve(args)
        return True
    return False
