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

DEFAULE_LOG_LEVEL = 'WARNING'
DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
DEFAULT_TEMPLATES = 'templates_html'
EMAIL_EXTENSION = '.xml'
SUBJECT_EXTENSION = '.subject'
TEXT_EXTENSION = '.text'
HTML_EXTENSION = '.html'


class Email(object):

    def __init__(self, name, subject, order, template, content):
        super().__init__()
        self.name = name
        self.subject = subject
        self.order = order
        self.template = template
        self.content = content

    def content_to_text(self):
        return {content_key: bs4.BeautifulSoup(content_html).get_text()
                for content_key, content_html in self.content_to_html().items()}

    def content_to_html(self):
        result = {}
        for content_key, content_value in self.content.items():
            content_html = markdown.markdown(content_value)
            result[content_key] = content_html
        return result

    def to_html(self, template):
        content_html = self.content_to_html()
        return pystache.render(template, content_html)

    def from_xml(email_dir, email_filename):
        email_path = os.path.join(email_dir, email_filename)
        tree = ET.parse(email_path)
        template_name = tree.getroot().get('template')
        email = {element.get('name'): element.text for element in tree.findall('./string')}

        if 'subject' not in email:
            logging.error('Template at path %s has no <string name="subject"> element', email_path)

        email_subject = email['subject'] or ''
        email_order = email.get('order', 0)

        # Subject and order are not markdown so we need to remove them from futher processing
        del email['subject']
        if 'order' in email:
            del email['order']

        email_name, _ = os.path.splitext(email_filename)
        logging.debug('Creating email object for %s from %s', email_name, email_dir)
        return Email(email_name, email_subject, email_order, template_name, email)


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
        for content_key, content_value in email.content_to_text().items():
            email_file.write(content_value)


def save_email_content_as_html(dest_dir, templates_dir, email):
    email_path = os.path.join(dest_dir, email.name + HTML_EXTENSION)
    with open(email_path, 'w') as email_file:
        template_path = os.path.join(templates_dir, email.template)
        logging.debug('Saving email as html to %s using template', email_path, template_path)
        with open(template_path, 'r') as template_file:
            template = template_file.read()
        email_html = email.to_html(template)
        email_file.write(email_html)


def parse_emails(src_dir, dest_dir, templates_dir):
    locales = list_locales(src_dir)
    logging.debug('Found locales:%s',  locales)
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
                             help='Specify log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)',
                             default=DEFAULE_LOG_LEVEL)
    args_parser.add_argument('-s', '--source',
                             help='Parser\'s source folder',
                             default=DEAFULT_SOURCE)
    args_parser.add_argument('-d', '--destination',
                             help='Parser\'s destination folder',
                             default=DEFAULT_DESTINATION)
    args_parser.add_argument('-t', '--templates',
                             help='Templates folder',
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
