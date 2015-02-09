"""
Extracts email information from an email file.
"""

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
    """
    Reads an email from the path.

    :param email_path: full path to an email
    :returns: tuple of email template and a collection of placeholders
    """
    tree = ElementTree.parse(email_path)

    template = _template(tree)
    placeholders = _placeholders(tree)

    return template, placeholders
