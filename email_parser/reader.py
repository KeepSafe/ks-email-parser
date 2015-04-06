"""
Extracts email information from an email file.
"""

import logging
from collections import namedtuple, OrderedDict
from xml.etree import ElementTree

Template = namedtuple('Template', ['name', 'styles'])


def _ignored_placeholder_names(tree):
    return [element.get('name') for element in tree.findall('./string') if element.get('isText') == 'false']


def _placeholders(tree):
    return OrderedDict((element.get('name'), element.text) for element in tree.findall('./string'))


def _template(tree):
    name = tree.getroot().get('template')
    if name is None:
        logging.error('no HTML template name define for %s', email_path)

    style_element = tree.getroot().get('style')
    if style_element:
        styles = style_element.split(',')
    else:
        styles = []

    return Template(name, styles)


def read(email_path):
    """
    Reads an email from the path.

    :param email_path: full path to an email
    :returns: tuple of email template, a collection of placeholders and ignored_placeholder_names
    """
    try:
        tree = ElementTree.parse(email_path)
    except ElementTree.ParseError:
        logging.exception('Unable to read content from %s', email_path)
        return None, {}, []

    template = _template(tree)
    placeholders = _placeholders(tree)
    ignored_plceholder_names = _ignored_placeholder_names(tree)

    return template, placeholders, ignored_plceholder_names
