from unittest import TestCase
from unittest.mock import patch, MagicMock
from xml.etree import ElementTree
from collections import OrderedDict

from email_parser import reader, fs


class TestReader(TestCase):
    def setUp(self):
        self.email = fs.Email(name='dummy', locale='dummy', path='dummy', full_path='dummy')
        self.email_element = ElementTree.fromstring("""
        <resources template="dummy_template.html" style="dummy_template.css">
            <string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
            <string name="greeting">dummy you</string>
        </resources>
        """)
        self.global_email_element = ElementTree.fromstring("""
        <resources>
            <string name="content">dummy global</string>
            <string name="order" isText="false">asc</string>
        </resources>
        """)
        self.template_str = "<html><head></head><body>{{content}}</body></html>"
        self.settings = MagicMock(pattern='{locale}/{name}.xml', source='src/', templates='temp/')

        self.patch_etree = patch('email_parser.reader.ElementTree')
        self.mock_etree = self.patch_etree.start()
        self.mock_etree.parse.side_effect = iter(
            [ElementTree.ElementTree(self.email_element), ElementTree.ElementTree(self.global_email_element)])

        self.patch_read = patch('email_parser.fs.read_file')
        self.mock_read = self.patch_read.start()
        self.mock_read.side_effect = iter([self.template_str])

        self.patch_isf = patch('email_parser.fs.is_file')
        self.mock_isf = self.patch_isf.start()
        self.mock_isf.side_effect = iter([True])

    def tearDown(self):
        super().tearDown()
        self.patch_etree.stop()
        self.patch_read.stop()
        self.patch_isf.stop()

    def test_template(self):
        expected_template = reader.Template(
            name='dummy_template.html',
            styles=['dummy_template.css'],
            content=self.template_str,
            placeholders=['subject', 'content'])

        template, _, _ = reader.read(self.email, self.settings)

        self.assertEqual(expected_template, template)

    def test_placeholders(self):
        template_str = "<html><head></head><body>{{greeting}}{{content}}</body></html>"

        self.mock_read.side_effect = iter([template_str])

        expected = OrderedDict([('subject', 'dummy subject'), ('greeting', 'dummy you'), ('content', 'dummy content')])

        _, placeholders, _ = reader.read(self.email, self.settings)

        self.assertEqual(expected, placeholders)

    def test_placeholders_with_global(self):
        template_str = "<html><head></head><body>{{global_content}}{{content}}</body></html>"

        self.mock_read.side_effect = iter([template_str])

        expected = OrderedDict([('subject', 'dummy subject'), ('global_content', 'dummy global'),
                                ('content', 'dummy content')])

        _, placeholders, _ = reader.read(self.email, self.settings)

        self.assertEqual(expected, placeholders)

    def test_template_with_multiple_styles(self):
        email_element = ElementTree.fromstring("""
        <resources template="dummy_template.html" style="dummy_template1.css,dummy_template2.css">
            <string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
        </resources>
        """)
        self.mock_etree.parse.side_effect = iter(
            [ElementTree.ElementTree(email_element), ElementTree.ElementTree(self.global_email_element)])

        template, _, _ = reader.read(self.email, self.settings)

        self.assertEqual(['dummy_template1.css', 'dummy_template2.css'], template.styles)

    def test_ignore_non_text_elements(self):
        email_element = ElementTree.fromstring("""
        <resources template="dummy_template.html" style="dummy_template1.css,dummy_template2.css">
            <string name="subject">dummy subject</string>
            <string name="content">dummy content</string>
            <string name="color" isText="false">blue</string>
        </resources>
        """)
        self.mock_etree.parse.side_effect = iter(
            [ElementTree.ElementTree(email_element), ElementTree.ElementTree(self.global_email_element)])

        expected = set(['color', 'global_order'])

        _, _, ignored = reader.read(self.email, self.settings)

        self.assertEqual(expected, set(ignored))
        self.assertEqual(2, len(ignored))

    @patch('email_parser.reader.logger.warn')
    def test_warn_on_extra_placeholders(self, mock_warn):
        self.mock_etree.parse.side = iter(
            [ElementTree.ElementTree(self.email_element), ElementTree.ElementTree(self.global_email_element)])

        reader.read(self.email, self.settings)
        expected_warn = "There are extra placeholders {'greeting'} in email dummy/dummy, \
missing in template dummy_template.html"

        mock_warn.assert_called_with(expected_warn)
