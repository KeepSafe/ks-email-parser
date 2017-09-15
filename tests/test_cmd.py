import os
import tempfile
import shutil
from unittest import TestCase

from email_parser import fs, cmd, config


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.root_path = tempfile.mkdtemp()
        shutil.copytree(os.path.join('./tests', config.paths.source), os.path.join(cls.root_path, config.paths.source))
        shutil.copytree(
            os.path.join('./tests', config.paths.templates), os.path.join(cls.root_path, config.paths.templates))
        cmd.parse_emails(cls.root_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root_path)

    def _run_and_assert(self, actual_filename, expected_filename=None, locale='en'):
        expected_filename = expected_filename or actual_filename
        expected = read_fixture(expected_filename).strip()
        actual = fs.read_file(TestParser.root_path, config.paths.destination, locale, actual_filename).strip()
        self.assertEqual(expected, actual)

    def test_subject(self):
        self._run_and_assert('email.subject')

    def test_text(self):
        self._run_and_assert('email.text')

    def test_html(self):
        self._run_and_assert('email.html')

    def test_global_text(self):
        self._run_and_assert('email_globale.text')

    def test_global_html(self):
        self._run_and_assert('email_globale.html')

    def test_rtl(self):
        self._run_and_assert('email.html', 'email.rtl.html', 'ar')

    def test_template_fallback(self):
        expected = fs.read_file(TestParser.root_path, config.paths.destination, 'en', 'fallback.html').strip()
        actual = fs.read_file(TestParser.root_path, config.paths.destination, 'fr', 'fallback.html').strip()
        self.assertEqual(expected, actual)
