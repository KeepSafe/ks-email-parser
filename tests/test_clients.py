import os
import tempfile
import shutil
from unittest import TestCase

from email_parser import consts, fs, clients

def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):
    maxDiff = None

    def setUp(self):
        self.dest = tempfile.mkdtemp()
        self.options = {
            consts.OPT_SOURCE: 'tests',
            consts.OPT_DESTINATION: self.dest,
            consts.OPT_TEMPLATES: 'tests/templates_html',
            consts.OPT_IMAGES: 'images_base',
            consts.OPT_RIGHT_TO_LEFT: ['ar', 'he'],
            consts.OPT_STRICT: False,
            consts.OPT_PATTERN: 'src/{locale}/{name}.xml',
            consts.OPT_EMAIL_NAME: 'email',
            consts.CMD_CLIENT: 'customerio'
        }
        self.client = clients.CustomerIoClient()

    def tearDown(self):
        shutil.rmtree(self.dest)

    def _run_and_assert(self, filename, fixture_filename):
        self.client.parse(self.options)
        expected = read_fixture(fixture_filename).strip()
        actual = fs.read_file(self.dest, filename).strip()
        self.assertEqual(expected, actual)

    def test_subject(self):
        self._run_and_assert('email.subject', 'customerio_email.subject')

    def test_text(self):
        self._run_and_assert('email.text', 'customerio_email.text')

    def test_html(self):
        self._run_and_assert('email.html', 'customerio_email.html')
