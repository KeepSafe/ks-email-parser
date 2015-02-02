from . import fs, reader, renderer, consts

class CustomIoClient(object):
    _start_locale_selection = '{{% if customer.language == "{}" %}}'
    _next_locale_selection = '{{% elsif customer.language == "{}" %}}'
    _end_locale_selection = '{% endif %}'

    def _append_content(self, locale, old_content, new_content):
        if old_content:
            content = old_content + '\n' + self._next_locale_selection.format(locale) + '\n' +  new_content
        else:
            content = self._start_locale_selection.format(locale) + '\n' +  new_content
        return content

    def parse(self, options, email_name):
        emails = fs.email(options[consts.OPT_SOURCE], options[consts.OPT_PATTERN], email_name)
        subject, text, html = '', '', ''
        for email in emails:
            template, placeholders = reader.read(email.full_path)
            email_subject, email_text, email_html = renderer.render(email, template, placeholders, options)
            subject = self._append_content(email.locale, subject, email_subject)
            text = self._append_content(email.locale, text, email_text)
            html = self._append_content(email.locale, html, email_html)
        subject = subject + '\n' + self._end_locale_selection
        text = text + '\n' + self._end_locale_selection
        html = html + '\n' + self._end_locale_selection
        email = fs.Email(email.name, '', email.path, email.full_path)
        fs.save(email, subject, text, html, options[consts.OPT_DESTINATION])


_clients = {
    'customerio': CustomIoClient()
}

def client(client_name):
    return _clients['customerio']
