from collections import defaultdict, Counter
from functools import reduce, lru_cache
import json
import re
import logging

from . import fs

PLACEHOLDERS_FILENAME = 'placeholders_config.json'

logger = logging.getLogger()


@lru_cache(maxsize=None)
def _read_placeholders_file(src_dir):
    content = fs.read_file(src_dir, PLACEHOLDERS_FILENAME)
    return json.loads(content)


def _save_placeholders_file(placeholders, src_dir, indent=4):
    fs.save_file(json.dumps(placeholders, sort_keys=True, indent=indent), src_dir, PLACEHOLDERS_FILENAME)


def _read_email_placeholders(email_name, src_dir):
    return _read_placeholders_file(src_dir).get(email_name, {})

def _parse_email_placeholders(email_path):
    content = fs.read_file(email_path)
    return _parse_string_placeholders(content)

def _parse_string_placeholders(content):
    return Counter(m.group(1) for m in re.finditer(r'\{\{(\w+)\}\}', content))

def _validate_email_placeholders(email_name, email_locale, email_placeholders, all_placeholders):
    result = True
    missing_placeholders = set(all_placeholders) - set(email_placeholders)
    if missing_placeholders:
        logger.error('There are missing placeholders %s in email %s, locale %s' %
                     (missing_placeholders, email_name, email_locale))
        result = False
    extra_placeholders = set(email_placeholders) - set(all_placeholders)
    if extra_placeholders:
        logger.error('There are extra placeholders %s in email %s, locale %s' %
                     (extra_placeholders, email_name, email_locale))
        result = False

    for name, count in all_placeholders.items():
        email_count = email_placeholders.get(name, 0)
        if count != email_count:
            logger.error('The number of placeholders "%s" in email "%s" locale "%s" should be %s but was %s' %
                         (name, email_name, email_locale, count, email_count))
            result = False
    return result


def _all_placeholders_for_email_name(locale_placeholders):
    result = {}
    for counter in locale_placeholders.values():
        for name, count in counter.items():
            if name in result and result[name] > count:
                continue
            result[name] = count
    return result


def _placeholders_from_emails(emails):
    placeholders = defaultdict(dict)
    for email in emails:
        email_placeholders = _parse_email_placeholders(email.full_path)
        placeholders[email.name][email.locale] = email_placeholders
    return placeholders


def _validate_placeholders(placeholders):
    result = True
    for email_name, locale_placeholders in placeholders.items():
        all_placeholders = _all_placeholders_for_email_name(locale_placeholders)
        for email_locale, email_placeholders in locale_placeholders.items():
            if not _validate_email_placeholders(email_name, email_locale, email_placeholders, all_placeholders):
                result = False
    return result


def _reduce_to_email_placeholders(placeholders):
    return {email_name: _all_placeholders_for_email_name(locale_placeholders)
            for email_name, locale_placeholders in placeholders.items()}


def generate_config(settings, indent=4):
    emails = fs.emails(settings.source, settings.pattern)
    emails = filter(lambda e: e.locale == 'en', emails)
    placeholders = _placeholders_from_emails(emails)
    placeholders = _reduce_to_email_placeholders(placeholders)
    if placeholders:
        _save_placeholders_file(placeholders, settings.source, indent)
        return True
    return False


def validate_email(email, src_dir=''):
    try:
        all_placeholders = _read_email_placeholders(email.name, src_dir)
        email_placeholders = _parse_email_placeholders(email.full_path)
        logger.debug('validating placeholders for %s', email.path)
        return _validate_email_placeholders(email.name, email.locale, email_placeholders, all_placeholders)
    except FileNotFoundError:
        # If the file does not exist skip validation
        return True

def validate_email_content(locale, name, content, src_dir=''):
    try:
        all_placeholders = _read_email_placeholders(name, src_dir)
        email_placeholders = _parse_string_placeholders(content)
        return _validate_email_placeholders(name, locale, email_placeholders, all_placeholders)
    except FileNotFoundError:
        # If the file does not exist skip validation
        return True


def from_email_name(email_name, src_dir=''):
    placeholders = _read_placeholders_file(src_dir).get(email_name, {})
    return list(placeholders)
