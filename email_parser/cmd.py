"""
Handles command line and calls the email parser with corrent options.
"""

import argparse
import logging
from collections import namedtuple

from . import consts


DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
DEFAULT_TEMPLATES = 'templates_html'
DEFAULT_IMAGES_DIR = 'http://www.getkeepsafe.com/emails/img'
DEFAULT_RTL_CODES = 'ar,he'
DEFAULT_PATTERN = '{locale}/{name}.xml'

logger = logging.getLogger()

def default_options():
    return {
        consts.OPT_VERBOSE: False,
        consts.OPT_SOURCE: DEAFULT_SOURCE,
        consts.OPT_DESTINATION: DEFAULT_DESTINATION,
        consts.OPT_TEMPLATES: DEFAULT_TEMPLATES,
        consts.OPT_IMAGES: DEFAULT_IMAGES_DIR,
        consts.OPT_RIGHT_TO_LEFT: DEFAULT_RTL_CODES,
        consts.OPT_STRICT: True,
        consts.OPT_FORCE: False,
        consts.OPT_PATTERN: DEFAULT_PATTERN
    }


def read_args(argsargs=argparse.ArgumentParser):
    logger.debug('reading arguments list')
    args = argsargs(epilog='Brought to you by KeepSafe - www.getkeepsafe.com')

    args.add_argument('-s', '--source',
                      help='args\'s source folder, default: %s' % DEAFULT_SOURCE,
                      default=DEAFULT_SOURCE)
    args.add_argument('-d', '--destination',
                      help='args\'s destination folder, default: %s' % DEFAULT_DESTINATION,
                      default=DEFAULT_DESTINATION)
    args.add_argument('-t', '--templates',
                      help='Templates folder, default: %s' % DEFAULT_TEMPLATES,
                      default=DEFAULT_TEMPLATES)
    args.add_argument('-rtl', '--right-to-left',
                      help='Comma separated list of RTL language codes, default: %s' % DEFAULT_RTL_CODES,
                      default=DEFAULT_RTL_CODES)
    args.add_argument('-i', '--images',
                      help='Images base directory, default: %s' % DEFAULT_IMAGES_DIR,
                      default=DEFAULT_IMAGES_DIR)
    args.add_argument('-st', '--strict',
                             help='Disable strict mode, allow templates with unfilled parameters',
                             action='store_false')
    args.add_argument('-p', '--pattern',
                      help='Email file search pattern, default: %s' % DEFAULT_PATTERN,
                      default=DEFAULT_PATTERN)
    args.add_argument('-v', '--version', help='Show version', action='store_true')
    args.add_argument('-f', '--force', help='Generate emails despite errors', action='store_true')
    args.add_argument('-vv', '--verbose', help='Generate emails despite errors', action='store_true')

    subparsers = args.add_subparsers(help='Parser additional commands', dest='command')

    template_parser = subparsers.add_parser('client')
    template_parser.add_argument('client', help='Provider name')
    template_parser.add_argument('email_name',
                                 help='Name of the email to generate the template for')

    config_parser = subparsers.add_parser('config_placeholders')

    return vars(args.parse_args())
