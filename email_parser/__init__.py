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
import asyncio
import concurrent.futures
from itertools import islice
from functools import reduce
from multiprocessing import Manager, Queue
from . import cmd, fs, reader, renderer, clients, placeholder, utils

logger = logging.getLogger()
loop = asyncio.get_event_loop()
loop.set_debug(False)


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


def _parse_email(email, settings):
    if _render_email(email, settings):
        logging.info('.', extra={'same_line': True})
        return True
    else:
        default_locale_email = next(
            fs.email(settings.source, settings.pattern, email.name, settings.default_locale), None)
        if default_locale_email and _render_email(default_locale_email, settings, email.locale):
            logging.info('F', extra={'same_line': True})
            logging.warn('Email %s/%s substituted by %s/%s' %
                         (email.locale, email.name, default_locale_email.locale, default_locale_email.name))
        else:
            logging.info('E', extra={'same_line': True})
        return False


def _parse_emails_batch(emails, settings):
    results = [_parse_email(email, settings) for email in emails]
    result = reduce(lambda acc, res: acc and res, results)
    return result


@asyncio.coroutine
def _emails_worker(executor, emails, settings):
    result = yield from loop.run_in_executor(executor, _parse_emails_batch, emails, settings)
    return result


def _parse_emails(settings):
    if not settings.exclusive:
        shutil.rmtree(settings.destination, ignore_errors=True)

    emails = iter(fs.emails(settings.source, settings.pattern, settings.exclusive))
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=settings.workers_pool)
    tasks = []

    emails_batch = list(islice(emails, settings.workers_pool))
    while emails_batch:
        task = loop.run_in_executor(executor, _parse_emails_batch, emails_batch, settings)
        tasks.append(task)
        emails_batch = list(islice(emails, settings.workers_pool))
    results = yield from asyncio.gather(*tasks)
    result = reduce(lambda acc, result: True if acc and result else False, results)
    return result


def parse_emails(settings):
    result = loop.run_until_complete(_parse_emails(settings))
    return result


def init_log(verbose):
    log_level = logging.DEBUG if verbose else logging.INFO
    error_msgs_queue = Manager().Queue()
    warning_msgs_queue = Manager().Queue()
    handler = utils.ProgressConsoleHandler(error_msgs_queue, warning_msgs_queue, stream=sys.stdout)
    logger.setLevel(log_level)
    logger.addHandler(handler)


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
    logger.info('\nAll done', extra={'flush_errors': True})
    sys.exit(0) if result else sys.exit(1)


if __name__ == '__main__':
    main()
