from unittest import TestCase
from unittest.mock import patch

from email_parser import renderer, errors, cmd
from email_parser.reader import Template
from email_parser.fs import Email


class TestTextRenderer(TestCase):

    def setUp(self):
        self.renderer = renderer.TextRenderer([])

    def test_happy_path(self):
        placeholders = {'content': 'dummy content'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy content', actual)

    def test_concat_multiple_placeholders(self):
        placeholders = {'content1': 'dummy content', 'content2': 'dummy content'}
        expected = renderer.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(placeholders.values())

        actual = self.renderer.render(placeholders)

        self.assertEqual(expected, actual)

    def test_ignore_subject(self):
        placeholders = {'content': 'dummy content', 'subject': 'dummy subject'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy content', actual)

    def test_ignore_empty_placeholders(self):
        placeholders = {'content': 'dummy content', 'empty': ''}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy content', actual)

    def test_ignored_placeholders(self):
        placeholders = {'content': 'dummy content', 'ignore': 'test'}

        r = renderer.TextRenderer(['ignore'])

        actual = r.render(placeholders)

        self.assertEqual('dummy content', actual)

    def test_use_text_and_url_for_links(self):
        placeholders = {'content': 'dummy [link_text](http://link_url) content'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy link_text (http://link_url) content', actual)

    def test_use_text_if_href_is_empty(self):
        placeholders = {'content': 'dummy [http://link_url]() content'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy http://link_url content', actual)

    def test_use_href_if_text_is_same(self):
        placeholders = {'content': 'dummy [http://link_url](http://link_url) content'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy http://link_url content', actual)

    def test_url_with_params(self):
        placeholders = {'content': 'dummy [param_link](https://something.com/thing?id=mooo) content'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy param_link (https://something.com/thing?id=mooo) content', actual)

    def test_unordered_list(self):
        placeholders = {'content': '- one\n- two\n- three'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('- one\n- two\n- three', actual.strip())

    def test_ordered_list(self):
        placeholders = {'content': '1. one\n2. two\n3. three'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('1. one\n2. two\n3. three', actual.strip())


class TestSubjectRenderer(TestCase):
    def setUp(self):
        self.renderer = renderer.SubjectRenderer()

    def test_happy_path(self):
        placeholders = {'content': 'dummy content', 'subject': 'dummy subject'}

        actual = self.renderer.render(placeholders)

        self.assertEqual('dummy subject', actual[0])

    def test_ab(self):
        placeholders = {'content': 'dummy content', 'subject': 'dummy subject',
                        'subject_b': 'bbb', 'subject_a': 'aaa'}

        actual = self.renderer.render(placeholders)

        self.assertEqual(['dummy subject', 'aaa', 'bbb'], actual)

    def test_raise_error_for_missing_subject(self):
        placeholders = {'content': 'dummy content'}

        with self.assertRaises(errors.MissingSubjectError):
            self.renderer.render(placeholders)


class TestHtmlRenderer(TestCase):

    def _get_renderer(self, template_html, template_placeholders, **kwargs):
        template = Template(name='template_name',
                            styles=['template_style'],
                            content=template_html,
                            placeholders_order=template_placeholders)
        return renderer.HtmlRenderer(template,
                                     kwargs.get('settings', self.settings),
                                     kwargs.get('email', self.email))

    def setUp(self):
        settings = cmd.default_settings()._asdict()
        settings['templates'] = 'dummy_templates'
        settings['images'] = 'dummy_images'
        self.settings = cmd.Settings(**settings)

        self.email = Email('name', 'locale', 'path', 'full_path')
        self.global_email = '<?xml version="1.0" encoding="UTF-8" ?><resources></resources>'

    @patch('email_parser.fs.read_file')
    def test_happy_path(self, mock_read):
        html = '<body>{{content1}}</body>'
        html_placeholders = ['content1']
        placeholders = {'content1': 'text1'}
        mock_read.side_effect = iter(['body {}'])

        renderer = self._get_renderer(html, html_placeholders)
        actual = renderer.render(placeholders)

        self.assertEqual('<body><p>text1</p></body>', actual)

    @patch('email_parser.fs.read_file')
    def test_empty_style(self, mock_read):
        html = '<body>{{content}}</body>'
        html_placeholders = ['content']
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([''])

        renderer = self._get_renderer(html, html_placeholders)
        actual = renderer.render(placeholders)

        self.assertEqual('<body><p>dummy_content</p></body>', actual)

    @patch('email_parser.fs.read_file')
    def test_include_raw_subject(self, mock_read):
        html = '<body>{{subject}}</body>'
        html_placeholders = ['subject']
        placeholders = {'subject': 'dummy_subject'}
        mock_read.side_effect = iter([''])

        renderer = self._get_renderer(html, html_placeholders)
        actual = renderer.render(placeholders)

        self.assertEqual('<body>dummy_subject</body>', actual)

    @patch('email_parser.fs.read_file')
    def test_include_base_url(self, mock_read):
        html = '<body>{{base_url}}</body>'
        html_placeholders = ['base_url']
        placeholders = {}
        mock_read.side_effect = iter([''])

        renderer = self._get_renderer(html, html_placeholders)
        actual = renderer.render(placeholders)

        self.assertEqual('<body>dummy_images</body>', actual)

    @patch('email_parser.fs.read_file')
    def test_ignore_missing_placeholders(self, mock_read):
        html = '<body>{{content}}{{missing}}</body>'
        html_placeholders = ['content', 'missing']
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([''])
        settings = self.settings._asdict()
        settings['strict'] = False
        settings = cmd.Settings(**settings)

        renderer = self._get_renderer(html, html_placeholders, settings=settings)
        actual = renderer.render(placeholders)

        self.assertEqual('<body><p>dummy_content</p></body>', actual)

    @patch('email_parser.fs.read_file')
    def test_fail_on_missing_placeholders(self, mock_read):
        html = '<body>{{content}}{{missing}}</body>'
        html_placeholders = ['content', 'missing']
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([''])

        renderer = self._get_renderer(html, html_placeholders)
        with self.assertRaises(errors.MissingTemplatePlaceholderError):
            renderer.render(placeholders)

    @patch('email_parser.fs.read_file')
    def test_rtl_locale(self, mock_read):
        html = '<body>{{content}}</body>'
        html_placeholders = ['content']
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter([''])
        email_dict = self.email._asdict()
        email_dict['locale'] = 'ar'

        renderer = self._get_renderer(html, html_placeholders, email=Email(**email_dict))
        actual = renderer.render(placeholders)

        self.assertEqual('<body dir="rtl">\n <p>\n  dummy_content\n </p>\n</body>', actual)

    @patch('email_parser.fs.read_file')
    def test_rtl_two_placeholders(self, mock_read):
        html = '<body><div>{{content1}}</div><div>{{content2}}</div></body>'
        html_placeholders = ['content1', 'content2']
        placeholders = {'content1': 'dummy_content1', 'content2': 'dummy_content2'}
        mock_read.side_effect = iter([''])
        email_dict = self.email._asdict()
        email_dict['locale'] = 'ar'

        renderer = self._get_renderer(html, html_placeholders, email=Email(**email_dict))
        actual = renderer.render(placeholders)
        expected = '<body dir="rtl">\n <div>\n  <p>\n   dummy_content1\n  </p>\n </div>\n <div>\n  <p>\n   dummy_content2\n  </p>\n </div>\
\n</body>'
        self.assertEqual(expected, actual)

    @patch('email_parser.fs.read_file')
    def test_inline_styles(self, mock_read):
        html = '<body>{{content}}</body>'
        html_placeholders = ['content']
        placeholders = {'content': 'dummy_content'}
        mock_read.side_effect = iter(['p {color:red;}'])

        renderer = self._get_renderer(html, html_placeholders)
        actual = renderer.render(placeholders)

        self.assertEqual('<body><p style="color: red">dummy_content</p></body>', actual)
