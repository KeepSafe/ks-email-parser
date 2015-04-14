import os
import tempfile
import shutil
from unittest import TestCase

import email_parser
from email_parser import consts, fs


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):
    def setUp(self):
        self.dest = tempfile.mkdtemp()
        self.options = {
            consts.OPT_SOURCE: 'tests',
            consts.OPT_DESTINATION: self.dest,
            consts.OPT_TEMPLATES: 'tests/templates_html',
            consts.OPT_IMAGES: 'images_base',
            consts.OPT_RIGHT_TO_LEFT: ['ar', 'he'],
            consts.OPT_STRICT: False,
            consts.OPT_PATTERN: 'src/{locale}/{name}.xml'
        }

    def tearDown(self):
        shutil.rmtree(self.dest)

    def _run_and_assert(self, actual_filename, expected_filename=None):
        expected_filename = expected_filename or actual_filename
        email_parser.parse_emails(self.options)
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
        self.options[consts.OPT_RIGHT_TO_LEFT] = ['en']
        self._run_and_assert('email.html', 'email.rtl.html')
