"""
Extracts email information from an email file.
"""

import logging
import re
from collections import OrderedDict
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from . import fs, const, config
from .model import *

logger = logging.getLogger(__name__)


def _placeholders(tree, prefix=''):
    if tree is None:
        return {}
    result = OrderedDict()
    for element in tree.findall('./string'):
        name = '{0}{1}'.format(prefix, element.get('name'))
        content = element.text or ''
        is_text = element.get('isText', 'true') == 'true'
        is_global = prefix == const.GLOBALS_PLACEHOLDER_PREFIX
        result[name] = Placeholder(name, content.strip(), is_text, is_global)
    return result


def get_template_parts(root_path, template_filename):
    content = None
    placeholders = []

    if template_filename:
        content = fs.read_file(root_path, config.paths.templates, template_filename)
        placeholders = [m.group(1) for m in re.finditer(r'\{\{(\w+)\}\}', content)]

    # TODO sad panda, refactor
    # base_url placeholder is not a content block
    while 'base_url' in placeholders:
        placeholders.remove('base_url')

    return content, placeholders


def _template(root_path, tree):
    styles = ''
    styles_names = []

    template_filename = tree.getroot().get('template')
    content, placeholders = get_template_parts(root_path, template_filename)
    style_element = tree.getroot().get('style')

    if style_element:
        styles_names = style_element.split(',')
        css = [fs.read_file(root_path, config.paths.templates, f) or ' ' for f in styles_names]
        styles = '\n'.join(css)
        styles = '<style>%s</style>' % styles

    # TODO either read all or leave just names for content and styles
    return Template(template_filename, styles_names, styles, content, placeholders)


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
        return None
    try:
        return ElementTree.parse(path)
    except ElementTree.ParseError as e:
        _handle_xml_parse_error(path, e)
        return None


def _read_xml_from_content(content):
    try:
        root = ElementTree.fromstring(content)
        return ElementTree.ElementTree(root)
    except ElementTree.ParseError as e:
        logger.exception('Unable to parse XML content %s %s', content, e)
        return None
    except TypeError:
        # got None? no results
        return None


def create_email_content(template_name, styles, placeholders):
    root = ElementTree.Element('resource')
    root.set('xmlns:tools', 'http://schemas.android.com/tools')
    root.set('template', template_name)
    root.set('style', ','.join(styles))
    for placeholder in placeholders:
        new_content_tag = ElementTree.SubElement(root, 'string', {
            'name': placeholder.name,
            'isText': str(placeholder.is_text).lower(),
        })
        new_content_tag.text = '![CDATA[' + placeholder.content + ']]'
    xml_as_str = ElementTree.tostring(root, encoding='utf8')
    pretty_xml = BeautifulSoup(xml_as_str, "xml").prettify()
    return pretty_xml


def read_from_content(root_path, email_content, locale):
    email_xml = _read_xml_from_content(email_content)
    if not email_xml:
        return None, None
    template = _template(root_path, email_xml)

    if not template.name:
        logger.error('no HTML template name defined for given content')

    globals_xml = _read_xml(fs.global_email(root_path, locale).path)
    placeholders = OrderedDict({name: content for name, content
                                in _placeholders(globals_xml, const.GLOBALS_PLACEHOLDER_PREFIX).items()
                                if name in template.placeholders})
    placeholders.update(_placeholders(email_xml).items())

    return template, placeholders


def read(root_path, email):
    """
    Reads an email from a path.

    :param root_path: root path of repository
    :param email: instance of Email namedtuple
    :returns: tuple of email template, a collection of placeholders
    """
    email_content = fs.read_file(email.path)
    results = read_from_content(root_path, email_content, email.locale)
    if not results[0] and email.locale != const.DEFAULT_LOCALE:
        email = fs.email(root_path, email.name, const.DEFAULT_LOCALE)
        email_content = fs.read_file(email.path)
        results = read_from_content(root_path, email_content, email.locale)

    return results
