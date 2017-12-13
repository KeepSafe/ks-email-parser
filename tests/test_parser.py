import os
from unittest import TestCase
from unittest.mock import patch

import email_parser
from email_parser import config
from email_parser.model import EmailType


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):
    def setUp(self):
        self.parser = email_parser.Parser('./tests')
        self.maxDiff = None

    def tearDown(self):
        config.init()

    def test_get_template_for_email(self):
        email = self.parser.get_template_for_email('email', 'en')
        self.assertEqual(email, read_fixture('email.raw.html'))

    def test_parse_email(self):
        subject, text, html = self.parser.render('email', 'en')
        self.assertEqual(subject, read_fixture('email.subject').strip())
        self.assertEqual(html, read_fixture('email.html'))
        self.assertEqual(text, read_fixture('email.text').strip())

    def test_parse_email_variant(self):
        subject, text, html = self.parser.render('email', 'en', 'B')
        self.assertEqual(subject, read_fixture('email.b.subject').strip())
        self.assertEqual(html, read_fixture('email.b.html'))
        self.assertEqual(text, read_fixture('email.b.text').strip())

    def test_get_email_names(self):
        names = self.parser.get_email_names()
        self.assertEqual(
            list(names), [
                'email', 'email_globale', 'email_order', 'email_subject_resend', 'email_subjects_ab', 'fallback',
                'missing_placeholder', 'placeholder'
            ])

    def test_get_email_placeholders(self):
        placeholders = self.parser.get_email_placeholders()
        self.assertEqual(len(placeholders.keys()), 8)
        self.assertCountEqual(placeholders['placeholder'], ['unsubscribe_link', 'placeholder'])

    def test_render(self):
        subject, text, html = self.parser.render('placeholder', 'en')
        self.assertEqual(text, 'Dummy content {{placeholder}}\n\nDummy inline')

    def test_create_email(self):
        placeholders = {
            'subject': {
                'content': "dummy subject",
                'is_text': True,
                'is_global': False,
                'type': 'text',
                'is_global': False,
                'variants': {
                    'B': 'better subject'
                }
            },
            'content': {
                'content': "dummy content",
                'type': 'text',
                'is_global': False
            },
            'global_content': {
                'content': "global dummy content",
                'type': 'text',
                'is_global': True
            },
        }
        expected = read_fixture('email.xml').strip()
        content = self.parser.create_email_content('basic_template.html', ['style1.css'], placeholders, 'transactional')
        self.assertMultiLineEqual(content.strip(), expected.strip())

    def test_create_email_without_emailtype(self):
        placeholders = {
            'subject': {
                'content': "dummy subject",
                'is_text': True,
                'is_global': False,
                'type': 'text',
                'is_global': False,
                'variants': {
                    'B': 'better subject'
                }
            },
            'content': {
                'content': "dummy content",
                'type': 'text',
                'is_global': False
            },
            'global_content': {
                'content': "global dummy content",
                'type': 'text',
                'is_global': True
            },
        }
        self.parser.create_email_content('basic_template.html', ['style1.css'], placeholders)

    def test_get_template(self):
        expected = ['subject', 'color', 'content', 'inline', 'image', 'image_absolute']
        _, actual = self.parser.get_template('basic_template.html', 'transactional')
        self.assertEqual(set(actual), set(expected))

    def test_get_template_without_type(self):
        expected = ['subject', 'color', 'content', 'inline', 'image', 'image_absolute']
        _, actual = self.parser.get_template('basic_template.html')
        self.assertEqual(set(actual), set(expected))

    def test_get_resources(self):
        templates_dict = {
            'marketing': {
                'basic_marketing_template.html': ['subject', 'color', 'content', 'inline', 'image', 'image_absolute'],
                'globale_template.html': ['subject', 'color', 'content', 'inline', 'image', 'image_absolute',
                                          'global_unsubscribe']
            },
            'transactional': {
                'basic_template.html': ['subject', 'color', 'content', 'inline', 'image', 'image_absolute'],
            }
        }
        actual_templates, styles, sections = self.parser.get_resources()
        self.assertEqual(actual_templates, templates_dict)
        self.assertIn('header-with-background.html', sections.keys())
        self.assertIn('basic_template.css', styles)

    def test_get_email_filepaths_all_locale(self):
        expected = ['src/ar/email.xml', 'src/en/email.xml', 'src/fr/email.xml']
        actual = self.parser.get_email_filepaths('email')
        self.assertEqual(actual, expected)

    def test_get_email_filepaths_single_locale(self):
        expected = ['src/ar/email.xml']
        actual = self.parser.get_email_filepaths('email', 'ar')
        self.assertEqual(actual, expected)

    def test_equality(self):
        parserA = email_parser.Parser('./tests')
        parserB = email_parser.Parser('./tests')
        self.assertEqual(parserA, parserB)

    def test_get_email_components(self):
        expected = ('basic_template.html', EmailType.transactional.value, ['basic_template.css'],
                    {
            'color': {
                'content': '[[#C0D9D9]]',
                'is_global': False,
                'name': 'color',
                'type': 'attribute',
                'variants': {}
            },
            'content': {
                'content': 'Dummy content',
                'is_global': False,
                'name': 'content',
                'type': 'text',
                'variants': {
                    'B': 'Awesome content'
                }
            },
            'image': {
                'content': '![Alt text](/path/to/img.jpg)',
                'is_global': False,
                'name': 'image',
                'type': 'text',
                'variants': {}
            },
            'image_absolute': {
                'content': '![Alt text](http://path.com/to/{link_locale}/img.jpg)',
                'is_global': False,
                'name': 'image_absolute',
                'type': 'text',
                'variants': {}
            },
            'inline': {
                'content': 'Dummy inline',
                'is_global': False,
                'name': 'inline',
                'type': 'raw',
                'variants': {}
            },
            'subject': {
                'content': 'Dummy subject',
                'is_global': False,
                'name': 'subject',
                'type': 'text',
                'variants': {'B': 'Awesome subject'}
            }
        })
        actual = self.parser.get_email_components('email', 'en')
        self.assertEqual(actual, expected)

    def test_get_email_variants(self):
        actual = self.parser.get_email_variants('email')
        self.assertEqual(actual, ['B'])

    @patch('email_parser.fs.save_file')
    def test_save_email_variant_default_content(self, mock_save):
        expected = read_fixture('email_en_default.xml')
        self.parser.save_email_variant_as_default('email', ['en'], None)
        content, _ = mock_save.call_args[0]
        self.assertMultiLineEqual(content.strip(), expected.strip())

    @patch('email_parser.fs.save_file')
    def test_save_email_variant_b_content(self, mock_save):
        expected = read_fixture('email_en_b.xml')
        self.parser.save_email_variant_as_default('email', ['en'], 'B')
        content, _ = mock_save.call_args[0]
        self.assertMultiLineEqual(content.strip(), expected.strip())

    def test_original(self):
        actual = self.parser.original('email_order', 'en')
        self.assertEqual(actual, read_fixture('original.txt').strip())

    def test_get_emails_resources_paths(self):
        expected = ['templates_html/basic_template.css',
                    'templates_html/transactional/basic_template.html']
        actual = self.parser.get_email_resources_filepaths('email')
        self.assertEqual(set(expected), set(actual))
