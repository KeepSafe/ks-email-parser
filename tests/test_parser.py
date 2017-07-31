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
        expected = '''<?xml version="1.0" encoding="utf-8"?>
<resource style="basic_template.css" template="basic_template.html" xmlns:tools="http://schemas.android.com/tools">
 <string isText="true" name="content">
  dummy content
 </string>
 <string isText="true" name="subject">
  dummy subject
 </string>
</resource>'''
        content = self.parser.create_email_content('basic_template.html', ['basic_template.css'], placeholders)
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

    def test_equality(self):
        parserA = email_parser.Parser('./tests')
        parserB = email_parser.Parser('./tests')
        self.assertEqual(parserA, parserB)
