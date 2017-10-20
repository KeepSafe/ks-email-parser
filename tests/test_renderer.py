from unittest import TestCase
from unittest.mock import patch

from email_parser.model import *
from email_parser import renderer, const, config


class TestTextRenderer(TestCase):
    def setUp(self):
        self.email_locale = 'locale'
        self.template = Template('dummy', [], '<style>body {}</style>', '<body>{{content1}}</body>',
                                 ['content', 'content1', 'content2'])
        self.r = renderer.TextRenderer(self.template, self.email_locale)

    def test_happy_path(self):
        placeholders = {'content': Placeholder('content', 'dummy content', 0)}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_render_variant(self):
        placeholders = {'content': Placeholder('content', 'dummy content', 1, variants={'B': 'awesome content'})}
        actual = self.r.render(placeholders, variant='B')
        self.assertEqual('awesome content', actual)

    def test_concat_multiple_placeholders(self):
        placeholders = {
            'content1': Placeholder('content', 'dummy content', 2),
            'content2': Placeholder('content2', 'dummy content', 3)
        }
        expected = const.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(['dummy content', 'dummy content'])
        actual = self.r.render(placeholders)
        self.assertEqual(expected, actual)

    def test_concat_multiple_placeholders_with_variants(self):
        placeholders = {
            'content1': Placeholder('content', 'dummy content', 2),
            'content2': Placeholder('content2', 'dummy content', 3, variants={'B': 'awesome content'})
        }
        expected = const.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(['dummy content', 'awesome content'])
        actual = self.r.render(placeholders, variant='B')
        self.assertEqual(expected, actual)

    def test_ignore_subject(self):
        placeholders = {
            'content': Placeholder('content', 'dummy content', 1),
            'subject': Placeholder('subject', 'dummy subject', -1)
        }
        actual = self.r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_ignore_empty_placeholders(self):
        placeholders = {'content': Placeholder('content', 'dummy content', 1), 'empty': Placeholder('empty', '', 99)}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_ignored_placeholders(self):
        placeholders = {
            'content': Placeholder('content', 'dummy content', 1),
            'ignore': Placeholder('ignore', 'test', 99, False)
        }
        r = renderer.TextRenderer(self.template, self.email_locale)
        actual = r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_use_text_and_url_for_links(self):
        placeholders = {'content': Placeholder('content', 'dummy [link_text](http://link_url) content', 1)}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy link_text (http://link_url) content', actual)

    def test_default_link_locale_for_links(self):
        placeholders = {
            'content': Placeholder('content', 'dummy [link_text](http://link_url?locale={link_locale}) content', 1)
        }
        actual = self.r.render(placeholders)
        self.assertEqual('dummy link_text (http://link_url?locale=locale) content', actual)

    def test_link_locale_for_links(self):
        self.email_locale = 'pt-BR'
        placeholders = {
            'content': Placeholder('content', 'dummy [link_text](http://link_url?locale={link_locale}) content', 1)
        }
        r = renderer.TextRenderer(self.template, self.email_locale)
        actual = r.render(placeholders)
        self.assertEqual('dummy link_text (http://link_url?locale=pt) content', actual)

    def test_use_text_if_href_is_empty(self):
        placeholders = {'content': Placeholder('content', 'dummy [http://link_url]() content', 1)}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy http://link_url content', actual)

    def test_use_href_if_text_is_same(self):
        placeholders = {'content': Placeholder('content', 'dummy [http://link_url](http://link_url) content', 1)}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy http://link_url content', actual)

    def test_url_with_params(self):
        placeholders = {
            'content': Placeholder('content', 'dummy [param_link](https://something.com/thing?id=mooo) content', 1)
        }
        actual = self.r.render(placeholders)
        self.assertEqual('dummy param_link (https://something.com/thing?id=mooo) content', actual)

    def test_unordered_list(self):
        placeholders = {'content': Placeholder('content', '- one\n- two\n- three', 1)}
        actual = self.r.render(placeholders)
        self.assertEqual('- one\n- two\n- three', actual.strip())

    def test_ordered_list(self):
        placeholders = {'content': Placeholder('content', '1. one\n2. two\n3. three', 1)}
        actual = self.r.render(placeholders)
        self.assertEqual('1. one\n2. two\n3. three', actual.strip())


class TestSubjectRenderer(TestCase):
    def setUp(self):
        self.r = renderer.SubjectRenderer()
        self.placeholders = {
            'content': Placeholder('content', 'dummy content', 0),
            'subject': Placeholder('subject', 'dummy subject', -1, variants={'B': 'experiment subject'})
        }

    def test_happy_path(self):
        actual = self.r.render(self.placeholders)
        self.assertEqual('dummy subject', actual)

    def test_variant(self):
        actual = self.r.render(self.placeholders, variant='B')
        self.assertEqual('experiment subject', actual)

    def test_raise_error_for_missing_subject(self):
        placeholders = {'content': 'dummy content'}
        with self.assertRaises(MissingSubjectError):
            self.r.render(placeholders)


class TestHtmlRenderer(TestCase):
    def _get_renderer(self, template_html, template_placeholders, **kwargs):
        template = Template(
            name='template_name',
            styles_names=['template_style.css', 'template_style2.css'],
            styles='',
            content=template_html,
            placeholders=template_placeholders)
        return renderer.HtmlRenderer(template, kwargs.get('email_locale', const.DEFAULT_LOCALE))

    def setUp(self):
        self.email_locale = 'locale'
        config.init(_base_img_path='images_base')

    def tearDown(self):
        config.init()

    def test_happy_path(self):
        placeholders = {'content1': Placeholder('content1', 'text1', 1)}
        template = Template('dummy', [], '<style>body {}</style>', '<body>{{content1}}</body>', ['content1'])
        r = renderer.HtmlRenderer(template, self.email_locale)

        actual = r.render(placeholders)
        self.assertEqual('<body><p>text1</p></body>', actual)

    def test_variant(self):
        placeholders = {'content1': Placeholder('content1', 'text1', 1, variants={'B': 'text2'})}
        template = Template('dummy', [], '<style>body {}</style>', '<body>{{content1}}</body>', ['content1'])
        r = renderer.HtmlRenderer(template, self.email_locale)

        actual = r.render(placeholders, variant='B')
        self.assertEqual('<body><p>text2</p></body>', actual)

    def test_empty_style(self):
        placeholders = {'content': Placeholder('content', 'dummy_content', 1)}
        template = Template('dummy', [], '', '<body>{{content}}</body>', ['content1'])
        r = renderer.HtmlRenderer(template, self.email_locale)

        actual = r.render(placeholders)
        self.assertEqual('<body><p>dummy_content</p></body>', actual)

    def test_include_base_url(self):
        template = Template('dummy', [], '<style>body {}</style>', '<body>{{base_url}}</body>', ['base_url'])
        placeholders = {}
        r = renderer.HtmlRenderer(template, self.email_locale)

        actual = r.render(placeholders)
        self.assertEqual('<body>images_base</body>', actual)

    def test_fail_on_missing_placeholders(self):
        template = Template('dummy', [], '<style>body {}</style>', '<body>{{content}}{{missing}}</body>',
                            ['content', 'missing'])
        r = renderer.HtmlRenderer(template, self.email_locale)
        placeholders = {'content': Placeholder('content', 'dummy_content', 1)}

        with self.assertRaises(MissingTemplatePlaceholderError):
            r.render(placeholders)

    def test_rtl_locale(self):
        email_locale = 'ar'
        template = Template('dummy', [], '<style>body {}</style>', '<body>{{content}}</body>', ['content'])
        r = renderer.HtmlRenderer(template, email_locale)
        placeholders = {'content': Placeholder('content', 'dummy_content', 1)}

        actual = r.render(placeholders)
        self.assertEqual('<body dir="rtl">\n <p>\n  dummy_content\n </p>\n</body>', actual)

    def test_rtl_two_placeholders(self):
        email_locale = 'ar'
        template = Template('dummy', [], '<style>body {}</style>',
                            '<body><div>{{content1}}</div><div>{{content2}}</div></body>', ['content1', 'content2'])
        r = renderer.HtmlRenderer(template, email_locale)
        placeholders = {
            'content1': Placeholder('content1', 'dummy_content1', 2),
            'content2': Placeholder('content2', 'dummy_content2', 3)
        }

        actual = r.render(placeholders)
        expected = '<body dir="rtl">\n <div>\n  <p>\n   dummy_content1\n  </p>\n </div>\n <div>\n  <p>\n   dummy_content2\n  </p>\n </div>\
\n</body>'

        self.assertEqual(expected, actual)

    def test_inline_styles(self):
        template = Template('dummy', [], '<style>p {color:red;}</style>', '<body>{{content}}</body>', ['content'])
        r = renderer.HtmlRenderer(template, self.email_locale)
        placeholders = {'content': Placeholder('content', 'dummy_content', 1)}

        actual = r.render(placeholders)
        self.assertEqual('<body><p style="color: red">dummy_content</p></body>', actual)

    @patch('email_parser.fs.read_file')
    def test_no_tracking(self, mock_read):
        html = '<body>{{content}}</body>'
        html_placeholders = ['content']
        placeholders = {'content': Placeholder('content', '[link_title](!http://link.com)', True, False)}
        mock_read.side_effect = iter([''])
        expected = """<body><p>
      <a clicktracking="off" href="http://link.com">link_title</a>
    </p></body>"""

        r = self._get_renderer(html, html_placeholders)
        actual = r.render(placeholders)

        self.assertEqual(expected, actual)

    def test_empty_placeholders_rendering(self):
        template = Template('dummy', [], '<style>p {color:red;}</style>', '<body>{{content}}</body>', ['content'])
        r = renderer.HtmlRenderer(template, self.email_locale)
        placeholders = {'content': Placeholder('content', '', 1)}

        actual = r.render(placeholders)
        self.assertEqual('<body></body>', actual)
