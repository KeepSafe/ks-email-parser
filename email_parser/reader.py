"""
Extracts email information from an email file.
"""

import logging
import re
from collections import OrderedDict
from xml.etree import ElementTree

from . import fs, const
from .model import *

logger = logging.getLogger(__name__)


def _placeholders(tree, prefix=''):
    if tree is None:
        return {}
    result = OrderedDict()
    for element in tree.findall('./string'):
        name = '{0}{1}'.format(prefix, element.get('name'))
        result[name] = Placeholder(name, element.text, element.get('isText', 'true') == 'true')
    return result


def _template(tree):
    content = None
    placeholders = []
    styles = []

    template_name = tree.getroot().get('template')
    if template_name:
        content = fs.template(template_name)
        placeholders = [m.group(1) for m in re.finditer(r'\{\{(\w+)\}\}', content)]

    # TODO sad panda, refactor
    # base_url placeholder is not a content block
    while 'base_url' in placeholders:
        placeholders.remove('base_url')

    style_element = tree.getroot().get('style')
    if style_element:
        styles = style_element.split(',')
        css = [fs.style(f) or ' ' for f in styles]
        styles = '\n'.join(css)
        styles = '<style>%s</style>' % styles
    else:
        styles = ''

    # TODO either read all or leave just names for content and styles
    return Template(template_name, styles, content, placeholders)


def _globals_path(email):
    email_globals = fs.email(const.GLOBALS_EMAIL_NAME, email.locale, const.DEFAULT_PATTERN)
    if email_globals:
        return email_globals.full_path
    else:
        return None


def _handle_xml_parse_error(file_path, exception):
    pos = exception.position
    with open(file_path) as f:
        lines = f.read().splitlines()
        error_line = lines[pos[0] - 1]
        node_matches = re.findall(const.SEGMENT_REGEX, error_line[:pos[1]])
        segment_id = None

        if not len(node_matches):
            prev_line = pos[0] - 1
            search_part = ''.join(lines[:prev_line])
            node_matches = re.findall(const.SEGMENT_REGEX, search_part)

        if len(node_matches):
            name_matches = re.findall(const.SEGMENT_NAME_REGEX, node_matches[-1])
            if len(name_matches):
                segment_id = name_matches[-1]
    logger.exception('Unable to read content from %s\n%s\nSegment ID: %s\n_______________\n%s\n%s\n', file_path,
                     exception, segment_id, error_line.replace('\t', '  '), " " * exception.position[1] + "^")


def _read_xml(path):
    if not path:
        return {}
    try:
        return ElementTree.parse(path)
    except ElementTree.ParseError as e:
        _handle_xml_parse_error(path, e)
        return {}


def read(email):
    """
    Reads an email from a path.

    :param email_path: a full path to an email
    :returns: tuple of email template, a collection of placeholders
    """
    email_xml = _read_xml(email.full_path)
    template = _template(email_xml)

    if not template.name:
        logger.error('no HTML template name define for %s', email.path)

    globals_xml = _read_xml(_globals_path(email))
    placeholders = OrderedDict(_placeholders(email_xml).items() | _placeholders(globals_xml, 'global_').items())

    return template, placeholders
