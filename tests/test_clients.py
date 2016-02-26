import os
import tempfile
import shutil
from unittest import TestCase

from email_parser import fs, clients, cmd


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestParser(TestCase):
    maxDiff = None

    def setUp(self):
        self.dest = tempfile.mkdtemp()
        settings = cmd.default_settings()._asdict()
        settings['destination'] = self.dest
        settings['source'] = 'tests'
        settings['templates'] = 'tests/templates_html'
        settings['images'] = 'images_base'
        settings['pattern'] = 'src/{locale}/{name}.xml'
        self.settings = cmd.Settings(**settings)
        self.client = clients.CustomerIoClient()

    def tearDown(self):
        shutil.rmtree(self.dest)

    def _run_and_assert(self, filename, fixture_filename):
        self.client.parse('email', self.settings)
        expected = read_fixture(fixture_filename).strip()
        actual = fs.read_file(self.dest, filename).strip()
        self.assertEqual(expected, actual)

    def test_subject(self):
        self._run_and_assert('email.subject', 'customerio_email.subject')

    def test_text(self):
        self._run_and_assert('email.text', 'customerio_email.text')

    def test_html(self):
        self._run_and_assert('email.html', 'customerio_email.html')
