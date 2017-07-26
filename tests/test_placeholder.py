from unittest import TestCase
from unittest.mock import patch
from collections import Counter

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
        config = placeholder.generate_config('.')
        self.assertEqual(config, {'test_name': Counter({'placeholder': 1})})

    def test_no_emails(self):
        self.mock_fs.emails.return_value = iter([])
        config = placeholder.generate_config('.')
        self.assertEqual(config, {})


class TestValidate(TestCase):
    def setUp(self):
        self.email = fs.Email('test_name', 'en', 'path')
        placeholder.expected_placeholders_file.cache_clear()

        self.patch_reader = patch('email_parser.placeholder.reader')
        self.mock_reader = self.patch_reader.start()
        self.mock_reader.read.return_value = ('', {'segment': Placeholder('segment', '{{test_placeholder}}')})

        self.patch_config = patch('email_parser.placeholder.expected_placeholders_file')
        self.mock_config = self.patch_config.start()
        self.mock_config.return_value = {self.email.name: {'test_placeholder': 1}}

    def tearDown(self):
        super().tearDown()
        self.patch_reader.stop()

    def test_happy_path(self):
        actual = placeholder.get_email_validation('.', self.email, )
        expected = {'valid': True, 'errors': None}
        self.assertEqual(expected, actual)

    def test_missing_placeholder(self):
        self.mock_reader.read.return_value = ('', {'segment': Placeholder('segment', 'content')})
        actual = placeholder.get_email_validation('.', self.email)
        expected = {'valid': False, 'errors': {'missing': ['test_placeholder'], 'extra': [], 'diff_number': []}}
        self.assertEqual(expected, actual)

    def test_extra_placeholder(self):
        self.mock_config.return_value = {self.email.name: {}}
        actual = placeholder.get_email_validation('.', self.email)
        expected = {'valid': False, 'errors': {'missing': [], 'extra': ['test_placeholder'], 'diff_number': []}}
        self.assertEqual(expected, actual)

    def test_diffrent_placeholder_count(self):
        self.mock_reader.read.return_value = ('', {'segment': Placeholder('segment',
                                                                          '{{test_placeholder}}{{test_placeholder}}')})
        actual = placeholder.get_email_validation('.', self.email)
        expected = {
            'valid': False,
            'errors': {
                'missing': [],
                'extra': [],
                'diff_number': [{'placeholder': 'test_placeholder', 'count': 2, 'expected_count': 1}]
            }
        }
        self.assertEqual(expected, actual)
