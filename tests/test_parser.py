import os
from unittest import TestCase

import email_parser
from email_parser import config


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):
    def setUp(self):
        self.parser = email_parser.Parser('./tests')

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
                'is_global': False
            },
            'content': {
                'content': "dummy content",
                'is_text': True,
                'is_global': False
            },
            'global_content': {
                'content': "global dummy content",
                'is_text': True,
                'is_global': True
            },
        }

        email_name = 'dummy_email'
        path = os.path.join('tests/src/en', email_name + email_parser.const.SOURCE_EXTENSION)
        self.parser.create_email(email_name, 'en', 'basic_template.html', ['basic_template.css'], placeholders)
        self.assertTrue(os.path.exists(path))
        os.remove(path)
