"""
All filesystem interaction.
"""

import logging
import os
import parse
from pathlib import Path
from string import Formatter
from collections import namedtuple

from . import errors

SUBJECT_EXTENSION = '.subject'
TEXT_EXTENSION = '.text'
HTML_EXTENSION = '.html'

Email = namedtuple('Email', ['name', 'locale', 'path', 'full_path'])
logger = logging.getLogger()


def _parse_params(pattern):
    params = [p for p in map(lambda e: e[1], Formatter().parse(pattern)) if p]
    if 'name' not in params:
        raise errors.MissingPatternParamError(
            '{{name}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    if 'locale' not in params:
        raise errors.MissingPatternParamError(
            '{{name}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    return params


def _emails(src_dir, pattern, params, exclusive_path=None):
    wildcard_params = {k: '*' for k in params}
    wildcard_pattern = pattern.format(**wildcard_params)
    parser = parse.compile(pattern)

    if exclusive_path:
        glob_path = Path('.').glob(exclusive_path)
    else:
        glob_path = Path(src_dir).glob(wildcard_pattern)

    for path in sorted(glob_path, key=lambda path: str(path)):
        if not path.is_dir() and (not exclusive_path or _has_correct_ext(path, pattern)):
            str_path = str(path.relative_to(src_dir))
            result = parser.parse(str_path)
            result.named['path'] = str_path
            result.named['full_path'] = str(path.resolve())
            logging.debug('loading email %s', result.named['full_path'])
            yield result


def _has_correct_ext(path, pattern):
    return os.path.splitext(str(path))[1] == os.path.splitext(pattern)[1]


def emails(src_dir, pattern, exclusive_path=None):
    """
    Resolves a pattern to a collection of emails. The pattern needs to have 'name' and 'locale' as this is used later
    to produce the results.

    :param src_dir: base dir for the search
    :param pattern: search pattern
    :exclusive_path: single email path, glob path for emails subset or None to not affect emails set

    :returns: generator for the emails matching the pattern
    """
    params = _parse_params(pattern)
    for result in _emails(src_dir, pattern, params, exclusive_path):
        yield Email(**result.named)


def email(src_dir, pattern, email_name, locale=None):
    """
    Gets an email by name. Used for clients which should produce a single file for all locales.

    :param src_dir: base dir for the search
    :param pattern: search pattern
    :param email_name: email name
    :param locale: locale name or None for all locales

    :returns: generator for the emails with email_name
    """
    single_email_pattern = pattern.replace('{name}', email_name)
    if locale:
        single_email_pattern = single_email_pattern.replace('{locale}', locale)
    params = _parse_params(pattern)
    for result in _emails(src_dir, single_email_pattern, params):
        result.named['name'] = email_name
        if locale:
            result.named['locale'] = locale
        yield Email(**result.named)


def read_file(*path_parts, **kwargs):
    """
    Helper for reading files
    """
    path = os.path.join(*path_parts)
    logger.debug('reading file from %s', path)
    with open(path, **kwargs) as fp:
        return fp.read()


def save_file(content, *path_parts):
    """
    Helper for saving files
    """
    path = os.path.join(*path_parts)
    logger.debug('saving file to %s', path)
    with open(path, 'w') as fp:
        return fp.write(content)


def save(email, subject, text, html, dest_dir, fallback_locale=None):
    """
    Saves an email. The locale and name are taken from email tuple.

    :param email: Email tuple
    :param subject: email's subject
    :param text: email's body as text
    :param html: email's body as html
    :param dest_dir: root destination directory
    """
    locale = fallback_locale if fallback_locale else email.locale

    os.makedirs(os.path.join(dest_dir, locale), exist_ok=True)
    save_file(subject, dest_dir, locale, email.name + SUBJECT_EXTENSION)
    save_file(text, dest_dir, locale, email.name + TEXT_EXTENSION)
    save_file(html, dest_dir, locale, email.name + HTML_EXTENSION)
