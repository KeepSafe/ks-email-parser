"""
Handles command line and calls the email parser with corrent options.
"""

import argparse
from collections import namedtuple

from . import consts


DEFAULE_LOG_LEVEL = 'INFO'
DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
DEFAULT_TEMPLATES = 'templates_html'
DEFAULT_IMAGES_DIR = 'http://www.getkeepsafe.com/emails/img'
DEFAULT_RTL_CODES = 'ar,he'
DEFAULT_PATTERN = '{locale}/{name}.xml'


def default_options():
    return {
        consts.OPT_LOG_LEVEL: DEFAULE_LOG_LEVEL,
        consts.OPT_SOURCE: DEAFULT_SOURCE,
        consts.OPT_DESTINATION: DEFAULT_DESTINATION,
        consts.OPT_TEMPLATES: DEFAULT_TEMPLATES,
        consts.OPT_IMAGES: DEFAULT_IMAGES_DIR,
        consts.OPT_RIGHT_TO_LEFT: DEFAULT_RTL_CODES,
        consts.OPT_STRICT: True,
        consts.OPT_PATTERN: DEFAULT_PATTERN
    }


def read_args(argsargs=argparse.ArgumentParser):
    args = argsargs(epilog='Brought to you by KeepSafe - www.getkeepsafe.com')

    args.add_argument('-l', '--loglevel',
                      help='Specify log level (DEBUG, INFO, WARNING, ERROR, CRITICAL), default: %s'
                      % DEFAULE_LOG_LEVEL,
                      default=DEFAULE_LOG_LEVEL)
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
                             help='Parse templates in strict mode, failing for missing or extra placeholders',
                             action='store_true')
    args.add_argument('-p', '--pattern',
                      help='Email file search pattern, default: %s' % DEFAULT_PATTERN,
                      default=DEFAULT_PATTERN)
    args.add_argument('-v', '--version', help='Show version', action='store_true')

    subparsers = args.add_subparsers(help='Generate 3rd party template', dest='client')

    template_parser = subparsers.add_parser('customerio')
    template_parser.add_argument('email_name',
                                 help='Name of the email to generate the template for')

    return vars(args.parse_args())
