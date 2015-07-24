"""
    email_parser
    ~~~~~~~~~~

    Parses emails from a source directory and outputs text and html format.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""

import logging
import sys
import shutil
from . import cmd, fs, reader, renderer, clients, placeholder, utils

logger = logging.getLogger()


def parse_emails(options=None):
    result = True
    options = options or cmd.default_options()
    shutil.rmtree(options[consts.OPT_DESTINATION])
    emails = fs.emails(options[consts.OPT_SOURCE], options[consts.OPT_PATTERN])
    for email in emails:
        if not placeholder.validate_email(email, options[consts.OPT_SOURCE]):
            result = False
            logging.info('F', extra={'same_line': True})
            continue
        template, placeholders, ignored_plceholder_names = reader.read(email.full_path)
        if template:
            subject, text, html = renderer.render(email, template, placeholders, ignored_plceholder_names, options)
            logging.info('.', extra={'same_line': True})
            fs.save(email, subject, text, html, options[consts.OPT_DESTINATION])
        else:
            logging.info('F', extra={'same_line': True})
    return result


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'INFO')
    handler = utils.ProgressConsoleHandler(stream=sys.stdout)
    logger.setLevel(num_level)
    logger.addHandler(handler)


def handle_client_command(options):
    client_name = options[consts.CMD_CLIENT]
    client = clients.client(client_name)
    logger.infp('parsing for client %s with options %s', client_name, options)
    return client.parse(options)


def handle_placeholder_command(options):
    logger.info('generating config for placeholders')
    return placeholder.generate_config(options)


command_dispatcher = {
    consts.CMD_CLIENT: handle_client_command,
    consts.CMD_CONFIG_PLACEHOLDERS: handle_placeholder_command
}


def main():
    result = True
    options = cmd.read_args()
    if options.get('version'):
        import pkg_resources
        version = pkg_resources.require('ks-email-parser')[0].version
        print(version)
        return
    init_log(options[consts.OPT_LOG_LEVEL])
    if options.get(consts.OPT_COMMAND) is not None:
        result = command_dispatcher[options[consts.OPT_COMMAND]](options)
    else:
        result = parse_emails(options)
    logging.info('All done', extra={'flush_errors': True})
    return 0 if result else 1


if __name__ == '__main__':
    main()
