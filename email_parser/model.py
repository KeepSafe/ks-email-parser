from collections import namedtuple
from enum import Enum
import string
import json


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
        attributes = dict(self.__dict__)
        if self._opt_attr:
            attributes.update(self._opt_attr)
        for k, v in attributes.items():
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


class BitmapPlaceholder(Placeholder):
    def __init__(self, name, bitmap_id, src, alt=None, is_global=False, variants=None, **opt_attr):
        self.name = name
        self.id = bitmap_id
        self.src = src
        self.alt = alt
        self.is_global = is_global
        self.type = PlaceholderType.bitmap
        self.variants = variants or {}
        self._opt_attr = opt_attr

    def get_content(self, variant=None):
        wrapper = string.Template("""<div class="bitmap-wrapper" style="$style">\n\t\t$img\n\t</div>""")
        img = string.Template("""<img id="$id" src="$src"$optional/>""")
        mapping = dict(self._opt_attr)
        optional = ""
        style = ""
        if self.alt:
            optional += " alt=\"{}\"".format(self.alt)
        for style_tag in ['max-width', 'max-height']:
            if style_tag in mapping:
                style += "{}: {};".format(style_tag, mapping[style_tag])
                del mapping[style_tag]
        mapping.update({
            'style': style,
            'id': self.id,
            'optional': optional,
            'src': self.src
        })
        mapping['img'] = img.substitute(mapping)
        final_wrapper = wrapper.substitute(mapping)
        return final_wrapper

    def set_attr(self, attr):
        self._opt_attr = attr


class MissingPatternParamError(Exception):
    pass


class MissingSubjectError(Exception):
    pass


class MissingTemplatePlaceholderError(Exception):
    pass


class RenderingError(Exception):
    pass
