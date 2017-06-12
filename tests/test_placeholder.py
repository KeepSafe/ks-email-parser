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

    def tearDown(self):
        super().tearDown()
        self.patch_reader.stop()

    def test_happy_path(self):
        actual = placeholder.validate_email('.', self.email, {'test_placeholder': 1})
        self.assertTrue(actual)

    def test_missing_placeholder(self):
        self.mock_reader.read.return_value = ('', {'segment': Placeholder('segment', 'content')})
        actual = placeholder.validate_email('.', self.email, {'test_placeholder': 1})
        self.assertFalse(actual)

    def test_extra_placeholder(self):
        actual = placeholder.validate_email('.', self.email, {})
        self.assertFalse(actual)
