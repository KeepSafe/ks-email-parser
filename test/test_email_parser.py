import email_parser

import os
import tempfile
from unittest import TestCase


SRC_PATH = os.path.join('test', 'src')
TEMPLATES_PATH = os.path.join('test', 'templates_html')


class TestParser(TestCase):

    def test_list_available_locales(self):
        locales = email_parser.list_locales(SRC_PATH)

        self.assertListEqual(['en'], locales)

    def test_list_available_emails(self):
        emails = email_parser.list_emails(SRC_PATH, 'en')

        self.assertEqual(len(emails), 1)
        email = emails[0]
        self.assertEqual('Dummy subject', email.subject)
        self.assertEqual('**strong** content', email.content['content'])

    def test_parse_emails(self):
        with tempfile.TemporaryDirectory() as dest_dir:
            email_parser.parse_emails(SRC_PATH, dest_dir)
            email_files = os.listdir(os.path.join(dest_dir, 'en'))

        self.assertListEqual(['dummy_email.subject', 'dummy_email.text'], email_files)


class TestEmail(TestCase):

    def setUp(self):
        email_dir = os.path.join(SRC_PATH, 'en')
        self.email = email_parser.Email.from_xml(email_dir, 'dummy_email.xml')
        self.template_path = os.path.join(SRC_PATH, 'en', 'basic_template.html')

    def test_render_text(self):
        email_text = self.email.content_to_text()

        self.assertTrue('content' in email_text)
        self.assertEqual('strong content', email_text['content'])
