import email_parser

import os
import tempfile
from unittest import TestCase

_ROOT_DIR = os.path.join(os.path.dirname(__file__))
SRC_PATH = os.path.join(_ROOT_DIR, 'src')
TEMPLATES_DIR = os.path.join(_ROOT_DIR, 'templates_html')


class TestParser(TestCase):

    def test_list_available_locales(self):
        locales = email_parser.list_locales(SRC_PATH)

        self.assertListEqual(['en'], locales)

    def test_list_available_emails(self):
        emails = email_parser.list_emails(SRC_PATH, 'en', '')

        self.assertEqual(len(emails), 4)
        email = next(filter(lambda e: e.name == 'dummy_email', emails))
        self.assertEqual('Dummy subject', email.subject)
        self.assertEqual('#head\n\n**strong** content', email.content['content'])

    def test_parse_emails(self):
        with tempfile.TemporaryDirectory() as dest_dir:
            email_parser.parse_emails(SRC_PATH, dest_dir, TEMPLATES_DIR, '', '')
            email_files = os.listdir(os.path.join(dest_dir, 'en'))

        expected = [
            'dummy_email.html',
            'dummy_email.subject',
            'dummy_email.text',
            'image.html',
            'image.subject',
            'image.text',
            'inline_text.html',
            'inline_text.subject',
            'inline_text.text',
            'order_email.html',
            'order_email.subject',
            'order_email.text']
        self.assertListEqual(expected, email_files)


class TestCustomerIOParser(TestCase):

    def setUp(self):
        email_dir = os.path.join(SRC_PATH, 'en')
        self.email = email_parser.Email.from_xml(email_dir, 'dummy_email.xml', 'en', '')

    def test_to_text_single(self):
        parser = email_parser.CustomerIOParser()
        expected = """{% if customer.language == "en" %}
head
strong content
{% endif %}
"""

        actual = parser._to_text({'en': self.email}, parser._content_to_text)

        self.assertEqual(expected, actual)

    def test_to_text_multiple(self):
        parser = email_parser.CustomerIOParser()

        actual = parser._to_text({'en': self.email, 'pl': self.email}, parser._content_to_text)

        self.assertTrue('{% if customer.language == ' in actual)
        self.assertTrue('{% elsif customer.language == ' in actual)
        self.assertTrue('{% endif %}' in actual)

    def test_to_html_single(self):
        parser = email_parser.CustomerIOParser()
        expected = {
            'content': '{% if customer.language == "en" %}\n<h1 style="font-size: 2.5em;line-height: 1.25em;margin: 0;font-weight: 200;color: #ccc;background: none;border: none">head</h1>\n<p><strong>strong</strong> content</p>\n{% endif %}\n'}

        actual = parser._concat_html_content({'en': self.email}, TEMPLATES_DIR)

        self.assertDictEqual(expected, actual)

    def test_to_subject_single(self):
        parser = email_parser.CustomerIOParser()
        expected = """{% if customer.language == "en" %}
Dummy subject
{% endif %}
"""

        actual = parser._to_text({'en': self.email}, parser._subject_to_text)
        self.assertEqual(expected, actual)


class TestEmail(TestCase):

    def setUp(self):
        email_dir = os.path.join(SRC_PATH, 'en')
        self.email = email_parser.Email.from_xml(email_dir, 'dummy_email.xml', 'en', '')

    def test_render_text(self):
        email_text = self.email.content_to_text()

        self.assertTrue('content' in email_text)
        self.assertEqual('head\nstrong content', email_text['content'])

    def test_render_html(self):
        email_html = self.email.content_to_html('')

        self.assertTrue('content' in email_html)
        self.assertEqual('<h1>head</h1>\n<p><strong>strong</strong> content</p>', email_html['content'])

    def test_render_text_anchor_as_href(self):
        d = 'dummy'
        email = email_parser.Email(d, d, d, d, d, {'content': '<a href="http://test.me">test value</a>'}, d, d)
        content = email.content_to_text()

        self.assertEqual('http://test.me', content['content'])

    def test_render_text_anchor_as_value_if_href_missing(self):
        d = 'dummy'
        email = email_parser.Email(d, d, d, d, d, {'content': '<a>test value</a>'}, d, d)
        content = email.content_to_text()

        self.assertEqual('test value', content['content'])

    def test_render_html_with_css(self):
        email_html = self.email.content_to_html('h1 {font-size:12px;}')

        self.assertTrue('content' in email_html)
        expected = '<h1 style="font-size: 12px">head</h1>\n<p><strong>strong</strong> content</p>'
        self.assertEqual(expected, email_html['content'])

    def test_correct_content_order(self):
        email = email_parser.Email.from_xml(os.path.join(SRC_PATH, 'en'), 'order_email.xml', 'en', '')

        self.assertEqual(email.order[0][0], 'content1')
        self.assertEqual(email.order[1][0], 'content2')

    def test_render_html_rtl(self):
        email_dir = os.path.join(SRC_PATH, 'en')
        email = email_parser.Email.from_xml(email_dir, 'dummy_email.xml', 'en', 'en')

        email_html = email.content_to_html('')

        self.assertTrue('content' in email_html)
        self.assertEqual(
            '<div dir=rtl>\n<h1>head</h1>\n<p><strong>strong</strong> content</p>\n</div>', email_html['content'])

    def test_include_urls_correctly(self):
        email_dir = os.path.join(SRC_PATH, 'en')
        email = email_parser.Email.from_xml(email_dir, 'inline_text.xml', 'en', '')
        email_html = email.content_to_html('')

        self.assertTrue('link' in email_html)
        self.assertEqual('http://www.google.com', email_html['link'])

    def test_prefix_images_with_base_url(self):
        email_dir = os.path.join(SRC_PATH, 'en')
        email = email_parser.Email.from_xml(email_dir, 'image.xml', 'en', '')
        email_html = email.content_to_html('', 'base_url')

        self.assertTrue('image' in email_html and 'image_title' in email_html)
        self.assertEqual('<p><img alt="Alt text" src="base_url/path/to/img.jpg" /></p>', email_html['image'])
        self.assertEqual('<p><img alt="Alt text" src="base_url/path/to/img.jpg" title="Optional title" /></p>', email_html['image_title'])
