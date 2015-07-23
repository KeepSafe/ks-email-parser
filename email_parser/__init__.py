"""
    email_parser
    ~~~~~~~~~~

    Parses emails from a source directory and outputs text and html format.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""

import logging
import sys
from . import cmd, fs, reader, renderer, clients, placeholder

logger = logging.getLogger()

def parse_emails(options=None):
    options = options or cmd.default_options()
    emails = fs.emails(options[consts.OPT_SOURCE], options[consts.OPT_PATTERN])
    for email in emails:
        logging.info('parsing {}'.format(email.path))
        if not placeholder.validate_email(email, options[consts.OPT_SOURCE]) and not options[consts.OPT_FORCE]:
            break
        template, placeholders, ignored_plceholder_names = reader.read(email.full_path)
        if template:
            subject, text, html = renderer.render(email, template, placeholders, ignored_plceholder_names, options)
            fs.save(email, subject, text, html, options[consts.OPT_DESTINATION])


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'INFO')
    logging.basicConfig(stream=sys.stdout, level=num_level, format='%(message)s')


def handle_client_command(options):
    client_name = options[consts.CMD_CLIENT]
    client = clients.client(client_name)
    logger.infp('parsing for client %s with options %s', client_name, options)
    client.parse(options)


def handle_placeholder_command(options):
    logger.info('generating config for placeholders')
    placeholder.generate_config(options)


command_dispatcher = {
    consts.CMD_CLIENT: handle_client_command,
    consts.CMD_CONFIG_PLACEHOLDERS: handle_placeholder_command
}


def main():
    options = cmd.read_args()
    if options.get('version'):
        import pkg_resources
        version = pkg_resources.require('ks-email-parser')[0].version
        print(version)
        return
    init_log(options[consts.OPT_LOG_LEVEL])
    if options.get(consts.OPT_COMMAND) is not None:
        command_dispatcher[options[consts.OPT_COMMAND]](options)
    else:
        parse_emails(options)


if __name__ == '__main__':
    main()
