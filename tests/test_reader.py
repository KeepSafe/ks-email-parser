from unittest import TestCase
from unittest.mock import patch
from xml.etree import ElementTree as ET

from email_parser import reader
from email_parser.model import *


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
        self.template_str = "<html><head></head><body>{{content}}</body></html>"

        self.patch_etree = patch('email_parser.reader.ElementTree')
        self.mock_etree = self.patch_etree.start()
        self.mock_etree.parse.side_effect = iter([ET.ElementTree(email_xml), ET.ElementTree(self.globals_xml)])

        self.patch_fs = patch('email_parser.reader.fs')
        self.mock_fs = self.patch_fs.start()
        self.mock_fs.template.return_value = self.template_str
        self.mock_fs.style.return_value = 'test'

    def tearDown(self):
        super().tearDown()
        self.patch_etree.stop()
        self.patch_fs.stop()

    def test_template(self):
        expected_template = Template('dummy_template.html', '<style>test</style>', self.template_str, ['content'])
        template, _ = reader.read(self.email)
        self.assertEqual(expected_template, template)

    def test_placeholders(self):
        expected = {
            'global_content': Placeholder('global_content', 'dummy global'),
            'global_order': Placeholder('global_order', 'asc', False),
            'subject': Placeholder('subject', 'dummy subject'),
            'content': Placeholder('content', 'dummy content')
        }
        _, placeholders = reader.read(self.email)
        self.assertEqual(expected, placeholders)

    def test_template_with_multiple_styles(self):
        email_xml = ET.fromstring("""
        <resources template="dummy_template.html" style="dummy_template1.css,dummy_template2.css">
            <string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
        </resources>
        """)
        self.mock_etree.parse.side_effect = iter([ET.ElementTree(email_xml), ET.ElementTree(self.globals_xml)])
        template, _ = reader.read(self.email)
        self.assertEqual('<style>test\ntest</style>', template.styles)
