"""
Extracts email information from an email file.
"""

import logging
import re
from collections import namedtuple, OrderedDict
from xml.etree import ElementTree

SEGMENT_REGEX = r'\<string[^>]*>'
SEGMENT_NAME_REGEX = r' name="([^"]+)"'

Template = namedtuple('Template', ['name', 'styles'])


def _ignored_placeholder_names(tree):
    return [element.get('name') for element in tree.findall('./string') if element.get('isText') == 'false']


def _placeholders(tree):
    return OrderedDict((element.get('name'), element.text) for element in tree.findall('./string'))


def _template(tree, email_path):
    name = tree.getroot().get('template')
    if name is None:
        logging.error('no HTML template name define for %s', email_path)

    style_element = tree.getroot().get('style')
    if style_element:
        styles = style_element.split(',')
    else:
        styles = []

    return Template(name, styles)


def _find_parse_error(file_path, exception):
    pos = exception.position
    with open(file_path) as f:
        lines = f.read().splitlines()
        error_line = lines[pos[0] - 1]
        node_matches = re.findall(SEGMENT_REGEX, error_line[:pos[1]])
        segment_id = None

        if not len(node_matches):
            prev_line = pos[0] - 1
            search_part = ''.join(lines[:prev_line])
            node_matches = re.findall(SEGMENT_REGEX, search_part)

        if len(node_matches):
            name_matches = re.findall(SEGMENT_NAME_REGEX, node_matches[-1])
            if len(name_matches):
                segment_id = name_matches[-1]

        return error_line, segment_id


def read(email_path):
    """
    Reads an email from the path.

    :param email_path: full path to an email
    :returns: tuple of email template, a collection of placeholders and ignored_placeholder_names
    """
    try:
        tree = ElementTree.parse(email_path)
    except ElementTree.ParseError as e:
        line, segment_id = _find_parse_error(email_path, e)

        logging.exception(
            'Unable to read content from %s\n%s\nSegment ID: %s\n_______________\n%s\n%s\n',
            email_path,
            e,
            segment_id,
            line.replace('\t', '  '),
            " " * e.position[1] + "^")

        return None, {}, []

    template = _template(tree, email_path)
    placeholders = _placeholders(tree)
    ignored_plceholder_names = _ignored_placeholder_names(tree)

    return template, placeholders, ignored_plceholder_names
