import logging


class ProgressConsoleHandler(logging.StreamHandler):
    error_msgs = []
    warning_msgs = []
    store_msg_loglevels = (logging.ERROR, logging.WARN)

    on_same_line = False
    flush_errors = False

    def _store_msg(self, msg, loglevel):
        if loglevel == logging.ERROR:
            self.error_msgs.append(msg)
        if loglevel == logging.WARN:
            self.warning_msgs.append(msg)

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
        if self.error_msgs:
            self._flush_store(stream, self.error_msgs, 'ERRORS:')
        if self.warning_msgs:
            self._flush_store(stream, self.warning_msgs, 'WARNINGS:')

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
