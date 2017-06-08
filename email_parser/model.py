from collections import namedtuple

Email = namedtuple('Email', ['name', 'locale', 'path'])
Template = namedtuple('Template', ['name', 'styles', 'content', 'placeholders'])
Placeholder = namedtuple('Placeholder', ['name', 'content', 'is_text'])
Placeholder.__new__.__defaults__ = (True, )


class MissingPatternParamError(Exception):
    pass


class MissingSubjectError(Exception):
    pass


class MissingTemplatePlaceholderError(Exception):
    pass


class RenderingError(Exception):
    pass
