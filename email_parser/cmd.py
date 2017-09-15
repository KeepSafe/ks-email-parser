"""
Handles command line and calls the email parser with corrent options.
"""

import argparse
import logging
import sys
import os
import shutil
import asyncio
import concurrent.futures
from itertools import islice
from functools import reduce
from multiprocessing import Manager

from . import const, Parser, config, fs

logger = logging.getLogger(__name__)


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


def read_args(argsargs=argparse.ArgumentParser):
    logger.debug('reading arguments list')
    args = argsargs(epilog='Brought to you by KeepSafe - www.getkeepsafe.com')

    args.add_argument('-i', '--images', help='Images base directory')
    args.add_argument('-vv', '--verbose', help='Generate emails despite errors', action='store_true')
    args.add_argument('-v', '--version', help='Show version', action='store_true')

    subparsers = args.add_subparsers(help='Parser additional commands', dest='command')

    config_parser = subparsers.add_parser('config')
    config_parser.add_argument('config_name', help='Name of config to generate. Available: `placeholders`')

    return args.parse_args()


def _parse_and_save(email, parser):
    result = parser.render_email(email)
    if result:
        subject, text, html = result
        fs.save_parsed_email(parser.root_path, email, subject, text, html)
        return True
    else:
        return False


def _parse_emails_batch(emails, parser):
    results = [_parse_and_save(email, parser) for email in emails]
    result = reduce(lambda acc, res: acc and res, results)
    return result


def _parse_emails(loop, root_path):
    shutil.rmtree(os.path.join(root_path, config.paths.destination), ignore_errors=True)
    emails = fs.emails(root_path)
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=const.DEFAULT_WORKER_POOL)
    tasks = []
    parser = Parser(root_path)

    emails_batch = list(islice(emails, const.DEFAULT_WORKER_POOL))
    while emails_batch:
        task = loop.run_in_executor(executor, _parse_emails_batch, emails_batch, parser)
        tasks.append(task)
        emails_batch = list(islice(emails, const.DEFAULT_WORKER_POOL))
    results = yield from asyncio.gather(*tasks)
    result = reduce(lambda acc, result: True if acc and result else False, results)
    return result


def parse_emails(root_path):
    loop = init_loop()
    result = loop.run_until_complete(_parse_emails(loop, root_path))
    return result


def print_version():
    import pkg_resources
    version = pkg_resources.require('ks-email-parser')[0].version
    print(version)
    return True


def generate_config(root_path):
    logger.info('generating config for placeholders')
    Parser(root_path).refresh_email_placeholders_config()
    return True


def execute_command(args):
    if args.command == 'config' and args.config_name == 'placeholders':
        return generate_config(args)
    return False


def init_log(verbose):
    log_level = logging.DEBUG if verbose else logging.INFO
    error_msgs_queue = Manager().Queue()
    warning_msgs_queue = Manager().Queue()
    handler = ProgressConsoleHandler(error_msgs_queue, warning_msgs_queue, stream=sys.stdout)
    logger.setLevel(log_level)
    logger.addHandler(handler)


def init_loop():
    loop = asyncio.get_event_loop()
    loop.set_debug(False)
    return loop


def main():
    root_path = os.getcwd()
    args = read_args()
    init_log(args.verbose)
    if args.images:
        config.base_img_path = args.images
    if args.version:
        result = print_version()
    elif args.command:
        result = execute_command(args)
    else:
        result = parse_emails(root_path)
    logger.info('\nAll done', extra={'flush_errors': True})
    sys.exit(0) if result else sys.exit(1)


if __name__ == '__main__':
    main()
