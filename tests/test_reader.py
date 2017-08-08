from unittest import TestCase
from unittest.mock import patch
from lxml import etree
import os.path

from email_parser import reader
from email_parser.model import *


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestReader(TestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None
        self.email = Email(name='dummy', locale='dummy', path='dummy')
        self.email_content = """
        <resources template="dummy_template.html" style="dummy_template.css">
            <string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
        </resources>
        """
        self.globals_xml = etree.fromstring("""
        <resources>
            <string name="content">dummy global</string>
            <string name="order" isText="false">asc</string>
        </resources>
        """)
        self.template_str = '<html><head></head><body>{{content}}{{global_content}}</body></html>'

        self.patch_parse = patch('email_parser.reader.etree.parse')
        self.mock_parse = self.patch_parse.start()
        self.mock_parse.return_value = etree.ElementTree(self.globals_xml).getroot()

        self.patch_fs = patch('email_parser.reader.fs')
        self.mock_fs = self.patch_fs.start()
        self.mock_fs.read_file.return_value = 'test'

    def tearDown(self):
        super().tearDown()
        self.patch_fs.stop()
        self.patch_parse.stop()

    def test_template(self):
        self.mock_fs.read_file.side_effect = iter([self.email_content, self.template_str, 'test'])
        expected_template = Template('dummy_template.html', ['dummy_template.css'], '<style>test</style>',
                                     self.template_str, ['content', 'global_content'])
        template, _ = reader.read('.', self.email)
        self.assertEqual(expected_template, template)

    def test_placeholders(self):
        self.mock_fs.read_file.side_effect = iter([self.email_content, self.template_str, 'test'])
        expected = {
            'global_content': Placeholder('global_content', 'dummy global', True, True),
            'subject': Placeholder('subject', 'dummy subject'),
            'content': Placeholder('content', 'dummy content')
        }
        _, placeholders = reader.read('.', self.email)
        self.assertEqual(expected, placeholders)

    def test_template_with_multiple_styles(self):
        email_content = """
        <resources template="dummy_template.html" style="dummy_template1.css,dummy_template2.css">
            <string name="subject"><![CDATA[dummy subject]]></string>
            <string name="content"><![CDATA[dummy content]]></string>
        </resources>
        """
        self.mock_fs.read_file.return_value = 'test'
        self.mock_fs.global_email().path = 'test'
        template, _ = reader.read_from_content('.', email_content, 'en')
        self.assertEqual('<style>test\ntest</style>', template.styles)

    def test_read_by_content(self):
        self.mock_fs.read_file.return_value = self.template_str
        template, _ = reader.read_from_content('.', self.email_content, 'en')
        self.assertEqual(template.name, 'dummy_template.html')

    def test_on_missing_content_return_fallback(self):
        self.mock_fs.read_file.return_value = None
        template, _ = reader.read('.', self.email)
        self.assertEqual(self.mock_fs.read_file.call_count, 2)

    def test_on_malformed_content_return_fallback(self):
        malformed_email_content = """
        <resources template="dummy_template.html" style="dummy_template1.css,dummy_template2.css">
            <string name="subject"dummy subject</string>
        </resources>
        """
        self.mock_fs.read_file.side_effect = iter([malformed_email_content,
                                                   self.email_content,
                                                   self.template_str,
                                                   'test'])
        template, _ = reader.read('.', self.email)
        self.assertEqual(self.mock_fs.read_file.call_count, 4)


class TestWriter(TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_email_content(self):
        expected = read_fixture('email.xml').strip()
        placeholders = [
            Placeholder('content', 'dummy content'),
            Placeholder('subject', 'dummy subject'),
        ]

        result = reader.create_email_content('dummy_template_name.html', ['style1.css'], placeholders)
        self.assertMultiLineEqual(expected, result.strip())
