import os
import tempfile
import shutil
from unittest import TestCase

import email_parser
from email_parser import fs, cmd


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):

    def setUp(self):
        self.dest = tempfile.mkdtemp()
        settings = cmd.default_settings()._asdict()
        settings['destination'] = self.dest
        settings['source'] = 'tests'
        settings['templates'] = 'tests/templates_html'
        settings['images'] = 'images_base'
        settings['pattern'] = 'src/{locale}/{name}.xml'
        self.settings = cmd.Settings(**settings)

    def tearDown(self):
        shutil.rmtree(self.dest)

    def _run_and_assert(self, actual_filename, expected_filename=None):
        expected_filename = expected_filename or actual_filename
        email_parser.parse_emails(self.settings)
        expected = read_fixture(expected_filename).strip()
        actual = fs.read_file(self.dest, 'en', actual_filename).strip()
        self.assertEqual(expected, actual)

    def test_subject(self):
        self._run_and_assert('email.subject')

    def test_text(self):
        self._run_and_assert('email.text')

    def test_html(self):
        self._run_and_assert('email.html')

    def test_rtl(self):
        settings = self.settings._asdict()
        settings['right_to_left'] = ['en']
        self.settings = cmd.Settings(**settings)
        self._run_and_assert('email.html', 'email.rtl.html')

    def test_placeholder(self):
        email_parser.parse_emails(self.settings)
        fs.read_file(self.dest, 'en', 'placeholder.html')

    def test_missing_placeholder(self):
        email_parser.parse_emails(self.settings)
        with self.assertRaises(FileNotFoundError):
            fs.read_file(self.dest, 'en', 'missing_placeholder.html')

    def test_template_fallback(self):
        email_parser.parse_emails(self.settings)
        expected = fs.read_file(self.dest, 'en', 'fallback.html').strip()
        actual = fs.read_file(self.dest, 'fr', 'fallback.html').strip()
        self.assertEqual(expected, actual)

    def remove_dest_folder_before_parsing(self):
        _, filepath = tempfile.mkstemp(dir=self.dest, text='dummy')
        self.assertTrue(os.path.exists(filepath))
        email_parser.parse_emails(self.settings)
        self.assertFalse(os.path.exists(filepath))
