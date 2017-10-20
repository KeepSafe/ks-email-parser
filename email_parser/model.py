from collections import namedtuple
from enum import Enum


class PlaceholderType(Enum):
    attribute = 'attribute'
    raw = 'raw'
    text = 'text'
    image = 'image'


class EmailType(Enum):
    marketing = 'marketing'
    transactional = 'transactional'


Email = namedtuple('Email', ['name', 'locale', 'path'])
Template = namedtuple('Template', ['name', 'styles_names', 'styles', 'content', 'placeholders'])


class Placeholder:
    def __init__(self, name, content, order, is_global=False, p_type=PlaceholderType.text, variants=None):
        self.name = name
        self.order = order
        self.is_global = is_global
        self.type = p_type
        self._content = content
        self.variants = variants or {}

    def __iter__(self):
        for k, v in self.__dict__.items():
            if k is 'type':
                yield k, self.type.value
            elif k is '_content':
                yield 'content', v
            else:
                yield k, v

    def __eq__(self, other):
        return dict(self) == dict(other)

    def get_content(self, variant=None):
        if variant:
            return self.variants.get(variant, self._content)
        else:
            return self._content

    def pick_variant(self, variant):
        self._content = self.get_content(variant)
        self.variants = {}
        return self


class MissingPatternParamError(Exception):
    pass


class MissingSubjectError(Exception):
    pass


class MissingTemplatePlaceholderError(Exception):
    pass


class RenderingError(Exception):
    pass
