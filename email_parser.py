import argparse
import logging
import os


DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'


def list_locales(path):
    return [locale for locale in os.listdir(path) if os.path.isdir(os.path.join(path, locale))]


def parse_emails(src_path, dest_path):
    locales = list_locales(src_path)


def read_args():
    args_parser = argparse.ArgumentParser()

    args_parser.add_argument('-l', '--loglevel', help='Specify log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)',
                             default='WARNING')
    args_parser.add_argument('-s', '--source_path',
                             help='Templates source folder',
                             default=DEAFULT_SOURCE)
    args_parser.add_argument('-d', '--destination_path',
                             help='Parser destination folder',
                             default=DEFAULT_DESTINATION)

    return args_parser.parse_args()


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'WARNING')
    logging.basicConfig(level=num_level)


def main():
    logging.debug('Starting script')
    args = read_args()
    logging.debug('Arguments from console: %s', args)
    init_log(args['loglevel'])

    parse_emails(args['source_path'], args['destination_path'])

if __name__ == '__main__':
    main()
