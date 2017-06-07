import logging
import sys
import shutil
import asyncio
import concurrent.futures
from itertools import islice
from functools import reduce
from multiprocessing import Manager
from . import cmd, fs, reader, renderer, placeholder

logger = logging.getLogger(__name__)
loop = asyncio.get_event_loop()
loop.set_debug(False)


class ProgressConsoleHandler(logging.StreamHandler):
    store_msg_loglevels = (logging.ERROR, logging.WARN)

    on_same_line = False
    flush_errors = False

    def __init__(self, err_queue, warn_queue, *args, **kwargs):
        self.err_msgs_queue = err_queue
        self.warn_msgs_queue = warn_queue
        super(ProgressConsoleHandler, self).__init__(*args, **kwargs)

    def _store_msg(self, msg, loglevel):
        if loglevel == logging.ERROR:
            self.err_msgs_queue.put(msg)
        if loglevel == logging.WARN:
            self.warn_msgs_queue.put(msg)

    def error_msgs(self):
        while not self.err_msgs_queue.empty():
            yield self.err_msgs_queue.get()

    def warning_msgs(self):
        while not self.warn_msgs_queue.empty():
            yield self.warn_msgs_queue.get()

    def _print_msg(self, stream, msg, record):
        same_line = hasattr(record, 'same_line')
        if self.on_same_line and not same_line:
            stream.write(self.terminator)
        stream.write(msg)
        if same_line:
            self.on_same_line = True
        else:
            stream.write(self.terminator)
            self.on_same_line = False
        self.flush()

    def _flush_store(self, stream, msgs, header):
        stream.write(self.terminator)
        stream.write(header)
        stream.write(self.terminator)
        for idx, msg in enumerate(msgs):
            stream.write('%s. %s' % (idx + 1, msg))
            stream.write(self.terminator)

    def _flush_errors(self, stream):
        if not self.err_msgs_queue.empty():
            self._flush_store(stream, self.error_msgs(), 'ERRORS:')
        if not self.warn_msgs_queue.empty():
            self._flush_store(stream, self.warning_msgs(), 'WARNINGS:')

    def _write_msg(self, stream, msg, record):
        flush_errors = hasattr(record, 'flush_errors')
        if flush_errors:
            self._flush_errors(stream)
        self._print_msg(stream, msg, record)

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if record.levelno in self.store_msg_loglevels:
                self._store_msg(msg, record.levelno)
            else:
                self._write_msg(stream, msg, record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def _render_email(email, link_locale_mappings, settings, fallback_locale=None):
    if not placeholder.validate_email(settings, email) and not settings.force:
        return False

    template, placeholders, ignored_plceholder_names = reader.read(email, settings)
    if template:
        subjects, text, html = renderer.render(email, template, placeholders, ignored_plceholder_names,
                                               link_locale_mappings, settings)
        fs.save(email, subjects, text, html, settings.destination, fallback_locale)
        return True
    else:
        return False


def _parse_email(email, link_locale_mappings, settings):
    if _render_email(email, link_locale_mappings, settings):
        logger.info('.', extra={'same_line': True})
        return True
    else:
        # TODO create default_locale_email function in fs module
        default_locale_email = fs.email(settings.source, settings.pattern, email.name, settings.default_locale)
        if default_locale_email and _render_email(default_locale_email, link_locale_mappings, settings, email.locale):
            logger.info('F', extra={'same_line': True})
            logger.warn('Email %s/%s substituted by %s/%s' %
                        (email.locale, email.name, default_locale_email.locale, default_locale_email.name))
        else:
            logger.info('E', extra={'same_line': True})
        return False


def _parse_emails_batch(emails, link_locale_mappings, settings):
    results = [_parse_email(email, link_locale_mappings, settings) for email in emails]
    result = reduce(lambda acc, res: acc and res, results)
    return result


def _parse_emails(settings):
    if not settings.exclusive:
        shutil.rmtree(settings.destination, ignore_errors=True)

    link_locale_mappings = reader.read_link_locale_mappings(settings)
    if not link_locale_mappings and not settings.force:
        return False

    emails = iter(fs.emails(settings.source, settings.pattern, settings.exclusive))

    executor = concurrent.futures.ProcessPoolExecutor(max_workers=settings.workers_pool)
    tasks = []

    emails_batch = list(islice(emails, settings.workers_pool))
    while emails_batch:
        task = loop.run_in_executor(executor, _parse_emails_batch, emails_batch, link_locale_mappings, settings)
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
    handler = ProgressConsoleHandler(error_msgs_queue, warning_msgs_queue, stream=sys.stdout)
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
