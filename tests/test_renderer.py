from unittest import TestCase
from unittest.mock import patch, MagicMock

from email_parser import renderer, consts, errors
from email_parser.reader import Template


class TestTextRenderer(TestCase):

    def setUp(self):
        self.renderer = renderer.TextRenderer()

    def test_render_happy_path(self):
        placeholders = {'content': 'dummy content'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy content', actual)

    def test_render_concat_multiple_placeholders(self):
        placeholders = {'content1': 'dummy content', 'content2': 'dummy content'}
        expected = consts.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(placeholders.values())

        actual = self.renderer.render(placeholders)

        self.assertEqual(expected, actual)

    def test_render_ignore_subject(self):
        placeholders = {'content': 'dummy content', 'subject': 'dummy subject'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy content', actual)


class TestSubjectRenderer(TestCase):
    def setUp(self):
        self.renderer = renderer.SubjectRenderer()

    def test_render_happy_path(self):
        placeholders = {'content': 'dummy content', 'subject': 'dummy subject'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy subject', actual)

    def test_raise_error_for_missing_subject(self):
        placeholders = {'content': 'dummy content'}

        with self.assertRaises(errors.MissingSubjectError):
            self.renderer.render(placeholders)


class TestHtmlRenderer(TestCase):
    def setUp(self):
        self.options = {
            consts.OPT_TEMPLATES: 'dummy_templates',
            consts.OPT_IMAGES: 'dummy_images',
            consts.OPT_RIGHT_TO_LEFT: ['ar', 'he'],
            consts.OPT_STRICT: False
        }
        self.template = Template('template_name', ['template_style'])
        self.renderer = renderer.HtmlRenderer(self.template, self.options, 'locale')

    @patch('email_parser.fs.read_file')
    def test_happy_path(self, mock_read):
        html = '<body>{{content1}}</body>'
        placeholders = {'content1':'text1'}
        mock_read.side_effect = iter([html, 'body {}'])

        actual = self.renderer.render(placeholders)

        self.assertEqual('<body><p>text1</p></body>', actual)

    @patch('email_parser.fs.read_file')
    def test_empty_style(self, mock_read):
        html = '<body>{{content}}</body>'
        placeholders = {'content':'dummy_content'}
        mock_read.side_effect = iter([html, ''])

        actual = self.renderer.render(placeholders)

        self.assertEqual('<body><p>dummy_content</p></body>', actual)

    @patch('email_parser.fs.read_file')
    def test_include_raw_subject(self, mock_read):
        html = '<body>{{subject}}</body>'
        placeholders = {'subject':'dummy_subject'}
        mock_read.side_effect = iter([html, ''])

        actual = self.renderer.render(placeholders)

        self.assertEqual('<body>dummy_subject</body>', actual)

    @patch('email_parser.fs.read_file')
    def test_include_base_url(self, mock_read):
        html = '<body>{{base_url}}</body>'
        placeholders = {}
        mock_read.side_effect = iter([html, ''])

        actual = self.renderer.render(placeholders)

        self.assertEqual('<body>dummy_images</body>', actual)

    @patch('email_parser.fs.read_file')
    def test_ignore_missing_placeholders(self, mock_read):
        html = '<body>{{content}}{{missing}}</body>'
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([html, ''])

        actual = self.renderer.render(placeholders)

        self.assertEqual('<body><p>dummy_content</p></body>', actual)


    @patch('email_parser.fs.read_file')
    def test_fail_on_missing_placeholders(self, mock_read):
        html = '<body>{{content}}{{missing}}</body>'
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([html, ''])
        self.options[consts.OPT_STRICT] = True
        r = renderer.HtmlRenderer(self.template, self.options, 'locale')

        with self.assertRaises(errors.MissingTemplatePlaceholderError):
            r.render(placeholders)

    @patch('email_parser.fs.read_file')
    def test_rtl_locale(self, mock_read):
        html = '<body>{{content}}</body>'
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([html, ''])
        r = renderer.HtmlRenderer(self.template, self.options, 'ar')

        actual = r.render(placeholders)

        self.assertEqual('<body><div dir="rtl">\n      <p>dummy_content</p>\n    </div></body>', actual)

    @patch('email_parser.fs.read_file')
    def test_inline_styles(self, mock_read):
        html = '<body>{{content}}</body>'
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([html, 'p {color:red;}'])

        actual = self.renderer.render(placeholders)

        self.assertEqual('<body><p style="color: red">dummy_content</p></body>', actual)
