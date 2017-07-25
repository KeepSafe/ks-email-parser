from unittest import TestCase
from unittest.mock import patch
from xml.etree import ElementTree as ET
import os.path

from email_parser import reader
from email_parser.model import *


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestReader(TestCase):
    def setUp(self):
        super().setUp()
        self.email = Email(name='dummy', locale='dummy', path='dummy')
        email_xml = ET.fromstring("""
        <resources template="dummy_template.html" style="dummy_template.css">
            <string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
        </resources>
        """)
        self.globals_xml = ET.fromstring("""
        <resources>
            <string name="content">dummy global</string>
            <string name="order" isText="false">asc</string>
        </resources>
        """)

        self.patch_etree = patch('email_parser.reader.ElementTree')
        self.mock_etree = self.patch_etree.start()
        self.mock_etree.parse.side_effect = iter([ET.ElementTree(email_xml), ET.ElementTree(self.globals_xml)])

        self.patch_fs = patch('email_parser.reader.fs')
        self.mock_fs = self.patch_fs.start()
        self.mock_fs.read_file.return_value = 'test'

    def tearDown(self):
        super().tearDown()
        self.patch_etree.stop()
        self.patch_fs.stop()

    def test_template(self):
        template_str = '<html><head></head><body>{{content}}</body></html>'
        self.mock_fs.read_file.side_effect = iter([template_str, 'test'])
        expected_template = Template('dummy_template.html', ['dummy_template.css'], '<style>test</style>', template_str,
                                     ['content'])
        template, _ = reader.read('.', self.email)
        self.assertEqual(expected_template, template)

    def test_placeholders(self):
        template_str = '<html><head></head><body>{{content}}{{global_content}}</body></html>'
        self.mock_fs.read_file.side_effect = iter([template_str, 'test'])
        expected = {
            'global_content': Placeholder('global_content', 'dummy global', True, True),
            'subject': Placeholder('subject', 'dummy subject'),
            'content': Placeholder('content', 'dummy content')
        }
        _, placeholders = reader.read('.', self.email)
        self.assertEqual(expected, placeholders)

    def test_template_with_multiple_styles(self):
        email_xml = ET.fromstring("""
        <resources template="dummy_template.html" style="dummy_template1.css,dummy_template2.css">
            <string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
        </resources>
        """)
        self.mock_etree.parse.side_effect = iter([ET.ElementTree(email_xml), ET.ElementTree(self.globals_xml)])
        template, _ = reader.read('.', self.email)
        self.assertEqual('<style>test\ntest</style>', template.styles)


class TestWriter(TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_email_content(self):
        expected = read_fixture('email.xml').strip()
        placeholders = [
            Placeholder('subject', 'dummy subject'),
            Placeholder('content', 'dummy content'),
        ]

        result = reader.create_email_content('dummy_template_name.html', ['style1.css'], placeholders)
        self.assertMultiLineEqual(expected, result.strip())
