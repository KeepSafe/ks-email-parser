import json
import os
import shutil
import subprocess
import sys
import tempfile
from unittest import TestCase

from email_parser import config, const, fs


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

    def test_cli_generates_placeholders_config(self):
        root_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root_path)
        source_path = os.path.join(root_path, 'src', 'en')
        template_path = os.path.join(root_path, 'templates_html', 'transactional')
        os.makedirs(source_path)
        os.makedirs(template_path)
        with open(os.path.join(source_path, 'welcome.xml'), 'w') as fp:
            fp.write(
                '<resources template="welcome.html" email_type="transactional">\n'
                '  <string name="subject">Welcome</string>\n'
                '  <string name="content"><![CDATA[Hello {{first_name}} from {{company}}]]></string>\n'
                '</resources>\n'
            )
        with open(os.path.join(source_path, 'global.xml'), 'w') as fp:
            fp.write('<resources></resources>\n')
        with open(os.path.join(template_path, 'welcome.html'), 'w') as fp:
            fp.write('<html><body>{{content}}</body></html>\n')

        result = subprocess.run(
            [sys.executable, '-m', 'email_parser.cmd', 'config', 'placeholders'],
            cwd=root_path,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        with open(os.path.join(root_path, const.REPO_SRC_PATH, const.PLACEHOLDERS_FILENAME)) as fp:
            self.assertEqual({'welcome': {'company': 1, 'first_name': 1}}, json.load(fp))

    def test_cli_rejects_unsupported_config_name(self):
        root_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root_path)
        result = subprocess.run(
            [sys.executable, '-m', 'email_parser.cmd', 'config', 'unsupported'],
            cwd=root_path,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(1, result.returncode)
        config_path = os.path.join(root_path, const.REPO_SRC_PATH, const.PLACEHOLDERS_FILENAME)
        self.assertFalse(os.path.exists(config_path))
