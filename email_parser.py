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

DEFAULE_LOG_LEVEL = 'WARNING'
DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
DEFAULT_TEMPLATES = 'templates_html'
EMAIL_EXTENSION = '.xml'
SUBJECT_EXTENSION = '.subject'
TEXT_EXTENSION = '.text'
HTML_EXTENSION = '.html'


class Email(object):

    def __init__(self, name, subject, order, template, css, content):
        super().__init__()
        self.name = name
        self.subject = subject
        self.order = order
        self.template = template
        self.css = css
        self.content = content

    def content_to_text(self):
        result = {}
        for content_key, content_value in self.content.items():
            content_html = markdown.markdown(content_value)
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
            content_html = markdown.markdown(content_value)
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
        # pystache escapes html by default, pass escape option to disable this
        renderer = pystache.Renderer(escape=lambda u: u)
        # add subject for rendering as we can have it in html as title tag
        return renderer.render(template, dict(content_html.items() | {'subject': self.subject}.items()))

    def from_xml(email_dir, email_filename):
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
        return Email(email_name, email_subject, elements_order, template_name, css_names, email)


def list_locales(src_dir):
    """
    Gets all directories in a given path. It assumes all directories are locale names.
    """
    logging.debug('reading locales from %s', src_dir)
    return [locale for locale in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, locale))]


def list_emails(src_dir, locale):
    """
    Creates Emails from files in a given directory. It assumes all files ending with an EMAIL_EXTENSION are email
    templates.
    """
    emails_path = os.path.join(src_dir, locale)
    logging.debug('reading emails from %s', emails_path)
    emails = [email for email in os.listdir(emails_path) if os.path.isfile(
        os.path.join(emails_path, email)) and email.endswith(EMAIL_EXTENSION)]
    return [Email.from_xml(emails_path, email) for email in emails]


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
        if email.css:
            css = []
            for style in email.css:
                style_path = os.path.join(templates_dir, style)
                with open(style_path) as style_file:
                    css.append(style_file.read())
        else:
            css = []
        email_html = email.to_html(template, css)
        email_file.write(email_html)


def parse_emails(src_dir, dest_dir, templates_dir):
    locales = list_locales(src_dir)
    logging.debug('Found locales:%s', locales)
    for locale in locales:
        emails = list_emails(src_dir, locale)
        for email in emails:
            dest_path_with_locale = os.path.join(dest_dir, locale)
            os.makedirs(dest_path_with_locale, exist_ok=True)
            save_email_subject(dest_path_with_locale, email)
            save_email_content_as_text(dest_path_with_locale, email)
            save_email_content_as_html(dest_path_with_locale, templates_dir, email)


def read_args():
    args_parser = argparse.ArgumentParser()

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
    return args_parser.parse_args()


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'WARNING')
    logging.basicConfig(level=num_level)


def main():
    print('Parsing emails...')
    logging.debug('Starting script')
    args = read_args()
    init_log(args.loglevel)
    logging.debug('Arguments from console: %s', args)
    parse_emails(args.source, args.destination, args.templates)
    print('Done')

if __name__ == '__main__':
    main()
