"""
    email_parser
    ~~~~~~~~~~

    Parses emails from a source directory and outputs text and html format.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""
import json

from . import placeholder, fs, reader, renderer, const
from .model import *


class Parser:
    def __init__(self, root_path, **kwargs):
        self.root_path = root_path
        config.init(**kwargs)

    def get_template_for_email(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        if not email:
            return None
        template, _ = reader.read(self.root_path, email)
        return template.content

    def delete_template(self, email_name, locale):
        fs.delete_file(self.root_path, locale, email_name + const.SOURCE_EXTENSION)

    def render(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        if not email:
            return None
        template, placeholders = reader.read(self.root_path, email)
        if template:
            return renderer.render(email.locale, template, placeholders)

    def render_email(self, email):
        if not email:
            return None
        template, placeholders = reader.read(self.root_path, email)
        if template:
            return renderer.render(email.locale, template, placeholders)

    def get_email(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        return fs.read_file(email.path)

    def delete_email(self, email_name):
        emails = fs.emails(self.root_path, email_name=email_name)
        files = []
        for email in emails:
            files.append(email.path)
            fs.delete_file(email.path)
        self.refresh_email_placeholders_config()
        return files

    def save_email(self, email_name, locale, template):
        fs.save_email(self.root_path, template, email_name, locale)
        self.refresh_email_placeholders_config()

    def get_email_names(self):
        return (email.name for email in fs.emails(self.root_path, locale=const.DEFAULT_LOCALE))

    def get_email_placeholders(self):
        expected_placeholders = placeholder.expected_placeholders_file(self.root_path)
        return {k: list(v) for k, v in expected_placeholders.items()}

    def get_placeholders_for_email(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        if not email:
            return None
        template, placeholders = reader.read(self.root_path, email)
        return placeholders

    def refresh_email_placeholders_config(self):
        placeholders_config = placeholder.generate_config(self.root_path)
        if placeholders_config:
            fs.save_file(
                json.dumps(placeholders_config, sort_keys=True, indent=const.JSON_INDENT), self.root_path,
                const.PLACEHOLDERS_FILENAME)
            placeholder.expected_placeholders_file.cache_clear()
