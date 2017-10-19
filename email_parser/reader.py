"""
Extracts email information from an email file.
"""

import logging
import re
from collections import OrderedDict

from lxml import etree

from . import fs, const, config
from .model import *

logger = logging.getLogger(__name__)


def _get_placeholder_order_num(placeholder_name, template_placeholders):
    if placeholder_name == const.SUBJECT_PLACEHOLDER:
        return -1
    elif placeholder_name in template_placeholders:
        return template_placeholders.index(placeholder_name)
    else:
        return 99


def _placeholders(tree, template_placeholders, prefix='', template_only=False):
    if tree is None:
        return {}
    is_global = (prefix == const.GLOBALS_PLACEHOLDER_PREFIX)
    result = {}
    for element in tree.xpath('./string | ./string-array'):
        name = '{0}{1}'.format(prefix, element.get('name'))
        if template_only and name in template_placeholders or not template_only:
            order_num = _get_placeholder_order_num(name, template_placeholders)
            placeholder_type = PlaceholderType[element.get('type', PlaceholderType.text.value)]
            if element.tag == 'string':
                content = element.text or ''
                result[name] = Placeholder(name, content.strip(), order_num, is_global, placeholder_type)
            else:
                content = ''
                variants = {}
                for item in element.findall('./item'):
                    variant = item.get('variant')
                    if variant:
                        variants[variant] = item.text.strip()
                    else:
                        content = item.text.strip()
                result[name] = Placeholder(name, content, order_num, is_global, placeholder_type, variants)

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
        parser = etree.XMLParser(encoding='utf-8')
        return etree.parse(path, parser=parser)
    except etree.ParseError as e:
        _handle_xml_parse_error(path, e)
        return None


def _read_xml_from_content(content):
    if not content:
        return None
    try:
        parser = etree.XMLParser(encoding='utf-8')
        root = etree.fromstring(content.encode('utf-8'), parser=parser)
        return etree.ElementTree(root)
    except etree.ParseError as e:
        logger.exception('Unable to parse XML content %s %s', content, e)
        return None
    except TypeError:
        # got None? no results
        return None


def create_email_content(template_name, styles, placeholders, email_type=None):
    root = etree.Element('resources')
    root.set('template', template_name)
    root.set('style', ','.join(styles))
    if email_type:
        root.set('email_type', email_type.value)
    placeholders.sort(key=lambda item: item.order)
    for placeholder in placeholders:
        if placeholder.variants:
            new_content_tag = etree.SubElement(root, 'string-array', {
                'name': placeholder.name,
                'type': placeholder.type.value or PlaceholderType.text.value
            })
            default_item_tag = etree.SubElement(new_content_tag, 'item')
            default_item_tag.text = etree.CDATA(placeholder.get_content())
            for variant_name, variant_content in placeholder.variants.items():
                new_item_tag = etree.SubElement(new_content_tag, 'item', {'variant': variant_name})
                new_item_tag.text = etree.CDATA(variant_content)
        else:
            new_content_tag = etree.SubElement(root, 'string', {
                'name': placeholder.name,
                'type': placeholder.type.value or PlaceholderType.text.value
            })
            new_content_tag.text = etree.CDATA(placeholder.get_content())
    xml_as_str = etree.tostring(root, encoding='utf8', pretty_print=True)
    return xml_as_str.decode('utf-8')


def read_from_content(root_path, email_content, locale):
    email_xml = _read_xml_from_content(email_content)
    if not email_xml:
        return None, None
    template = _template(root_path, email_xml)

    if not template.name:
        logger.error('no HTML template name defined for given content')

    globals_xml = _read_xml(fs.global_email(root_path, locale).path)
    placeholders = _placeholders(globals_xml, template.placeholders,
                                 prefix=const.GLOBALS_PLACEHOLDER_PREFIX, template_only=True)
    placeholders.update(_placeholders(email_xml, template.placeholders).items())

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


def get_email_type(root_path, email):
    email_content = fs.read_file(email.path)
    email_xml = _read_xml_from_content(email_content)
    return email_xml.getroot().get('email_type')
