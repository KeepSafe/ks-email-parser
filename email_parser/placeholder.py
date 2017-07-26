from collections import Counter
from functools import lru_cache
import re
import json
import logging

from . import reader, fs, const

logger = logging.getLogger(__name__)


def _extract_placeholders(text):
    return Counter(m.group(1) for m in re.finditer(r'\{\{(\w+)\}\}', text))


@lru_cache(maxsize=None)
def expected_placeholders_file(root_path):
    content = fs.read_file(root_path, const.REPO_SRC_PATH, const.PLACEHOLDERS_FILENAME)
    return json.loads(content)


def _email_placeholders(root_path, email):
    _, contents = reader.read(root_path, email)
    content = ''.join(map(lambda c: c.content, contents.values()))
    return _extract_placeholders(content)


def get_email_validation(root_path, email):
    email_placeholders = _email_placeholders(root_path, email)
    expected_placeholders = expected_placeholders_file(root_path).get(email.name, {})
    missing_placeholders = set(expected_placeholders) - set(email_placeholders)
    extra_placeholders = set(email_placeholders) - set(expected_placeholders)
    diff_number = []
    for expected_name, expected_count in expected_placeholders.items():
        email_count = email_placeholders.get(expected_name)
        if email_count and expected_count != email_count:
            diff_number.append({'placeholder': expected_name, 'expected_count': expected_count, 'count': email_count})

    valid = not missing_placeholders and not extra_placeholders and not diff_number
    if not valid:
        errors = {
            'missing': list(missing_placeholders),
            'extra': list(extra_placeholders),
            'diff_number': diff_number
        }
    else:
        errors = None

    return {'valid': valid, 'errors': errors}


def generate_config(root_path):
    emails = fs.emails(root_path, locale=const.DEFAULT_LOCALE)
    placeholders = {email.name: _email_placeholders(root_path, email) for email in emails}
    return placeholders
