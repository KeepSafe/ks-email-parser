import os
import shutil
import subprocess
import sys
import tempfile
from unittest import TestCase

from email_parser import config, fs


def read_fixture(filename):
    with open(os.path.join('tests/fixtures', filename)) as fp:
        return fp.read()


class TestCliSmoke(TestCase):
    maxDiff = None

    def setUp(self):
        self.root_path = tempfile.mkdtemp()
        shutil.copytree(os.path.join('tests', config.paths.source), os.path.join(self.root_path, config.paths.source))
        shutil.copytree(
            os.path.join('tests', config.paths.templates),
            os.path.join(self.root_path, config.paths.templates),
        )

    def tearDown(self):
        shutil.rmtree(self.root_path)

    def test_cli_render_matches_golden_fixtures(self):
        result = subprocess.run(
            [sys.executable, '-m', 'email_parser.cmd'],
            cwd=self.root_path,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual(
            read_fixture('email.subject').strip(),
            fs.read_file(self.root_path, config.paths.destination, 'en', 'email.subject').strip(),
        )
        self.assertEqual(
            read_fixture('email.text').strip(),
            fs.read_file(self.root_path, config.paths.destination, 'en', 'email.text').strip(),
        )
        self.assertEqual(
            read_fixture('email.html'),
            fs.read_file(self.root_path, config.paths.destination, 'en', 'email.html'),
        )

    def test_cli_render_fails_when_no_emails_are_found(self):
        empty_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty_root)

        result = subprocess.run(
            [sys.executable, '-m', 'email_parser.cmd'],
            cwd=empty_root,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(1, result.returncode)
        self.assertFalse(os.path.exists(os.path.join(empty_root, config.paths.destination)))
