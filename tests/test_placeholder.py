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
    def test_happy_path(self, mock_fs):
        mock_fs.emails.return_value = [fs.Email('test_name', 'en', 'path', 'full_path')]
        mock_fs.read_file.return_value = '{{placeholder}}'

        placeholder.generate_config(self.settings, None)

        mock_fs.save_file.assert_called_with(
            '{"test_name": {"placeholder": 1}}', 'test_src', 'placeholders_config.json')

    @patch('email_parser.placeholder.fs')
    def test_no_emails(self, mock_fs):
        mock_fs.emails.return_value = []
        mock_fs.read_file.return_value = '{{placeholder}}'

        placeholder.generate_config(self.settings)

        self.assertFalse(mock_fs.save_file.called)

    @patch('email_parser.placeholder.fs')
    def test_use_default_language_to_count_placeholders(self, mock_fs):
        mock_fs.emails.return_value = [
            fs.Email('test_name', 'en', 'path', 'full_path'),
            fs.Email('test_name', 'de', 'path', 'full_path')
        ]
        mock_fs.read_file.side_effect = iter(['{{placeholder}}', '{{placeholder}}{{extra_placeholder}}'])

        placeholder.generate_config(self.settings, None)

        mock_fs.save_file.assert_called_with(
            '{"test_name": {"placeholder": 1}}', 'test_src', 'placeholders_config.json')


class TestValidate(TestCase):

    def setUp(self):
        self.email = fs.Email('test_name', 'en', 'path', 'full_path')
        self.placeholders = json.dumps({'test_name': {'test_placeholder': 1}})
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
        placeholders = json.dumps({'test_name': {}})
        mock_fs.read_file.side_effect = iter([placeholders, self.content])

        actual = placeholder.validate_email(self.email)

        self.assertFalse(actual)

class TestList(TestCase):

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

        result = placeholder.list_from_email('test_name')
        result.sort()

        self.assertEqual(expected, result)

    def test_placeholder_list_for_email_without_them(self):
        expected = []

        result = placeholder.list_from_email('without_placeholders')
        self.assertEqual(expected, result)


    def test_placeholder_list_for_non_existing_email(self):
        expected = None

        result = placeholder.list_from_email('to_be_or_not_to_be')
        self.assertEqual(expected, result)
