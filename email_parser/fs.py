"""
All filesystem interaction.
"""

import logging
import os
import parse
import re
from pathlib import Path
from string import Formatter

from . import const
from .model import *

logger = logging.getLogger(__name__)


def _parse_params(pattern):
    params = [p for p in map(lambda e: e[1], Formatter().parse(pattern)) if p]
    if 'name' not in params:
        raise MissingPatternParamError(
            '{{name}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    if 'locale' not in params:
        raise MissingPatternParamError(
            '{{locale}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    return params


def _has_correct_ext(path, pattern):
    return os.path.splitext(str(path))[1] == os.path.splitext(pattern)[1]


def _emails(pattern, params):
    wildcard_params = {k: '*' for k in params}
    wildcard_pattern = pattern.format(**wildcard_params)
    parser = parse.compile(pattern)
    glob_path = Path(const.DIR_SOURCE).glob(wildcard_pattern)
    global_email_pattern = re.compile('/%s\.xml$' % const.GLOBALS_EMAIL_NAME)
    for path in sorted(glob_path, key=lambda path: str(path)):
        if not path.is_dir() and _has_correct_ext(path, pattern):
            str_path = str(path.relative_to(const.DIR_SOURCE))
            result = parser.parse(str_path)
            if result:  # HACK: result can be empty when pattern doesn't contain any placeholder
                result.named['path'] = str_path
                result.named['full_path'] = str(path.resolve())
                if not re.findall(global_email_pattern, str_path):
                    logger.debug('loading email %s', result.named['full_path'])
                    yield result


# TODO eliminate pattern
def emails(pattern, locale=None):
    """
    Resolves a pattern to a collection of emails. 

    :param src_dir: base dir for the search
    :param pattern: search pattern
    :exclusive_path: single email path, glob path for emails subset or None to not affect emails set

    :returns: generator for the emails matching the pattern
    """
    params = _parse_params(pattern)
    if locale:
        pattern = pattern.replace('{locale}', locale)
    for result in _emails(pattern, params):
        yield Email(**result.named)


def email(email_name, locale, pattern):
    """
    Gets an email by name and locale

    :param src_dir: base dir for the search
    :param pattern: search pattern
    :param email_name: email name
    :param locale: locale name or None for all locales

    :returns: generator for the emails with email_name
    """
    params = _parse_params(pattern)
    pattern = pattern.replace('{name}', email_name)
    pattern = pattern.replace('{locale}', locale)
    for result in _emails(pattern, params):
        result.named['name'] = email_name
        result.named['locale'] = locale
        return Email(**result.named)
    return None


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


def delete_file(*path_parts):
    path = os.path.join(*path_parts)
    logger.debug('deleting file to %s', path)
    os.remove(path)


def save_email(email, subjects, text, html):
    """
    Saves an email. The locale and name are taken from email tuple.

    :param email: Email tuple
    :param subject: email's subject
    :param text: email's body as text
    :param html: email's body as html
    :param dest_dir: root destination directory
    """
    locale = email.locale or const.DEFAULT_LOCALE
    os.makedirs(os.path.join(dest_dir, locale), exist_ok=True)
    save_file(subjects[0], dest_dir, locale, email.name + const.SUBJECT_EXTENSION)
    if len(subjects) > 1 and subjects[1] is not None:
        save_file(subjects[1], dest_dir, locale, email.name + const.SUBJECT_A_EXTENSION)
    if len(subjects) > 2 and subjects[2] is not None:
        save_file(subjects[2], dest_dir, locale, email.name + const.SUBJECT_B_EXTENSION)
    if len(subjects) > 3 and subjects[3] is not None:
        save_file(subjects[3], dest_dir, locale, email.name + const.SUBJECT_RESEND_EXTENSION)
    save_file(text, dest_dir, locale, email.name + const.TEXT_EXTENSION)
    save_file(html, dest_dir, locale, email.name + const.HTML_EXTENSION)


def resolve_path(template_name, locale):
    pattern = const.DEFAULT_PATTERN.replace('{locale}', locale)
    pattern = pattern.replace('{name}', template_name)
    return os.path.join(const.DIR_SOURCE, pattern)


def template(name):
    pass


def style(name):
    pass
