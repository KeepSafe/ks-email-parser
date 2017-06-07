"""
    email_parser
    ~~~~~~~~~~

    Parses emails from a source directory and outputs text and html format.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""

from . import placeholder, fs, reader, renderer
from .model import *


class Parser:
    def __init__(self, settings=None):
        settings = settings or {}
        dsettings = default_settings()._asdict()
        dsettings.update(settings)
        self._settings = Settings(**dsettings)

    def get_email(self, locale, email_name):
        email = fs.email(self._settings.source, self._settings.pattern, email_name, locale, True)
        if not email:
            return None
        if not placeholder.validate_email(self._settings, email) and not settings.force:
            return None
        template, _, _ = reader.read(email, self._settings)
        return template.content

    def parse_email(self, locale, email_name):
        email = fs.email(self._settings.source, self._settings.pattern, email_name, locale, True)
        if not email:
            return None
        if not placeholder.validate_email(self._settings, email) and not self._settings.force:
            return None

        template, placeholders, ignored_placeholder_names = reader.read(email, self._settings)
        if template:
            return renderer.render(email, template, placeholders, ignored_placeholder_names, self._settings)

    def get_template(self, locale, template_name):
        email = fs.email(self._settings.source, self._settings.pattern, template_name, locale, True)
        return fs.read_file(email.full_path)

    def delete_template(self, template_name):
        emails = fs.email(self._settings.source, self._settings.pattern, template_name, None, True)
        files = []
        for email in emails:
            files.append(email.full_path)
            fs.delete_file(email.full_path)
        placeholder.generate_config(settings)
        return files

    def save_template(self, locale, template_name, template):
        path = fs.resolve_path(self._settings.source, self._settings.pattern, locale, template_name)
        fs.save_file(template, path)
        placeholder.generate_config(self._settings)
        return path

    def get_email_names(self):
        return (email.name
                for email in fs.emails(self._settings.source, self._settings.pattern, self._settings.exclusive))

    def get_email_placeholders(self):
        names = (email.name
                 for email in fs.emails(self._settings.source, self._settings.pattern, self._settings.exclusive))
        return {name: placeholder.from_email_name(name, self._settings.source) for name in names}

    def save_email_placeholders(self, placeholders):
        placeholder.generate_config(self._settings)
        placeholder._read_placeholders_file.cache_clear()

    def placeholders_filepath(self):
        return fs.path(self._settings.source, placeholder.PLACEHOLDERS_FILENAME)
