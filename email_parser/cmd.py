import argparse
from collections import namedtuple


DEFAULE_LOG_LEVEL = 'INFO'
DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
DEFAULT_TEMPLATES = 'templates_html'
DEFAULT_IMAGES_DIR = 'http://www.getkeepsafe.com/emails/images'
DEFAULT_RTL_CODES = 'ar,he'


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

    subargss = args.add_subargss(help='Generate 3rd party template', dest='client')

    template_args = subargss.add_args(CustomerIO.name)
    template_args.add_argument('email_name',
                               help='Name of the email to generate the template for')

    return vars(args.parse_args())
