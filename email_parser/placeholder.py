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


def _validate_placeholders(email, email_placeholders, expected_placeholders):
    result = True
    missing_placeholders = set(expected_placeholders) - set(email_placeholders)
    if missing_placeholders:
        logger.error('There are missing placeholders %s in email %s, locale %s' %
                     (missing_placeholders, email.name, email.locale))
        result = False
    extra_placeholders = set(email_placeholders) - set(expected_placeholders)
    if extra_placeholders:
        logger.error('There are extra placeholders %s in email %s, locale %s' %
                     (extra_placeholders, email.name, email.locale))
        result = False

    for expected_name, expected_count in expected_placeholders.items():
        email_count = email_placeholders.get(expected_name, 0)
        if expected_count != email_count:
            logger.error('The number of placeholders "%s" in email "%s" locale "%s" should be %s but was %s' %
                         (expected_name, email.name, email.locale, expected_count, email_count))
            result = False
    return result


def validate_email(root_path, email, expected_placeholders):
    try:
        email_placeholders = _email_placeholders(root_path, email)
        logger.debug('validating placeholders for email %s locale %s', email.name, email.locale)
        return _validate_placeholders(email, email_placeholders, expected_placeholders)
    except FileNotFoundError:
        # If the file does not exist skip validation
        return True


def validate_template(template, email):
    template_placeholders = set(_extract_placeholders(template))
    email_placeholders = set(_email_placeholders(email))
    extra_placeholders = email_placeholders - template_placeholders
    if extra_placeholders:
        logger.warn('There are extra placeholders %s in email %s/%s, not used in template' %
                    (extra_placeholders, email.locale, email.name))
        return False
    return True


def generate_config(root_path):
    emails = fs.emails(root_path, locale=const.DEFAULT_LOCALE)
    placeholders = {email.name: _email_placeholders(root_path, email) for email in emails}
    return placeholders
