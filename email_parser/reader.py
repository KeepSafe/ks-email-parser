from collections import namedtuple, OrderedDict
from xml.etree import ElementTree

Template = namedtuple('Template', ['name', 'styles'])


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
    tree = ElementTree.parse(email_path)

    template = _template(tree)
    placeholders = _placeholders(tree)

    return template, placeholders
