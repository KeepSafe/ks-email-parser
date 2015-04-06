"""
    email_parser
    ~~~~~~~~~~

    Parses emails from a source directory and outputs text and html format.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""

import logging
import sys
from . import cmd, fs, reader, renderer


def parse_emails(options=None):
    options = options or cmd.default_options()
    emails = fs.emails(options[consts.OPT_SOURCE], options[consts.OPT_PATTERN])
    for email in emails:
        logging.debug('parsing {}'.format(email.path))
        template, placeholders, ignored_plceholder_names = reader.read(email.full_path)
        if template:
            subject, text, html = renderer.render(email, template, placeholders, ignored_plceholder_names, options)
            fs.save(email, subject, text, html, options[consts.OPT_DESTINATION])


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'INFO')
    logging.basicConfig(level=num_level, format='%(message)s')


def main():
    options = cmd.read_args()
    init_log(options[consts.OPT_LOG_LEVEL])
    if options.get(consts.OPT_CLIENT) is None:
        parse_emails(options)
    else:
        client = client(options[consts.OPT_CLIENT])
        client.parse(options, email_name)


if __name__ == '__main__':
    main()
