import argparse
import logging
import os
import xml.etree.ElementTree as ET
import markdown
import bs4


DEFAULT_DESTINATION = 'target'
DEAFULT_SOURCE = 'src'
EMAIL_EXTENSION = '.xml'
SUBJECT_EXTENSION = '.subject'
TEXT_EXTENSION = '.text'


class Email(object):

    def __init__(self, name, subject, order, content):
        super().__init__()
        self.name = name
        self.subject = subject
        self.order = order
        self.content = content

    def content_to_text(self):
        result = {}
        for content_key, content_value in self.content.items():
            content_html = markdown.markdown(content_value)
            content_text = bs4.BeautifulSoup(content_html).get_text()
            result[content_key] = content_text
        return result

    def content_to_html(self, template):
        pass

    def from_xml(email_dir, email_filename):
        email_path = os.path.join(email_dir, email_filename)
        tree = ET.parse(email_path)
        email = {element.get('name'): element.text for element in tree.findall('./string')}

        if 'subject' not in email:
            logging.error('Template at path %s has no <string name="subject"> element', email_path)

        email_subject = email['subject'] or ''
        email_order = email.get('order', 0)

        # Subject and order are not in markdown so we need to remove them from futher processing
        del email['subject']
        if 'order' in email:
            del email['order']

        email_name, _ = os.path.splitext(email_filename)
        return Email(email_name, email_subject, email_order, email)


def list_locales(path):
    logging.debug('reading locales from %s', path)
    return [locale for locale in os.listdir(path) if os.path.isdir(os.path.join(path, locale))]


def list_emails(path, locale):
    emails_path = os.path.join(path, locale)
    logging.debug('reading emails from %s', emails_path)
    emails = [email for email in os.listdir(emails_path) if os.path.isfile(
        os.path.join(emails_path, email)) and email.endswith(EMAIL_EXTENSION)]
    return [Email.from_xml(emails_path, email) for email in emails]


def save_email_subject(dest_dir, email):
    email_path = os.path.join(dest_dir, email.name + SUBJECT_EXTENSION)
    with open(email_path, 'w') as email_file:
        email_file.write(email.subject)


def save_email_as_text(dest_dir, email):
    email_path = os.path.join(dest_dir, email.name + TEXT_EXTENSION)
    with open(email_path, 'w') as email_file:
        for content_key, content_value in email.content.items():
            email_file.write(content_value)


def parse_emails(src_path, dest_path):
    locales = list_locales(src_path)
    for locale in locales:
        emails = list_emails(src_path, locale)
        for email in emails:
            dest_path_with_locale = os.path.join(dest_path, locale)
            os.makedirs(dest_path_with_locale, exist_ok=True)
            save_email_subject(dest_path_with_locale, email)
            save_email_as_text(dest_path_with_locale, email)


def read_args():
    args_parser = argparse.ArgumentParser()

    args_parser.add_argument('-l', '--loglevel', help='Specify log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)',
                             default='WARNING')
    args_parser.add_argument('-s', '--source_path',
                             help='Templates source folder',
                             default=DEAFULT_SOURCE)
    args_parser.add_argument('-d', '--destination_path',
                             help='Parser destination folder',
                             default=DEFAULT_DESTINATION)

    return args_parser.parse_args()


def init_log(loglevel):
    num_level = getattr(logging, loglevel.upper(), 'WARNING')
    logging.basicConfig(level=num_level)


def main():
    logging.debug('Starting script')
    args = read_args()
    logging.debug('Arguments from console: %s', args)
    init_log(args['loglevel'])

    parse_emails(args['source_path'], args['destination_path'])

if __name__ == '__main__':
    main()
