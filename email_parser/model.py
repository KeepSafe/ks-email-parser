from collections import namedtuple
from enum import Enum


class PlaceholderType(Enum):
    attribute = 'attribute'
    raw = 'raw'
    text = 'text'


Email = namedtuple('Email', ['name', 'locale', 'path'])
Template = namedtuple('Template', ['name', 'styles_names', 'styles', 'content', 'placeholders'])
Placeholder = namedtuple('Placeholder', ['name', 'content', 'is_global', 'type'])
Placeholder.__new__.__defaults__ = (False, PlaceholderType.text)


class MissingPatternParamError(Exception):
    pass


class MissingSubjectError(Exception):
    pass


class MissingTemplatePlaceholderError(Exception):
    pass


class RenderingError(Exception):
    pass
