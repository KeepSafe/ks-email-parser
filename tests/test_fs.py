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
    @patch('email_parser.fs.Path')
    def test_emails_happy_path(self, mock_path):
        expected = fs.Email('name1', 'locale1', 'src/locale1/name1.xml', 'src/locale1/name1.xml')
        mock_path.return_value.glob.return_value = [MockPath(expected.path)]

        actual = list(fs.emails('dummy_path', 'src/{locale}/{name}.xml'))

        self.assertEqual([expected], actual)

    @patch('email_parser.fs.Path')
    def test_emails_correct_size(self, mock_path):
        mock_path.return_value.glob.return_value = [
            MockPath('src/locale1/name1.xml'), MockPath('src/locale2/name2.xml')
        ]

        actual = list(fs.emails('dummy_path', 'src/{locale}/{name}.xml'))

        self.assertEqual(2, len(actual))

    @patch('email_parser.fs.Path')
    def test_emails_fail_on_missing_locale(self, mock_path):
        mock_path.return_value.glob.return_value = [MockPath('src/name1.xml')]

        with self.assertRaises(MissingPatternParamError):
            list(fs.emails('dummy_path', 'src/{name}.xml'))

    @patch('email_parser.fs.Path')
    def test_emails_fail_on_missing_name(self, mock_path):
        mock_path.return_value.glob.return_value = [MockPath('src/locale1.xml')]

        with self.assertRaises(MissingPatternParamError):
            list(fs.emails('dummy_path', 'src/{locale}.xml'))

    @patch('email_parser.fs.Path')
    def test_emails_ignore_dirs(self, mock_path):
        mock_path.return_value.glob.return_value = [MockPath('src/locale1/name1.xml'), MockPath('src/locale1', True)]

        actual = list(fs.emails('dummy_path', 'src/{locale}/{name}.xml'))

        self.assertEqual(1, len(actual))

    @patch('email_parser.fs.Path')
    def test_emails_ignore_global_by_default(self, mock_path):
        mock_path.return_value.glob.return_value = [
            MockPath('src/locale1/name1.xml'), MockPath('src/locale1/global.xml')
        ]

        actual = list(fs.emails('dummy_path', 'src/{locale}/{name}.xml'))
        self.assertEqual(1, len(actual))

    @patch('email_parser.fs.Path')
    def test_email_include_global(self, mock_path):
        mock_path.return_value.glob.return_value = [
            MockPath('src/locale1/name1.xml'), MockPath('src/locale1/global.xml'), MockPath('src/locale2/global.xml')
        ]

        actual = list(fs.email('dummy_path', 'src/{locale}/{name}.xml', 'global', 'locale1', True))
        self.assertEqual(1, len(actual))
        self.assertEqual('global', actual[0].name)
        self.assertEqual('locale1', actual[0].locale)
