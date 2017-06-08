from unittest import TestCase
from unittest.mock import patch
import json

from email_parser import placeholder, fs
from email_parser.model import *


class TestGenerator(TestCase):
    def setUp(self):
        super().setUp()

        self.patch_fs = patch('email_parser.placeholder.fs')
        self.mock_fs = self.patch_fs.start()
        self.mock_fs.read_file.return_value = 'test'

        self.patch_reader = patch('email_parser.placeholder.reader')
        self.mock_reader = self.patch_reader.start()

    def tearDown(self):
        super().tearDown()
        self.patch_fs.stop()
        self.patch_reader.stop()

    def test_happy_path(self):
        self.mock_fs.emails.return_value = iter([Email('test_name', 'en', 'path')])
        self.mock_reader.read.return_value = ('', {'segment': Placeholder('segment', '{{placeholder}}')})
        placeholder.generate_config(None)
        self.mock_fs.save_file.assert_called_with('{"test_name": {"placeholder": 1}}', 'placeholders_config.json')

    def test_no_emails(self):
        self.mock_fs.emails.return_value = iter([])
        placeholder.generate_config()
        self.assertFalse(self.mock_fs.save_file.called)


class TestValidate(TestCase):
    def setUp(self):
        self.email = fs.Email('test_name', 'en', 'path')
        placeholder._expected_placeholders_file.cache_clear()

        self.patch_fs = patch('email_parser.placeholder.fs')
        self.mock_fs = self.patch_fs.start()
        self.mock_fs.read_file.side_effect = iter([json.dumps({'test_name': {'test_placeholder': 1}})])

        self.patch_reader = patch('email_parser.placeholder.reader')
        self.mock_reader = self.patch_reader.start()
        self.mock_reader.read.return_value = ('', {'segment': Placeholder('segment', '{{test_placeholder}}')})

    def tearDown(self):
        super().tearDown()
        self.patch_fs.stop()
        self.patch_reader.stop()

    def test_happy_path(self):
        actual = placeholder.validate_email(self.email)
        self.assertTrue(actual)

    def test_missing_placeholder(self):
        self.mock_reader.read.return_value = ('', {'segment': Placeholder('segment', 'content')})
        actual = placeholder.validate_email(self.email)
        self.assertFalse(actual)

    def test_extra_placeholder(self):
        placeholders = json.dumps({'test_name': {}})
        self.mock_fs.read_file.side_effect = iter([placeholders])
        actual = placeholder.validate_email(self.email)
        self.assertFalse(actual)


class TestFromEmailName(TestCase):
    def setUp(self):
        self.patch_fs = patch('email_parser.placeholder.fs')
        self.mock_fs = self.patch_fs.start()
        self.mock_fs.read_file.return_value = json.dumps({
            'test_name': {
                'test_placeholder': 1,
                'another': 1
            },
            'without_placeholders': {}
        })

    def tearDown(self):
        super().tearDown()
        self.patch_fs.stop()

    def test_placeholder_list_for_given_email_name(self):
        expected = ['another', 'test_placeholder']
        result = placeholder.for_email('test_name')
        result.sort()
        self.assertEqual(expected, result)

    def test_placeholder_list_for_email_without_them(self):
        expected = []
        result = placeholder.for_email('without_placeholders')
        self.assertEqual(expected, result)

    def test_placeholder_list_for_non_existing_email(self):
        expected = []
        result = placeholder.for_email('to_be_or_not_to_be')
        self.assertEqual(expected, result)
