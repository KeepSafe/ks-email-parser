from unittest import TestCase
from unittest.mock import patch
from email_parser import fs
from email_parser.model import *


class MockPath(object):
    def __init__(self, path, is_dir=False):
        self.path = path
        self._is_dir = is_dir

    def is_dir(self):
        return self._is_dir

    def resolve(self):
        return self.path

    def relative_to(self, base):
        return self.path

    def __str__(self):
        return self.path


class TestFs(TestCase):
    def setUp(self):
        self.patch_path = patch('email_parser.fs.Path')
        self.mock_path = self.patch_path.start()

    def tearDown(self):
        super().tearDown()
        self.patch_path.stop()

    def test_emails_happy_path(self):
        expected = Email('name1', 'locale1', 'src/locale1/name1.xml', 'src/locale1/name1.xml')
        self.mock_path.return_value.glob.return_value = [MockPath(expected.path)]
        actual = list(fs.emails('src/{locale}/{name}.xml'))
        self.assertEqual([expected], actual)

    def test_emails_correct_size(self):
        self.mock_path.return_value.glob.return_value = [
            MockPath('src/locale1/name1.xml'), MockPath('src/locale2/name2.xml')
        ]
        actual = list(fs.emails('src/{locale}/{name}.xml'))
        self.assertEqual(2, len(actual))

    def test_emails_ignore_dirs(self):
        self.mock_path.return_value.glob.return_value = [
            MockPath('src/locale1/name1.xml'), MockPath('src/locale1', True)
        ]
        actual = list(fs.emails('src/{locale}/{name}.xml'))
        self.assertEqual(1, len(actual))

    def test_emails_ignore_global_by_default(self):
        self.mock_path.return_value.glob.return_value = [
            MockPath('src/locale1/name1.xml'), MockPath('src/locale1/global.xml')
        ]
        actual = list(fs.emails('src/{locale}/{name}.xml'))
        self.assertEqual(1, len(actual))

    def test_email_include_global(self):
        self.mock_path.return_value.glob.return_value = [
            MockPath('src/locale1/name1.xml'), MockPath('src/locale1/name2.xml'), MockPath('src/locale2/name2.xml')
        ]
        actual = fs.email('name2', 'locale1', 'src/{locale}/{name}.xml')
        self.assertEqual('name2', actual.name)
        self.assertEqual('locale1', actual.locale)
