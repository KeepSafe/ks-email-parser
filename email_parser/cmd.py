import argparse
from collections import namedtuple


DEFAULE_LOG_LEVEL = 'WARNING'
DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
DEFAULT_TEMPLATES = 'templates_html'
DEFAULT_IMAGES_DIR = 'http://www.getkeepsafe.com/emails/images'


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
                      help='Comma separated list of RTL language codes, default: %s' % RTL_CODES,
                      default=RTL_CODES)
    args.add_argument('-i', '--images',
                      help='Images base directory, default: %s' % DEFAULT_IMAGES_DIR,
                      default=DEFAULT_IMAGES_DIR)
    args.add_argument('-st', '--strict',
                             help='Parse templates in strict mode, failing for missing or extra placeholders',
                             action='store_true')

    subargss = args.add_subargss(help='Generate 3rd party template', dest='client')

    template_args = subargss.add_args(CustomerIOargs.name)
    template_args.add_argument('email_name',
                               help='Name of the email to generate the template for')

    return args.parse_args()


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'WARNING')
    logging.basicConfig(level=num_level)


def run():
    print('Parsing emails...')
    args = cmd.read_args()
    init_log(args.loglevel)
    logging.debug('Starting script')
    logging.debug('Arguments from console: %s', args)
    if args.client is None:
        parse_emails(args.source, args.destination, args.templates, args.right_to_left, args.images, args.strict)
    else:
        client = parsers[args.client]
        client.generate_template(args.source, args.destination, args.templates, args.email_name, args.strict)
    print('Done')