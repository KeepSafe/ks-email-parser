from collections import namedtuple

Settings = namedtuple('Settings', [
    'source', 'destination', 'templates', 'images', 'pattern', 'right_to_left', 'strict', 'force', 'verbose',
    'exclusive', 'default_locale', 'local_images', 'workers_pool', 'shortener', 'save', 'cms_service_host'
])
Email = namedtuple('Email', ['name', 'locale', 'path', 'full_path'])
Template = namedtuple('Template', ['name', 'styles', 'content', 'placeholders'])
Placeholders = namedtuple('Placeholders', ['local', 'general', 'ignored'])


class MissingPatternParamError(Exception):
    pass


class MissingSubjectError(Exception):
    pass


class MissingTemplatePlaceholderError(Exception):
    pass


class RenderingError(Exception):
    pass


def default_settings():
    return Settings(
        verbose=False,
        strict=True,
        force=False,
        source='src',
        destination='target',
        templates='templates_html',
        images='http://www.getkeepsafe.com/emails/img',
        right_to_left=['ar', 'he'],
        pattern='{locale}/{name}.xml',
        shortener={},
        exclusive=None,
        default_locale='en',
        workers_pool=10,
        local_images='templates_html/img',
        save=None,
        cms_service_host="http://localhost:5000")
