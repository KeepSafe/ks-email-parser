from unittest import TestCase

from email_parser.model import *
from email_parser import renderer, const, config


class TestTextRenderer(TestCase):
    def setUp(self):
        self.email = Email('name', 'locale', 'path')
        self.template = Template('dummy', '<style>body {}</style>', '<body>{{content1}}</body>',
                                 ['content', 'content1', 'content2'])
        self.r = renderer.TextRenderer(self.template, self.email)

    def test_happy_path(self):
        placeholders = {'content': Placeholder('content', 'dummy content')}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_concat_multiple_placeholders(self):
        placeholders = {
            'content1': Placeholder('content', 'dummy content'),
            'content2': Placeholder('content2', 'dummy content')
        }
        expected = const.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(map(lambda p: p.content, placeholders.values()))
        actual = self.r.render(placeholders)
        self.assertEqual(expected, actual)

    def test_ignore_subject(self):
        placeholders = {
            'content': Placeholder('content', 'dummy content'),
            'subject': Placeholder('subject', 'dummy subject')
        }
        actual = self.r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_ignore_empty_placeholders(self):
        placeholders = {'content': Placeholder('content', 'dummy content'), 'empty': Placeholder('empty', '')}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_ignored_placeholders(self):
        placeholders = {
            'content': Placeholder('content', 'dummy content'),
            'ignore': Placeholder('ignore', 'test', False)
        }
        r = renderer.TextRenderer(self.template, self.email)
        actual = r.render(placeholders)
        self.assertEqual('dummy content', actual)

    def test_use_text_and_url_for_links(self):
        placeholders = {'content': Placeholder('content', 'dummy [link_text](http://link_url) content')}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy link_text (http://link_url) content', actual)

    def test_default_link_locale_for_links(self):
        placeholders = {
            'content': Placeholder('content', 'dummy [link_text](http://link_url?locale={link_locale}) content')
        }
        actual = self.r.render(placeholders)
        self.assertEqual('dummy link_text (http://link_url?locale=locale) content', actual)

    def test_link_locale_for_links(self):
        self.email = Email('name', 'pt-BR', 'path')
        placeholders = {
            'content': Placeholder('content', 'dummy [link_text](http://link_url?locale={link_locale}) content')
        }
        r = renderer.TextRenderer(self.template, self.email)
        actual = r.render(placeholders)
        self.assertEqual('dummy link_text (http://link_url?locale=pt) content', actual)

    def test_use_text_if_href_is_empty(self):
        placeholders = {'content': Placeholder('content', 'dummy [http://link_url]() content')}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy http://link_url content', actual)

    def test_use_href_if_text_is_same(self):
        placeholders = {'content': Placeholder('content', 'dummy [http://link_url](http://link_url) content')}
        actual = self.r.render(placeholders)
        self.assertEqual('dummy http://link_url content', actual)

    def test_url_with_params(self):
        placeholders = {
            'content': Placeholder('content', 'dummy [param_link](https://something.com/thing?id=mooo) content')
        }
        actual = self.r.render(placeholders)
        self.assertEqual('dummy param_link (https://something.com/thing?id=mooo) content', actual)

    def test_unordered_list(self):
        placeholders = {'content': Placeholder('content', '- one\n- two\n- three')}
        actual = self.r.render(placeholders)
        self.assertEqual('- one\n- two\n- three', actual.strip())

    def test_ordered_list(self):
        placeholders = {'content': Placeholder('content', '1. one\n2. two\n3. three')}
        actual = self.r.render(placeholders)
        self.assertEqual('1. one\n2. two\n3. three', actual.strip())


class TestSubjectRenderer(TestCase):
    def setUp(self):
        self.r = renderer.SubjectRenderer()

    def test_happy_path(self):
        placeholders = {
            'content': Placeholder('content', 'dummy content'),
            'subject': Placeholder('subject', 'dummy subject')
        }
        actual = self.r.render(placeholders)
        self.assertEqual('dummy subject', actual[0])

    def test_ab(self):
        placeholders = {
            'content': Placeholder('content', 'dummy content'),
            'subject': Placeholder('subject', 'dummy subject'),
            'subject_b': Placeholder('subject_b', 'bbb'),
            'subject_a': Placeholder('subject_a', 'aaa')
        }
        actual = self.r.render(placeholders)
        self.assertEqual(['dummy subject', 'aaa', 'bbb', None], actual)

    def test_raise_error_for_missing_subject(self):
        placeholders = {'content': 'dummy content'}
        with self.assertRaises(MissingSubjectError):
            self.r.render(placeholders)


class TestHtmlRenderer(TestCase):
    def setUp(self):
        self.email = Email('name', 'locale', 'path')
        config.init(_base_img_path='images_base')

    def tearDown(self):
        config.init()

    def test_happy_path(self):
        placeholders = {'content1': Placeholder('content1', 'text1')}
        template = Template('dummy', '<style>body {}</style>', '<body>{{content1}}</body>', ['content1'])
        r = renderer.HtmlRenderer(template, self.email)

        actual = r.render(placeholders)
        self.assertEqual('<body><p>text1</p></body>', actual)

    def test_empty_style(self):
        placeholders = {'content': Placeholder('content', 'dummy_content')}
        template = Template('dummy', '', '<body>{{content}}</body>', ['content1'])
        r = renderer.HtmlRenderer(template, self.email)

        actual = r.render(placeholders)
        self.assertEqual('<body><p>dummy_content</p></body>', actual)

    def test_include_base_url(self):
        template = Template('dummy', '<style>body {}</style>', '<body>{{base_url}}</body>', ['base_url'])
        placeholders = {}
        r = renderer.HtmlRenderer(template, self.email)

        actual = r.render(placeholders)
        self.assertEqual('<body>images_base</body>', actual)

    def test_fail_on_missing_placeholders(self):
        template = Template('dummy', '<style>body {}</style>', '<body>{{content}}{{missing}}</body>',
                            ['content', 'missing'])
        r = renderer.HtmlRenderer(template, self.email)
        placeholders = {'content': Placeholder('content', 'dummy_content')}

        with self.assertRaises(MissingTemplatePlaceholderError):
            r.render(placeholders)

    def test_rtl_locale(self):
        email = Email('name', 'ar', 'path')
        template = Template('dummy', '<style>body {}</style>', '<body>{{content}}</body>', ['content'])
        r = renderer.HtmlRenderer(template, email)
        placeholders = {'content': Placeholder('content', 'dummy_content')}

        actual = r.render(placeholders)
        self.assertEqual('<body dir="rtl">\n <p>\n  dummy_content\n </p>\n</body>', actual)

    def test_rtl_two_placeholders(self):
        email = Email('name', 'ar', 'path')
        template = Template('dummy', '<style>body {}</style>',
                            '<body><div>{{content1}}</div><div>{{content2}}</div></body>', ['content1', 'content2'])
        r = renderer.HtmlRenderer(template, email)
        placeholders = {
            'content1': Placeholder('content1', 'dummy_content1'),
            'content2': Placeholder('content2', 'dummy_content2')
        }

        actual = r.render(placeholders)
        expected = '<body dir="rtl">\n <div>\n  <p>\n   dummy_content1\n  </p>\n </div>\n <div>\n  <p>\n   dummy_content2\n  </p>\n </div>\
\n</body>'

        self.assertEqual(expected, actual)

    def test_inline_styles(self):
        template = Template('dummy', '<style>p {color:red;}</style>', '<body>{{content}}</body>', ['content'])
        r = renderer.HtmlRenderer(template, self.email)
        placeholders = {'content': Placeholder('content', 'dummy_content')}

        actual = r.render(placeholders)
        self.assertEqual('<body><p style="color: red">dummy_content</p></body>', actual)
