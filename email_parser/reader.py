"""
Extracts email information from an email file.
"""

import logging
import re
from collections import namedtuple, OrderedDict
from xml.etree import ElementTree
from . import fs

SEGMENT_REGEX = r'\<string[^>]*>'
SEGMENT_NAME_REGEX = r' name="([^"]+)"'

Template = namedtuple('Template', ['name', 'styles', 'content', 'placeholders_order'])


def _ignored_placeholder_names(tree, prefix=''):
    return ['{0}{1}'.format(prefix, element.get('name')) for element in tree.findall('./string') if element.get('isText') == 'false']


def _placeholders(tree, prefix=''):
    return {'{0}{1}'.format(prefix, element.get('name')): element.text for element in tree.findall('./string')}

def _email_placeholders(tree, global_tree):
    placeholders = dict(_placeholders(tree).items() | _placeholders(global_tree, 'global_').items())
    ignored_placeholder_names = _ignored_placeholder_names(tree) + _ignored_placeholder_names(global_tree, 'global_')
    return placeholders, ignored_placeholder_names

def _ordered_placeholders(names, placeholders):
    if 'subject' not in names:
        names.append('subject')
    return OrderedDict((name, placeholders[name]) for name in names)

def _template(tree, settings):
    content = None
    placeholders = []
    styles = []

    name = tree.getroot().get('template')
    if name:
        content = fs.read_file(settings.templates, name)
        placeholders = [m.group(1) for m in re.finditer(r'\{\{(\w+)\}\}', content)]

    style_element = tree.getroot().get('style')
    if style_element:
        styles = style_element.split(',')

    return Template(name, styles, content, placeholders)

def _find_parse_error(file_path, exception):
    pos = exception.position
    with open(file_path) as f:
        lines = f.read().splitlines()
        error_line = lines[pos[0]-1]
        node_matches = re.findall(SEGMENT_REGEX, error_line[:pos[1]])
        segment_id = None

        if not len(node_matches):
            prev_line = pos[0]-1
            search_part = ''.join(lines[:prev_line])
            node_matches = re.findall(SEGMENT_REGEX, search_part)

        if len(node_matches):
            name_matches = re.findall(SEGMENT_NAME_REGEX, node_matches[-1])
            if len(name_matches):
                segment_id = name_matches[-1]

        return error_line, segment_id


def _handle_xml_parse_error(path, e):
    line, segment_id = _find_parse_error(path, e)
    logging.exception(
        'Unable to read content from %s\n%s\nSegment ID: %s\n_______________\n%s\n%s\n',
        path,
        e,
        segment_id,
        line.replace('\t', '  '),
        " "*e.position[1]+"^")


def read(email, settings):
    """
    Reads an email from the path.

    :param email_path: full path to an email
    :returns: tuple of email template, a collection of placeholders and ignored_placeholder_names
    """
    # read email
    try:
        tree = ElementTree.parse(email.full_path)
    except ElementTree.ParseError as e:
        _handle_xml_parse_error(email.full_path, e)
        return None, {}, []

    # read global placeholders email
    try:
        global_email_path = settings.pattern.replace('{locale}', email.locale)
        global_email_path = global_email_path.replace('{name}', fs.GLOBAL_PLACEHOLDERS_EMAIL_NAME)
        global_email_fullpath = fs.path(settings.source, global_email_path)
        global_tree = ElementTree.parse(global_email_fullpath)
    except ElementTree.ParseError as e:
        _handle_xml_parse_error(global_email_path, e)
        return None, {}, []

    template = _template(tree, settings)
    if not template.name:
        logging.error('no HTML template name define for %s', email.path)

    placeholders, ignored_plceholder_names = _email_placeholders(tree, global_tree)
    ordered_placeholders = _ordered_placeholders(template.placeholders_order, placeholders)

    return template, ordered_placeholders, ignored_plceholder_names
