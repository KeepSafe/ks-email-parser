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

    def get_email_type(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        return reader.get_email_type(self.root_path, email)

    def render(self, email_name, locale, variant=None):
        email = fs.email(self.root_path, email_name, locale)
        return self.render_email(email, variant)

    def render_email(self, email, variant=None):
        if not email:
            return None
        template, persisted_placeholders = reader.read(self.root_path, email)
        if template:
            return renderer.render(email.locale, template, persisted_placeholders, variant)

    def render_email_content(self, content, locale=const.DEFAULT_LOCALE, variant=None, highlight=None):
        template, persisted_placeholders = reader.read_from_content(self.root_path, content, locale)
        return renderer.render(locale, template, persisted_placeholders, variant=variant, highlight=highlight)

    def get_email(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        return fs.read_file(email.path)

    def original(self, email_name, locale, variant=None):
        email = fs.email(self.root_path, email_name, locale)
        if not email:
            return None
        template, placeholders = reader.read(self.root_path, email)
        return '\n\n'.join([placeholders[name].get_content() for name in template.placeholders if
                            placeholders[name].type == PlaceholderType.text])

    def get_email_components(self, email_name, locale):
        email = fs.email(self.root_path, email_name, locale)
        template, placeholders = reader.read(self.root_path, email)
        serialized_placeholders = {name: dict(placeholder) for name, placeholder in placeholders.items()}
        return template.name, template.type, template.styles_names, serialized_placeholders

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

    def save_email_variant_as_default(self, email_name, locales, variant, email_type=None):
        paths = []
        for locale in locales:
            email = fs.email(self.root_path, email_name, locale)
            template, placeholders = reader.read(self.root_path, email)
            placeholders_list = [p.pick_variant(variant) for _, p in placeholders.items() if not p.is_global]
            if email_type:
                email_type = EmailType(email_type)
            elif template.type:
                email_type = EmailType(template.type)
            content = reader.create_email_content(self.root_path, template.name, template.styles_names,
                                                  placeholders_list, email_type)
            email_path = fs.save_email(self.root_path, content, email_name, locale)
            paths.append(email_path)
        return paths

    def create_email_content(self, template_name, styles_names, placeholders, email_type):
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
        email_type = EmailType(email_type)
        return reader.create_email_content(self.root_path, template_name, styles_names, placeholder_list, email_type)

    def render_template_content(self, template_content, styles_names, placeholders, locale=const.DEFAULT_LOCALE):
        styles = reader.get_inline_style(self.root_path, styles_names)
        placeholders_objs = {name: Placeholder(name, content) for name, content in placeholders.items()}
        template = Template('preview', styles_names, styles, template_content, placeholders_objs, None)
        return renderer.render(locale, template, placeholders_objs)

    def get_email_names(self):
        return (email.name for email in fs.emails(self.root_path, locale=const.DEFAULT_LOCALE))

    def get_emails(self, locale=const.DEFAULT_LOCALE):
        return (email._asdict() for email in fs.emails(self.root_path, locale=locale))

    def get_email_placeholders(self):
        expected_placeholders = placeholder.expected_placeholders_file(self.root_path)
        return {k: list(v) for k, v in expected_placeholders.items()}

    def get_template(self, template_filename, template_type=None):
        try:
            template_type = EmailType(template_type)
        except ValueError:
            template_type = None
        content, placeholders = reader.get_template_parts(self.root_path, template_filename, template_type)
        return content, placeholders

    def save_template(self, template_filename, template_type, template_content):
        template_type = EmailType(template_type)
        return fs.save_template(self.root_path, template_filename, template_type, template_content)

    def refresh_email_placeholders_config(self):
        placeholders_config = placeholder.generate_config(self.root_path)
        if placeholders_config:
            fs.save_file(
                json.dumps(placeholders_config, sort_keys=True, indent=const.JSON_INDENT),
                self.get_placeholders_filepath())
            placeholder.expected_placeholders_file.cache_clear()

    def get_placeholders_filepath(self):
        return os.path.join(self.root_path, const.REPO_SRC_PATH, const.PLACEHOLDERS_FILENAME)

    def get_templates_directory_filepath(self):
        return os.path.join(self.root_path, config.paths.templates)

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
        sections_map = fs.get_html_sections_map(self.root_path)
        for template_type in templates:
            types_templates = templates[template_type]
            templates_view_type = templates_view.setdefault(template_type, {})
            for template_name in types_templates:
                tpl_content, tpl_placeholders = self.get_template(template_name, template_type)
                templates_view_type[template_name] = tpl_placeholders
        return templates_view, styles, sections_map

    def get_global_placeholders_map(self, locale=const.DEFAULT_LOCALE):
        global_placeholders = reader.get_global_placeholders(self.root_path, locale)
        return {name: placeholder.get_content() for name, placeholder in global_placeholders.items()}
