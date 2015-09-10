"""
Each email service has it's own client. The client is responsible for generating email for the service to process.
"""

from . import fs, reader, renderer
import logging

logger = logging.getLogger()


class CustomerIoClient(object):

    """
    Generates file for customer.io
    Custmer.io has a custom formatting for emails http://customer.io/docs/localization-i18n.html
    """
    _start_locale_selection = '{{% if customer.language == "{}" %}}'
    _next_locale_selection = '{{% elsif customer.language == "{}" %}}'
    _end_locale_selection = '{% endif %}'

    def _append_content(self, locale, old_content, new_content):
        if old_content:
            content = old_content + '\n' + self._next_locale_selection.format(locale) + '\n' + new_content
        else:
            content = self._start_locale_selection.format(locale) + '\n' + new_content
        return content

    def parse(self, email_name, settings):
        emails = fs.email(settings.source, settings.pattern, email_name)
        subject, text, html, last_email = '', '', '', None
        for email in emails:
            logger.info('parsing email %s locale %s', email.name, email.locale)
            template, placeholders, ignored_plceholder_names = reader.read(email.full_path)
            email_subject, email_text, email_html = renderer.render(
                email, template, placeholders, ignored_plceholder_names, settings)
            subject = self._append_content(email.locale, subject, email_subject)
            text = self._append_content(email.locale, text, email_text)
            html = self._append_content(email.locale, html, email_html)
            last_email = email
        if not last_email:
            logger.error('No emails found for given name %s' % email_name)
            return False
        subject = subject + '\n' + self._end_locale_selection
        text = text + '\n' + self._end_locale_selection
        html = html + '\n' + self._end_locale_selection
        email = fs.Email(last_email.name, '', last_email.path, last_email.full_path)
        fs.save(email, subject, text, html, settings.destination)
        return True


_clients = {
    'customerio': CustomerIoClient()
}


def client(client_name):
    return _clients[client_name]
