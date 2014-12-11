"""
    email_parser
    ~~~~~~~~~~

    Parses emails from a source directory and outputs text and html format.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""

import argparse
import logging
import os
import xml.etree.ElementTree as ET
import markdown
import bs4
import pystache
import inlinestyler.utils as inline_styler
from . import markdown_ext

DEFAULE_LOG_LEVEL = 'WARNING'
DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
DEFAULT_TEMPLATES = 'templates_html'
RTL_CODES = 'ar,he'
EMAIL_EXTENSION = '.xml'
SUBJECT_EXTENSION = '.subject'
TEXT_EXTENSION = '.text'
HTML_EXTENSION = '.html'


class CustomerIOParser(object):

    """
    Generates templates for translactional email client Customer.io
    """

    name = 'customerio'
    _start_locale_selection = '{{% if customer.language == "{}" %}}'
    _next_locale_selection = '{{% elsif customer.language == "{}" %}}'
    _end_locale_selection = '{% endif %}'

    def generate_template(self, source, destination, templates_dir, email_name):
        locales = list_locales(source)
        emails = {}
        for locale in locales:
            email_dir = os.path.join(source, locale)
            email_filename = email_name + EMAIL_EXTENSION
            emails[locale] = Email.from_xml(email_dir, email_filename)
        email_subject = self._to_text(emails, self._subject_to_text)
        email_text = self._to_text(emails, self._content_to_text)
        email_html = self._to_html(emails, templates_dir)
        self._save(destination, email_name + TEXT_EXTENSION, email_text)
        self._save(destination, email_name + HTML_EXTENSION, email_html)
        self._save(destination, email_name + SUBJECT_EXTENSION, email_subject)

    def _save(self, destination, email_filename, email_content):
        filepath = os.path.join(destination, email_filename)
        logging.info('saving data to %s', filepath)
        with open(filepath, 'w') as email_file:
            email_file.write(email_content)

    def _to_text(self, emails, concat_text_fn):
        text = None
        for locale, email in emails.items():
            if text is None:
                text = self._start_locale_selection.format(locale)
            else:
                text = text + '\n' + self._next_locale_selection.format(locale)
            text = concat_text_fn(email, text)
        return text + '\n' + self._end_locale_selection + '\n'

    def _content_to_text(self, email, text):
        contents = email.content_to_text()
        for content_key, _ in email.order:
            text = text + '\n' + contents[content_key]
        return text

    def _subject_to_text(self, email, text):
        return text + '\n' + email.subject

    def _concat_html_content(self, emails, templates_dir):
        content_html = {}
        for locale, email in emails.items():
            css = read_css(email, templates_dir)
            email_content = email.content_to_html(css)
            for content_key, content_value in email_content.items():
                text = content_html.get(content_key)
                if text is None:
                    text = self._start_locale_selection.format(locale)
                else:
                    text = text + '\n' + self._next_locale_selection.format(locale)
                text = text + '\n' + content_value
                content_html[content_key] = text
        for content_key, content_value in content_html.items():
            content_html[content_key] = content_value + '\n' + self._end_locale_selection + '\n'
        return content_html

    def _to_subject(self, emails):
        subject = None
        for locale, email in emails.items():
            if subject is None:
                subject = self._start_locale_selection.format(locale)
            else:
                subject = subject + self._next_locale_selection.format(locale)

            subject = subject + email.subject

        subject = subject + self._end_locale_selection
        return subject

    def _to_html(self, emails, templates_dir):
        content_html = self._concat_html_content(emails, templates_dir)
        email = emails['en']
        template_path = os.path.join(templates_dir, email.template)
        with open(template_path) as template_file:
            template = template_file.read()
        return render_html(template, content_html, email.subject)

parsers = {CustomerIOParser.name: CustomerIOParser()}


class Email(object):

    """
    Represents a single email
    """

    def __init__(self, name, subject, order, template, css, content, locale, rtl_codes):
        super().__init__()
        self.name = name
        self.subject = subject
        self.order = order
        self.template = template
        self.css = css
        self.content = content
        self.locale = locale
        self.rtl_codes = rtl_codes

    def _text_to_html(self, text):
        return markdown.markdown(text, extensions=[markdown_ext.inline_text()])

    def content_to_text(self):
        result = {}
        for content_key, content_value in self.content.items():
            content_html = self._text_to_html(content_value)
            soup = bs4.BeautifulSoup(content_html)

            # replace all <a> with the text links in href as get_text() will take the value inside <a> instead
            anchors = soup.find_all('a')
            for anchor in anchors:
                anchor.replace_with(anchor.get('href', anchor.string))

            result[content_key] = soup.get_text()
        return result

    def content_to_html(self, css):
        result = {}
        for content_key, content_value in self.content.items():
            content_html = self._text_to_html(content_value)
            if self.locale in self.rtl_codes.split(','):
                content_html = wrap_with_text_direction(content_html)
            content_html_with_css = self._inline_css(content_html, css)
            result[content_key] = content_html_with_css
        return result

    def _inline_css(self, html, css):
        if css:
            css_tags = ''.join(['<style>{}</style>'.format(style) for style in css])
            html_with_css = inline_styler.inline_css(css_tags + html)
            body = ET.fromstring(html_with_css).find('.//body')
            return ''.join(ET.tostring(e, encoding='unicode') for e in body)
        else:
            return html

    def to_html(self, template, css):
        content_html = self.content_to_html(css)
        return render_html(template, content_html, self.subject)

    @staticmethod
    def from_xml(email_dir, email_filename, locale, rtl_codes):
        email_path = os.path.join(email_dir, email_filename)
        tree = ET.parse(email_path)
        template_name = tree.getroot().get('template')

        if template_name is None:
            logging.error('no HTML template name define for %s', email_path)

        css_names = tree.getroot().get('style', [])
        if css_names:
            css_names = css_names.split(',')

        elements = list(tree.findall('./string'))
        email = {element.get('name'): element.text for element in elements}
        elements_order = [(element.get('name'), element.get('order', 0)) for element in elements]
        elements_order.sort(key=lambda e: e[1])

        if 'subject' not in email:
            logging.error('Template at path %s has no <string name="subject"> element', email_path)

        email_subject = email['subject'] or ''

        # Subject and order are not markdown so we need to remove them from futher processing
        del email['subject']
        elements_order = list(filter(lambda e: e[0] != 'subject', elements_order))

        email_name, _ = os.path.splitext(email_filename)
        logging.debug('Creating email object for %s from %s', email_name, email_dir)
        return Email(email_name, email_subject, elements_order, template_name, css_names, email, locale, rtl_codes)


def wrap_with_text_direction(html):
    return '<div dir=rtl>\n' + html + '\n</div>'


def render_html(template, htmls, subject):
    # pystache escapes html by default, pass escape option to disable this
    renderer = pystache.Renderer(escape=lambda u: u)
    # add subject for rendering as we have it in html
    return renderer.render(template, dict(htmls.items() | {'subject': subject}.items()))


def list_locales(src_dir):
    logging.debug('reading locales from %s', src_dir)
    return [locale for locale in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, locale))]


def list_emails(src_dir, locale, rtl_codes):
    emails_path = os.path.join(src_dir, locale)
    logging.debug('reading emails from %s', emails_path)
    emails = [email for email in os.listdir(emails_path) if os.path.isfile(
        os.path.join(emails_path, email)) and email.endswith(EMAIL_EXTENSION)]
    return [Email.from_xml(emails_path, email, locale, rtl_codes) for email in emails]


def read_css(email, templates_dir):
    css = []
    if email.css:
        for style in email.css:
            style_path = os.path.join(templates_dir, style)
            with open(style_path) as style_file:
                css.append(style_file.read())
    return css


def save_email_subject(dest_dir, email):
    email_path = os.path.join(dest_dir, email.name + SUBJECT_EXTENSION)
    logging.debug('Saving email subject to %s', email_path)
    with open(email_path, 'w') as email_file:
        email_file.write(email.subject)


def save_email_content_as_text(dest_dir, email):
    email_path = os.path.join(dest_dir, email.name + TEXT_EXTENSION)
    logging.debug('Saving email as text to %s', email_path)
    with open(email_path, 'w') as email_file:
        content_text = email.content_to_text()
        for content_key, _ in email.order:
            email_file.write(content_text[content_key])
            # End with new paragraph start in case we have more to write
            email_file.write('\n\n')


def save_email_content_as_html(dest_dir, templates_dir, email):
    email_path = os.path.join(dest_dir, email.name + HTML_EXTENSION)
    template_path = os.path.join(templates_dir, email.template)
    with open(email_path, 'w') as email_file, open(template_path) as template_file:
        logging.debug('Saving email as html to %s using template %s', email_path, template_path)
        template = template_file.read()
        css = read_css(email, templates_dir)
        email_html = email.to_html(template, css)
        email_file.write(email_html)


def parse_emails(src_dir, dest_dir, templates_dir, rtl_codes):
    locales = list_locales(src_dir)
    logging.debug('Found locales:%s', locales)
    for locale in locales:
        emails = list_emails(src_dir, locale, rtl_codes)
        for email in emails:
            dest_path_with_locale = os.path.join(dest_dir, locale)
            os.makedirs(dest_path_with_locale, exist_ok=True)
            save_email_subject(dest_path_with_locale, email)
            save_email_content_as_text(dest_path_with_locale, email)
            save_email_content_as_html(dest_path_with_locale, templates_dir, email)


def read_args():
    args_parser = argparse.ArgumentParser(epilog='Brought to you by KeepSafe - www.getkeepsafe.com')

    args_parser.add_argument('-l', '--loglevel',
                             help='Specify log level (DEBUG, INFO, WARNING, ERROR, CRITICAL), default: %s'
                             % DEFAULE_LOG_LEVEL,
                             default=DEFAULE_LOG_LEVEL)
    args_parser.add_argument('-s', '--source',
                             help='Parser\'s source folder, default: %s' % DEAFULT_SOURCE,
                             default=DEAFULT_SOURCE)
    args_parser.add_argument('-d', '--destination',
                             help='Parser\'s destination folder, default: %s' % DEFAULT_DESTINATION,
                             default=DEFAULT_DESTINATION)
    args_parser.add_argument('-t', '--templates',
                             help='Templates folder, default: %s' % DEFAULT_TEMPLATES,
                             default=DEFAULT_TEMPLATES)
    args_parser.add_argument('-rtl', '--right-to-left',
                             help='Comma separated list of RTL language codes, default: %s' % RTL_CODES,
                             default=RTL_CODES)

    subparsers = args_parser.add_subparsers(help='Generate 3rd party template', dest='client')

    template_parser = subparsers.add_parser(CustomerIOParser.name)
    template_parser.add_argument('email_name',
                                 help='Name of the email to generate the template for')

    return args_parser.parse_args()


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'WARNING')
    logging.basicConfig(level=num_level)


def main():
    print('Parsing emails...')
    args = read_args()
    init_log(args.loglevel)
    logging.debug('Starting script')
    logging.debug('Arguments from console: %s', args)
    if args.client is None:
        parse_emails(args.source, args.destination, args.templates, args.right_to_left)
    else:
        client = parsers[args.client]
        client.generate_template(args.source, args.destination, args.templates, args.email_name)
    print('Done')

if __name__ == '__main__':
    main()
