"""
    email_parser
    ~~~~~~~~~~

    Parses emails from a source directory and outputs text and html format.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""
import json
import os

from . import placeholder, fs, reader, renderer, const, config
from .model import *


class Parser:
    def __init__(self, root_path, **kwargs):
        self.root_path = root_path
        config.init(**kwargs)

    def __hash__(self):
        return hash(self.root_path)

    def __eq__(self, other):
        """
        since parser is just wrapper it means essentially that parsers are equal if they work on the same root_path
        sorting this out is needed for caching
        """
        return self.__hash__() == hash(other)

    def get_template_for_email(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        if not email:
            return None
        template, _ = reader.read(self.root_path, email)
        return template.content

    def render(self, email_name, locale, variant=None):
        email = fs.email(self.root_path, email_name, locale)
        return self.render_email(email, variant)

    def render_email(self, email, variant=None):
        if not email:
            return None
        template, persisted_placeholders = reader.read(self.root_path, email)
        if template:
            return renderer.render(email.locale, template, persisted_placeholders, variant)

    def render_email_content(self, content, locale=const.DEFAULT_LOCALE, variant=None):
        template, persisted_placeholders = reader.read_from_content(self.root_path, content, locale)
        return renderer.render(locale, template, persisted_placeholders, variant=None)

    def get_email(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        return fs.read_file(email.path)

    def get_email_components(self, email_name, locale):
        serialized_placeholders = {}
        email = fs.email(self.root_path, email_name, locale)
        template, placeholders = reader.read(self.root_path, email)
        serialized_placeholders = {name: dict(placeholder) for name, placeholder in placeholders.items()}
        return template.name, template.styles_names, serialized_placeholders

    def get_email_variants(self, email_name):
        email = fs.email(self.root_path, email_name, const.DEFAULT_LOCALE)
        _, placeholders = reader.read(self.root_path, email)
        variants = set([name for _, p in placeholders.items() for name in p.variants.keys()])
        return list(variants)

    def delete_email(self, email_name):
        emails = fs.emails(self.root_path, email_name=email_name)
        files = []
        for email in emails:
            files.append(email.path)
            fs.delete_file(email.path)
        self.refresh_email_placeholders_config()
        return files

    def save_email(self, email_name, locale, content):
        saved_path = fs.save_email(self.root_path, content, email_name, locale)
        self.refresh_email_placeholders_config()
        return saved_path

    def create_email_content(self, template_name, styles_names, placeholders):
        placeholder_list = []
        for placeholder_name, placeholder_props in placeholders.items():
            if not placeholder_props.get('is_global', False):
                is_global = placeholder_props.get('is_global', False)
                content = placeholder_props['content']
                variants = placeholder_props.get('variants', {})
                pt = placeholder_props.get('type', PlaceholderType.text.value)
                pt = PlaceholderType[pt]
                p = Placeholder(placeholder_name, content, is_global, pt, variants)
                placeholder_list.append(p)
        placeholder_list.sort(key=lambda item: item.name)
        return reader.create_email_content(template_name, styles_names, placeholder_list)

    def get_email_names(self):
        return (email.name for email in fs.emails(self.root_path, locale=const.DEFAULT_LOCALE))

    def get_emails(self, locale=const.DEFAULT_LOCALE):
        return (email._asdict() for email in fs.emails(self.root_path, locale=locale))

    def get_email_placeholders(self):
        expected_placeholders = placeholder.expected_placeholders_file(self.root_path)
        return {k: list(v) for k, v in expected_placeholders.items()}

    def get_template_placeholders(self, template_filename):
        _, placeholders = reader.get_template_parts(self.root_path, template_filename)
        return placeholders

    def refresh_email_placeholders_config(self):
        placeholders_config = placeholder.generate_config(self.root_path)
        if placeholders_config:
            fs.save_file(
                json.dumps(placeholders_config, sort_keys=True, indent=const.JSON_INDENT),
                self.get_placeholders_filepath())
            placeholder.expected_placeholders_file.cache_clear()

    def get_placeholders_filepath(self):
        return os.path.join(self.root_path, const.REPO_SRC_PATH, const.PLACEHOLDERS_FILENAME)

    def get_email_filepaths(self, email_name, locale=None):
        """
        return list of file paths for single email or collection of emails if locale = None
        :param email_name:
        :param locale:
        :return:
        """
        emails = fs.emails(self.root_path, email_name, locale)
        abs_paths = map(lambda email: fs.get_email_filepath(self.root_path, email.name, email.locale), emails)
        return list(abs_paths)

    def get_email_placeholders_validation_errors(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        return placeholder.get_email_validation(self.root_path, email)['errors']

    def get_resources(self):
        templates_view = {}
        templates, styles = fs.resources(self.root_path)
        for template_name in templates:
            templates_view[template_name] = self.get_template_placeholders(template_name)
        return templates_view, styles
