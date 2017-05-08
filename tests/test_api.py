import os
from unittest import TestCase

from email_parser import api


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestAPI(TestCase):
    def setUp(self):
        self.settings = {
            'source': 'tests',
            'templates': 'tests/templates_html',
            'images': 'images_base',
            'pattern': 'src/{locale}/{name}.xml'
        }

    def test_get_email(self):
        email = api.get_email(self.settings, 'en', 'email')
        self.assertEqual(email, read_fixture('email.raw.html'))

    def test_parse_email(self):
        subjects, text, html = api.parse_email(self.settings, 'en', 'email')
        self.assertEqual(subjects[0], read_fixture('email.subject').strip())
        self.assertEqual(html, read_fixture('email.html'))
        self.assertEqual(text, read_fixture('email.text').strip())

    def test_get_email_names(self):
        names = api.get_email_names(self.settings)
        self.assertEqual(
            list(names), [
                'email', 'email_globale', 'email_subject_resend', 'email_subjects_ab', 'fallback',
                'missing_placeholder', 'placeholder', 'email', 'fallback', 'missing_placeholder', 'placeholder'
            ])

    def test_get_email_placeholders(self):
        placeholders = api.get_email_placeholders(self.settings)
        self.assertEqual(len(placeholders.keys()), 7)
        self.assertEqual(placeholders['placeholder'], ['placeholder'])
