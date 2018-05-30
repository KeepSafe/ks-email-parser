from collections import namedtuple
from enum import Enum
import json


class MetaPlaceholderType(Enum):
    text = 'text'
    image = 'image'


class PlaceholderType(Enum):
    attribute = 'attribute'
    raw = 'raw'
    text = 'text'
    image = 'image'
    bitmap = 'bitmap'


class EmailType(Enum):
    marketing = 'marketing'
    transactional = 'transactional'


Email = namedtuple('Email', ['name', 'locale', 'path'])
Template = namedtuple('Template', ['name', 'styles_names', 'styles', 'content', 'placeholders', 'type'])


class MetaPlaceholder:
    def __init__(self, name, my_type=PlaceholderType.text, attributes=None):
        self.name = name
        self.type = my_type
        self.attributes = attributes

    def __getstate__(self):
        state = dict(self.__dict__)
        state['type'] = state['type'].value
        return state

    def __eq__(self, other):
        try:
            my_state = self.__getstate__()
            other_state = other.__getstate__()
            return my_state == other_state
        except Exception:
            return False


class Placeholder:
    def __init__(self, name, content, is_global=False, p_type=PlaceholderType.text, variants=None, opt_attr=None):
        self.name = name
        self.is_global = is_global
        self.type = p_type
        self._content = content
        self.variants = variants or {}
        self._opt_attr = opt_attr

    def __iter__(self):
        attributes = self.__dict__.items()
        if self._opt_attr:
            attributes.update(self._opt_attr)
        for k, v in attributes:
            if k is 'type':
                yield k, self.type.value
            elif k is '_content':
                yield 'content', v
            elif k is '_opt_attr':
                continue
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


class ModelJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, MetaPlaceholder):
            as_dict = o.__getstate__()
            return as_dict
        return super().default(o)


class MissingPatternParamError(Exception):
    pass


class MissingSubjectError(Exception):
    pass


class MissingTemplatePlaceholderError(Exception):
    pass


class RenderingError(Exception):
    pass
