"""
All filesystem interaction.
"""

import logging
import os
import parse
from pathlib import Path
from string import Formatter
from collections import namedtuple

from . import errors, consts

Email = namedtuple('Email', ['name', 'locale', 'path', 'full_path'])


def _parse_params(pattern):
    params = [p for p in map(lambda e: e[1], Formatter().parse(pattern)) if p]
    if 'name' not in params:
        raise errors.MissingPatternParamError(
            '{{name}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    if 'locale' not in params:
        raise errors.MissingPatternParamError(
            '{{name}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    return params


def emails(src_dir, pattern):
    """
    Resolves a pattern to a collection of emails. The pattern needs to have 'name' and 'locale' as this is used later
    to produce the results.

    :param src_dir: base dir for the search
    :param pattern: search pattern

    :returns: generator for the emails matching the pattern
    """
    params = _parse_params(pattern)

    wildcard_params = {k: '*' for k in params}
    wildcard_pattern = pattern.format(**wildcard_params)
    parser = parse.compile(pattern)

    for path in Path(src_dir).glob(wildcard_pattern):
        if not path.is_dir():
            str_path = str(path.relative_to(src_dir))
            result = parser.parse(str_path)
            result.named['path'] = str_path
            result.named['full_path'] = str(path.resolve())
            yield Email(**result.named)


def email(src_dir, pattern, email_name):
    """
    Gets an email by name. Used for clients which should produce a single file for all locales.

    :param src_dir: base dir for the search
    :param pattern: search pattern
    :param email_name: email name for all locales

    :returns: generator for the emails with email_name
    """
    single_email_pattern = pattern.replace('{name}', email_name)

    #TODO refactor with emails
    params = _parse_params(pattern)

    wildcard_params = {k: '*' for k in params}
    wildcard_pattern = single_email_pattern.format(**wildcard_params)
    parser = parse.compile(single_email_pattern)

    for path in Path(src_dir).glob(wildcard_pattern):
        if not path.is_dir():
            str_path = str(path.relative_to(src_dir))
            result = parser.parse(str_path)
            result.named['name'] = email_name
            result.named['path'] = str_path
            result.named['full_path'] = str(path.resolve())
            yield Email(**result.named)


def read_file(*path_parts):
    """
    Helper for reading files
    """
    path = os.path.join(*path_parts)
    with open(path) as fp:
        return fp.read()

def save_file(content, *path_parts):
    """
    Helper for saving files
    """
    path = os.path.join(*path_parts)
    with open(path, 'w') as fp:
        return fp.write(content)


def save(email, subject, text, html, dest_dir):
    """
    Saves an email. The locale and name are taken from email tuple.

    :param email: Email tuple
    :param subject: email's subject
    :param text: email's body as text
    :param html: email's body as html
    :param dest_dir: root destination directory
    """
    os.makedirs(os.path.join(dest_dir, email.locale), exist_ok=True)
    save_file(subject, dest_dir, email.locale, email.name + consts.SUBJECT_EXTENSION)
    save_file(text, dest_dir, email.locale, email.name + consts.TEXT_EXTENSION)
    save_file(html, dest_dir, email.locale, email.name + consts.HTML_EXTENSION)
