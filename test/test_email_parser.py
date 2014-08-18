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

    def test_list_available_emails(self):
        emails = email_parser.list_emails(SRC_PATH, 'en')

        expected = ['access_code.xml', 'activate_trial.xml', 'change_email_notice.xml', 'new_device.xml',
                    'password_reset_code.xml', 'signup.xml', 'soft_trial_end.xml', 'trial_end_hard.xml',
                    'upgrade_to_premium.xml', 'verify_email.xml', 'welcome_to_keepsafe.xml']
        self.assertListEqual(expected, emails)
