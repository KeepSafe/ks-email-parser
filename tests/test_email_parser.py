import os
import tempfile
import shutil
from unittest import TestCase

import email_parser
from email_parser import consts, fs


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):
    def setUp(self):
        self.dest = tempfile.mkdtemp()
        self.options = {
            consts.OPT_SOURCE: 'tests',
            consts.OPT_DESTINATION: self.dest,
            consts.OPT_TEMPLATES: 'tests/templates_html',
            consts.OPT_IMAGES: 'images_base',
            consts.OPT_RIGHT_TO_LEFT: ['ar', 'he'],
            consts.OPT_STRICT: False,
            consts.OPT_PATTERN: 'src/{locale}/{name}.xml'
        }

    def tearDown(self):
        shutil.rmtree(self.dest)

    def _run_and_assert(self, filename):
        email_parser.parse_emails(self.options)
        expected = read_fixture(filename).strip()
        actual = fs.read_file(self.dest, 'en', filename).strip()
        self.assertEqual(expected, actual)

    def test_subject(self):
        self._run_and_assert('email.subject')

    def test_text(self):
        self._run_and_assert('email.text')

    def test_html(self):
        self._run_and_assert('email.html')


class _TestCustomerIOParser(TestCase):

    def setUp(self):
        email_dir = os.path.join(SRC_PATH, 'en')
        self.email = email_parser.Email.from_xml(email_dir, 'dummy_email.xml', 'en', '')

    def test_to_text_single(self):
        parser = email_parser.CustomerIOParser()
        expected = """{% if customer.language == "en" %}
head
strong content
test image
test link
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
            'content': '{% if customer.language == "en" %}\n<h1 style="font-size: 2.5em;line-height: 1.25em;margin: 0;font-weight: 200;color: #ccc;background: none;border: none">head</h1>\n<p><strong>strong</strong> content</p>\n{% endif %}\n',
            'image': '{% if customer.language == "en" %}\n<p>test image</p>\n  \n{% endif %}\n',
            'link': '{% if customer.language == "en" %}\n<p>test link</p>\n  \n{% endif %}\n'
            }

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


# class TestEmail(TestCase):
#
#     def setUp(self):
#         email_dir = os.path.join(SRC_PATH, 'en')
#         self.email = email_parser.Email.from_xml(email_dir, 'dummy_email.xml', 'en', '')
#
#     def test_render_text(self):
#         email_text = self.email.content_to_text()
#
#         self.assertTrue('content' in email_text)
#         self.assertEqual('head\nstrong content', email_text['content'])
#
#     def test_render_html(self):
#         email_html = self.email.content_to_html('')
#
#         self.assertTrue('content' in email_html)
#         self.assertEqual('<h1>head</h1>\n<p><strong>strong</strong> content</p>', email_html['content'])
#
#     def test_render_text_anchor_as_href(self):
#         d = 'dummy'
#         email = email_parser.Email(d, d, d, d, d, {'content': '<a href="http://test.me">test value</a>'}, d, d)
#         content = email.content_to_text()
#
#         self.assertEqual('http://test.me', content['content'])
#
#     def test_render_text_anchor_as_value_if_href_missing(self):
#         d = 'dummy'
#         email = email_parser.Email(d, d, d, d, d, {'content': '<a>test value</a>'}, d, d)
#         content = email.content_to_text()
#
#         self.assertEqual('test value', content['content'])
#
#     def test_render_html_with_css(self):
#         email_html = self.email.content_to_html('h1 {font-size:12px;}')
#
#         self.assertTrue('content' in email_html)
#         expected = '<h1 style="font-size: 12px">head</h1>\n<p><strong>strong</strong> content</p>'
#         self.assertEqual(expected, email_html['content'])
#
#     def test_correct_content_order(self):
#         email = email_parser.Email.from_xml(os.path.join(SRC_PATH, 'en'), 'order_email.xml', 'en', '')
#
#         self.assertEqual(email.order[0][0], 'content1')
#         self.assertEqual(email.order[1][0], 'content2')
#
#     def test_render_html_rtl(self):
#         email_dir = os.path.join(SRC_PATH, 'en')
#         email = email_parser.Email.from_xml(email_dir, 'dummy_email.xml', 'en', 'en')
#
#         email_html = email.content_to_html('')
#
#         self.assertTrue('content' in email_html)
#         self.assertEqual(
#             '<div dir=rtl>\n<h1>head</h1>\n<p><strong>strong</strong> content</p>\n</div>', email_html['content'])
#
#     def test_include_urls_correctly(self):
#         email_dir = os.path.join(SRC_PATH, 'en')
#         email = email_parser.Email.from_xml(email_dir, 'inline_text.xml', 'en', '')
#         email_html = email.content_to_html('')
#
#         self.assertTrue('link' in email_html)
#         self.assertEqual('http://www.google.com', email_html['link'])
#
#     def test_include_urls_with_csscorrectly(self):
#         email_dir = os.path.join(SRC_PATH, 'en')
#         email = email_parser.Email.from_xml(email_dir, 'inline_text.xml', 'en', '')
#         email_html = email.content_to_html('a {}')
#
#         self.assertTrue('link' in email_html)
#         self.assertEqual('http://www.google.com', email_html['link'])
#
#     def test_prefix_images_with_base_url(self):
#         email_dir = os.path.join(SRC_PATH, 'en')
#         email = email_parser.Email.from_xml(email_dir, 'image.xml', 'en', '')
#         email_html = email.content_to_html('', 'base_url')
#
#         self.assertTrue('image' in email_html and 'image_title' in email_html)
#         self.assertEqual('<p><img alt="Alt text" src="base_url/path/to/img.jpg" /></p>', email_html['image'])
#         self.assertEqual('<p><img alt="Alt text" src="base_url/path/to/img.jpg" title="Optional title" /></p>', email_html['image_title'])
#         self.assertEqual('<p><img alt="Alt text" src="http://path.com/to/img.jpg" /></p>', email_html['image_absolute'])
#
#     def test_render_html_with_missing_placeholders(self):
#         with open(os.path.join(TEMPLATES_DIR, 'basic_template.html')) as fp:
#             template = fp.read()
#         email_dir = os.path.join(SRC_PATH, 'en')
#         email = email_parser.Email.from_xml(email_dir, 'inline_text.xml', 'en', '')
#         with self.assertRaises(email_parser.MissingPlaceholderError):
#             email.to_html(template, '', '', 'strict')
