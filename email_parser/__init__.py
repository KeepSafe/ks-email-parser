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

def _render_email(email, settings, fallback_locale=None):
    if not placeholder.validate_email(email, settings.source) and not settings.force:
        return False

    template, placeholders, ignored_plceholder_names = reader.read(email.full_path)
    if template:
        subject, text, html = renderer.render(email, template, placeholders, ignored_plceholder_names, settings)
        fs.save(email, subject, text, html, settings.destination, fallback_locale)
        return True
    else:
        return False

def parse_emails(settings):
    result = True

    if not settings.exclusive:
        shutil.rmtree(settings.destination, ignore_errors=True)

    emails = fs.emails(settings.source, settings.pattern, settings.exclusive)
    for email in emails:
        if _render_email(email, settings):
            logging.info('.', extra={'same_line': True})
        else:
            result = False
            default_locale_email = next(fs.email(settings.source, settings.pattern, email.name, settings.default_locale), None)
            if default_locale_email and _render_email(default_locale_email, settings, email.locale):
                logging.info('!', extra={'same_line': True})
                logging.warn("Email %s/%s substitued by %s/%s" % (email.locale, email.name, default_locale_email.locale, default_locale_email.name))
            else:
                logging.info('F', extra={'same_line': True})

    return result


def init_log(verbose):
    log_level = logging.DEBUG if verbose else logging.INFO
    handler = utils.ProgressConsoleHandler(stream=sys.stdout)
    logger.setLevel(log_level)
    logger.addHandler(handler)


# def handle_client_command(options):
#     client_name = options[consts.CMD_CLIENT]
#     client = clients.client(client_name)
#     logger.infp('parsing for client %s with options %s', client_name, options)
#     return client.parse(options)


def main():
    args = cmd.read_args()
    if args.version:
        result = cmd.print_version()
    elif args.command:
        result = cmd.execute_command(args)
    else:
        settings = cmd.read_settings(args)
        init_log(settings.verbose)
        result = parse_emails(settings)
    logger.info('All done', extra={'flush_errors': True})
    sys.exit(0) if result else sys.exit(1)


if __name__ == '__main__':
    main()
