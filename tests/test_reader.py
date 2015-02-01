from unittest import TestCase
from unittest.mock import patch, MagicMock
from xml.etree import ElementTree
from collections import OrderedDict

from email_parser import reader


class TestReader(TestCase):
    def setUp(self):
        self.email_element = ElementTree.fromstring("""
        <resources template="dummy_template.html" style="dummy_template.css">
        	<string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
        </resources>
        """)

    @patch('email_parser.reader.ElementTree')
    def test_read_template(self, mock_tree):
        mock_tree.parse.return_value = ElementTree.ElementTree(self.email_element)

        template, _ = reader.read('dummy_path')

        self.assertEqual('dummy_template.html', template.name)
        self.assertEqual(['dummy_template.css'], template.styles)

    @patch('email_parser.reader.ElementTree')
    def test_read_placeholders(self, mock_tree):
        mock_tree.parse.return_value = ElementTree.ElementTree(self.email_element)
        expected = OrderedDict([('subject', 'dummy subject'), ('content', 'dummy content')])

        _, placeholders = reader.read('dummy_path')

        self.assertEqual(expected, placeholders)

    @patch('email_parser.reader.ElementTree')
    def test_read_template_multiple_styles(self, mock_tree):
        email_element = ElementTree.fromstring("""
        <resources template="dummy_template.html" style="dummy_template1.css,dummy_template2.css">
        	<string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
        </resources>
        """)
        mock_tree.parse.return_value = ElementTree.ElementTree(email_element)

        template, _ = reader.read('dummy_path')

        self.assertEqual(['dummy_template1.css', 'dummy_template2.css'], template.styles)
