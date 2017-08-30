import os
from unittest import TestCase
from collections import OrderedDict

import email_parser
from email_parser import config


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
        subjects, text, html = self.parser.render('email', 'en')
        self.assertEqual(subjects[0], read_fixture('email.subject').strip())
        self.assertEqual(html, read_fixture('email.html'))
        self.assertEqual(text, read_fixture('email.text').strip())

    def test_get_email_names(self):
        names = self.parser.get_email_names()
        self.assertEqual(
            list(names), [
                'email', 'email_globale', 'email_subject_resend', 'email_subjects_ab', 'fallback',
                'missing_placeholder', 'placeholder'
            ])

    def test_get_email_placeholders(self):
        placeholders = self.parser.get_email_placeholders()
        self.assertEqual(len(placeholders.keys()), 8)
        self.assertCountEqual(placeholders['placeholder'], ['unsubscribe_link', 'placeholder'])

    def test_render(self):
        subjects, text, html = self.parser.render('placeholder', 'en')
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
        content = self.parser.create_email_content('dummy_template_name.html', ['style1.css'], placeholders)
        self.assertMultiLineEqual(content.strip(), expected.strip())

    def test_get_template_placeholders(self):
        expected = ['subject', 'color', 'content', 'inline', 'image', 'image_absolute']
        actual = self.parser.get_template_placeholders('basic_template.html')
        self.assertEqual(set(actual), set(expected))

    def test_get_resources(self):
        templates_dict = {
            'basic_template.html': ['subject', 'color', 'content', 'inline', 'image', 'image_absolute'],
            'globale_template.html': ['subject', 'color', 'content', 'inline', 'image', 'image_absolute',
                                      'global_unsubscribe']}
        expected = templates_dict, ['basic_template.css']
        actual = self.parser.get_resources()
        self.assertEqual(actual, expected)

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
        expected = ('basic_template.html', ['basic_template.css'],
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
                'variants': {}
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
            'test': {
                'content': 'control',
                'is_global': False,
                'name': 'test',
                'type': 'text',
                'variants': {
                    'B': 'experiment'
                }
            },
            'subject': {
                'content': 'Dummy subject',
                'is_global': False,
                'name': 'subject',
                'type': 'text',
                'variants': {}
            }
        })
        actual = self.parser.get_email_components('email', 'en')
        self.assertEqual(actual, expected)
