from unittest import TestCase
from unittest.mock import MagicMock, patch
import json

from email_parser import placeholder, consts, fs


class TestGenerator(TestCase):

    def setUp(self):
        self.options = {
            consts.OPT_SOURCE: 'test_src',
            consts.OPT_PATTERN: 'test_pattern'
        }

    @patch('email_parser.placeholder.fs')
    def test_happy_path(self, mock_fs):
        mock_fs.emails.return_value = [fs.Email('test_name', 'en', 'path', 'full_path')]
        mock_fs.read_file.return_value = '{{placeholder}}'

        placeholder.generate_config(self.options)

        mock_fs.save_file.assert_called_with(
            '{\n    "test_name": [\n        "placeholder"\n    ]\n}', 'test_src', 'placeholders_config.json')

    @patch('email_parser.placeholder.fs')
    def test_no_placeholders(self, mock_fs):
        mock_fs.emails.return_value = [fs.Email('test_name', 'en', 'path', 'full_path')]
        mock_fs.read_file.return_value = 'content'

        placeholder.generate_config(self.options)

        self.assertFalse(mock_fs.save_file.called)

    @patch('email_parser.placeholder.fs')
    def test_no_emails(self, mock_fs):
        mock_fs.emails.return_value = []
        mock_fs.read_file.return_value = '{{placeholder}}'

        placeholder.generate_config(self.options)

        self.assertFalse(mock_fs.save_file.called)

    @patch('email_parser.placeholder.fs')
    def test_extra_placeholders(self, mock_fs):
        mock_fs.emails.return_value = [
            fs.Email('test_name', 'en', 'path', 'full_path'),
            fs.Email('test_name', 'de', 'path', 'full_path')
        ]
        mock_fs.read_file.side_effect = iter(['{{placeholder}}', '{{placeholder}}{{extra_placeholder}}'])

        placeholder.generate_config(self.options)

        self.assertFalse(mock_fs.save_file.called)


class TestValidate(TestCase):

    def setUp(self):
        self.email = fs.Email('test_name', 'en', 'path', 'full_path')
        self.placeholders = json.dumps({'test_name': ['test_placeholder']})
        self.content = '{{test_placeholder}}'
        placeholder._read_placeholders_file.cache_clear()

    @patch('email_parser.placeholder.fs')
    def test_happy_path(self, mock_fs):
        mock_fs.read_file.side_effect = iter([self.placeholders, self.content])

        actual = placeholder.validate_email(self.email)

        self.assertTrue(actual)

    @patch('email_parser.placeholder.fs')
    def test_missing_placeholder(self, mock_fs):
        content = 'content'
        mock_fs.read_file.side_effect = iter([self.placeholders, content])

        actual = placeholder.validate_email(self.email)

        self.assertFalse(actual)

    @patch('email_parser.placeholder.fs')
    def test_extra_placeholder(self, mock_fs):
        placeholders = json.dumps({'test_name': []})
        mock_fs.read_file.side_effect = iter([placeholders, self.content])

        actual = placeholder.validate_email(self.email)

        self.assertFalse(actual)
