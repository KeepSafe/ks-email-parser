from unittest import TestCase
from unittest.mock import MagicMock, patch
import json

from email_parser import placeholder, fs, cmd


class TestGenerator(TestCase):

    def setUp(self):
        settings = cmd.default_settings()._asdict()
        settings['source'] = 'test_src'
        settings['pattern'] = 'test_pattern'
        self.settings = cmd.Settings(**settings)

    @patch('email_parser.placeholder.fs')
    @patch('email_parser.placeholder.reader')
    def test_happy_path(self, mock_reader, mock_fs):
        mock_fs.emails.return_value = [fs.Email('test_name', 'en', 'path', 'full_path')]
        mock_reader.read.return_value = ('', {'segment': '{{placeholder}}'}, '')

        placeholder.generate_config(self.settings, None)

        mock_fs.save_file.assert_called_with(
            '{"test_name": {"placeholder": 1}}', 'test_src', 'placeholders_config.json')

    @patch('email_parser.placeholder.fs')
    @patch('email_parser.placeholder.reader')
    def test_no_emails(self, mock_reader, mock_fs):
        mock_fs.emails.return_value = []
        mock_reader.read.return_value = ('', {'segment': '{{placeholder}}'}, '')

        placeholder.generate_config(self.settings)

        self.assertFalse(mock_fs.save_file.called)

    @patch('email_parser.placeholder.fs')
    @patch('email_parser.placeholder.reader')
    def test_use_default_language_to_count_placeholders(self, mock_reader, mock_fs):
        mock_fs.emails.return_value = [
            fs.Email('test_name', 'en', 'path', 'full_path'),
            fs.Email('test_name', 'de', 'path', 'full_path')
        ]
        mock_reader.read.side_effect = iter([('', {'segment': '{{placeholder}}'}, ''),
                                             ('', {'segment:' '{{placeholder}}{{extra_placeholder}}'}, '')])

        placeholder.generate_config(self.settings, None)

        mock_fs.save_file.assert_called_with(
            '{"test_name": {"placeholder": 1}}', 'test_src', 'placeholders_config.json')


class TestValidate(TestCase):

    def setUp(self):
        self.settings = cmd.default_settings()
        self.email = fs.Email('test_name', 'en', 'path', 'full_path')
        self.placeholders = json.dumps({'test_name': {'test_placeholder': 1}})
        self.content = '{{test_placeholder}}'
        placeholder._read_placeholders_file.cache_clear()

    @patch('email_parser.placeholder.fs')
    @patch('email_parser.placeholder.reader')
    def test_happy_path(self, mock_reader, mock_fs):
        mock_fs.read_file.side_effect = iter([self.placeholders])
        mock_reader.read.return_value = ('', {'segment': self.content}, '')

        actual = placeholder.validate_email(self.settings, self.email)

        self.assertTrue(actual)

    @patch('email_parser.placeholder.fs')
    @patch('email_parser.placeholder.reader')
    def test_missing_placeholder(self, mock_reader, mock_fs):
        content = 'content'
        mock_fs.read_file.side_effect = iter([self.placeholders])
        mock_reader.read.return_value = ('', {'segment': content}, '')

        actual = placeholder.validate_email(self.settings, self.email)

        self.assertFalse(actual)

    @patch('email_parser.placeholder.fs')
    @patch('email_parser.placeholder.reader')
    def test_extra_placeholder(self, mock_reader, mock_fs):
        placeholders = json.dumps({'test_name': {}})
        mock_fs.read_file.side_effect = iter([placeholders])
        mock_reader.read.return_value = ('', {'segment': self.content}, '')

        actual = placeholder.validate_email(self.settings, self.email)

        self.assertFalse(actual)


class TestFromEmailName(TestCase):

    def setUp(self):
        self.placeholders = json.dumps({'test_name': {
            'test_placeholder': 1,
            'another': 1
        },
            'without_placeholders': {}
        })
        placeholder.fs.read_file = MagicMock(return_value=self.placeholders)

    def test_placeholder_list_for_given_email_name(self):
        expected = ['another', 'test_placeholder']

        result = placeholder.from_email_name('test_name')
        result.sort()

        self.assertEqual(expected, result)

    def test_placeholder_list_for_email_without_them(self):
        expected = []

        result = placeholder.from_email_name('without_placeholders')
        self.assertEqual(expected, result)

    def test_placeholder_list_for_non_existing_email(self):
        expected = []

        result = placeholder.from_email_name('to_be_or_not_to_be')
        self.assertEqual(expected, result)
