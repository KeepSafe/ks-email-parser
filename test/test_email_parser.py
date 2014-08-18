import email_parser

import os
import tempfile
from unittest import TestCase


SRC_PATH = os.path.join('test', 'src')


class TestParser(TestCase):
    def serUp(self):
        self.test_source_path = ''
        self.test_dest_path

    def test_list_available_locales(self):
        locales = email_parser.list_locales(SRC_PATH)

        self.assertListEqual(['en'], locales)
