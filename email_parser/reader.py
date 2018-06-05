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


def _parse_placeholder(placeholder_str):
    args = {}
    try:
        placeholder_type, name, args_str = placeholder_str.split(':')
    except ValueError:
        return MetaPlaceholder(placeholder_str)
    try:
        placeholder_type = PlaceholderType(placeholder_type)
    except ValueError:
        raise ValueError('Placeholder definition %s uses invalid PlaceholderType' % placeholder_str)
    for attr_str in args_str.split(';'):
        attr_name, attr_value = attr_str.split('=')
        args[attr_name] = attr_value
    return MetaPlaceholder(name, placeholder_type, args)


def _placeholders(tree, prefix=''):
    if tree is None:
        return {}
    is_global = (prefix == const.GLOBALS_PLACEHOLDER_PREFIX)
    result = OrderedDict()
    for element in tree.xpath('./string | ./string-array | ./array'):
        name = '{0}{1}'.format(prefix, element.get('name'))
        placeholder_type = PlaceholderType[element.get('type', PlaceholderType.text.value)]
        opt_attrs = dict(element.items())
        del opt_attrs['name']
        try:
            del opt_attrs['type']
        except KeyError:
            pass
        if element.tag == 'string':
            content = element.text or ''
            result[name] = Placeholder(name, content.strip(), is_global, placeholder_type, None, opt_attrs)
        elif element.tag in ['string-array', 'array']:
            content = ''
            variants = {}
            for item in element.findall('./item'):
                variant = item.get('variant')
                if variant:
                    variants[variant] = item.text.strip()
                else:
                    content = item.text.strip()
            result[name] = Placeholder(name, content, is_global, placeholder_type, variants, opt_attrs)
        else:
            raise Exception('Unknown tag:\n%s' % element)

    return result


def get_template_parts(root_path, template_filename, template_type):
    content = None
    placeholders = OrderedDict()

    try:
        template_type = EmailType(template_type)
    except ValueError:
        template_type = None

    if template_type:
        template_path = str(fs.get_template_filepath(root_path, template_filename, template_type.value))
        content = fs.read_file(template_path)
    else:
        logger.warning('FIXME: no email_type set for: %s, trying all types..', template_filename)
        for email_type in EmailType:
            try:
                template_path = str(fs.get_template_filepath(root_path, template_filename, email_type.value))
                content = fs.read_file(template_path)
                break
            except FileNotFoundError:
                continue

    for m in re.finditer(r'\{\{(\w+)\}\}', content):
        placeholder_def = m.group(1)
        placeholder_meta = MetaPlaceholder(placeholder_def)
        placeholders[placeholder_meta.name] = placeholder_meta

    try:
        # TODO sad panda, refactor
        # base_url placeholder is not a content block
        del placeholders['base_url']
    except KeyError:
        pass

    return content, placeholders


def get_inline_style(root_path, styles_names):
    if not len(styles_names):
        return ''
    css = [fs.read_file(root_path, config.paths.templates, f) or ' ' for f in styles_names]
    styles = '\n'.join(css)
    return '<style>%s</style>' % styles


def _template(root_path, tree):
    styles = ''
    styles_names = []

    template_filename = tree.getroot().get('template')
    email_type = tree.getroot().get('email_type')
    content, placeholders = get_template_parts(root_path, template_filename, email_type)
    style_element = tree.getroot().get('style')

    if style_element:
        styles_names = style_element.split(',')
        styles = get_inline_style(root_path, styles_names)

    # TODO either read all or leave just names for content and styles
    return Template(template_filename, styles_names, styles, content, placeholders, email_type)


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


def _sort_from_template(root_path, template_filename, template_type, placeholders):
    _, placeholders_ordered = get_template_parts(root_path, template_filename, template_type)
    ordered_placeholders_names = list(placeholders_ordered.keys())
    placeholders.sort(
        key=lambda item: ordered_placeholders_names.index(item.name) if item.name in ordered_placeholders_names else 99)


def create_email_content(root_path, template_name, styles, placeholders, email_type):
    root = etree.Element('resources')
    root.set('template', template_name)
    root.set('style', ','.join(styles))
    if email_type:
        root.set('email_type', email_type.value)
    _sort_from_template(root_path, template_name, email_type, placeholders)
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
        elif placeholder.type == PlaceholderType.bitmap:
            new_content_tag = etree.SubElement(root, 'bitmap', {
                'name': placeholder.name,
                'type': placeholder.type.value,
                'id': placeholder.id,
            })
        else:
            new_content_tag = etree.SubElement(root, 'string', {
                'name': placeholder.name,
                'type': placeholder.type.value or PlaceholderType.text.value
            })
            new_content_tag.text = etree.CDATA(placeholder.get_content())
    xml_as_str = etree.tostring(root, encoding='utf8', pretty_print=True)
    return xml_as_str.decode('utf-8')


def get_global_placeholders(root_path, locale):
    globals_xml = _read_xml(fs.global_email(root_path, locale).path)
    return _placeholders(globals_xml, const.GLOBALS_PLACEHOLDER_PREFIX)


def read_from_content(root_path, email_content, locale):
    email_xml = _read_xml_from_content(email_content)
    if not email_xml:
        return None, None
    template = _template(root_path, email_xml)

    if not template.name:
        logger.error('no HTML template name defined for given content')
    global_placeholders = get_global_placeholders(root_path, locale)
    placeholders = OrderedDict({name: content for name, content
                                in global_placeholders.items()
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


def get_email_type(root_path, email):
    email_content = fs.read_file(email.path)
    email_xml = _read_xml_from_content(email_content)
    return email_xml.getroot().get('email_type')
