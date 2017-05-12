from . import cmd, placeholder, fs, reader, renderer
"""
Making a library out of a command line tool... not being proud of myself
"""


def _update_settings(settings=None):
    settings = settings or {}
    default_settings = cmd.default_settings()._asdict()
    default_settings.update(settings)
    return cmd.Settings(**default_settings)


def get_email(settings, locale, email_name):
    settings = _update_settings(settings)
    email = fs.master_email(settings.source, settings.pattern, email_name, locale, True)
    if not email:
        return None
    if not placeholder.validate_email(settings, email) and not settings.force:
        return None
    template, _, _ = reader.read(email, settings)
    return template.content


def parse_email(settings, locale, email_name):
    settings = _update_settings(settings)
    email = fs.master_email(settings.source, settings.pattern, email_name, locale, True)
    if not email:
        return None
    if not placeholder.validate_email(settings, email) and not settings.force:
        return None
    link_locale_mappings = reader.read_link_locale_mappings(settings)
    if not link_locale_mappings and not settings.force:
        return None

    template, placeholders, ignored_placeholder_names = reader.read(email, settings)
    if template:
        return renderer.render(email, template, placeholders, ignored_placeholder_names, link_locale_mappings, settings)


def get_template(settings, locale, template_name):
    settings = _update_settings(settings)
    email = fs.master_email(settings.source, settings.pattern, template_name, locale, True)
    return fs.read_file(email.full_path)


def delete_template(settings, template_name):
    settings = _update_settings(settings)
    emails = fs.master_email(settings.source, settings.pattern, template_name, None, True)
    files = []
    for email in emails:
        files.append(email.full_path)
        fs.delete_file(email.full_path)
    placeholder.generate_config(settings)
    return files


def save_template(settings, locale, template_name, template):
    settings = _update_settings(settings)
    path = fs.resolve_path(settings.source, settings.pattern, locale, template_name)
    fs.save_file(template, path)
    placeholder.generate_config(settings)
    if placeholder.validate_email_content(locale, template_name, template, settings.source):
        return path


def get_email_names(settings):
    settings = _update_settings(settings)
    return (email.name for email in fs.emails(settings.source, settings.pattern, settings.exclusive))


def get_email_placeholders(settings):
    settings = _update_settings(settings)
    names = (email.name for email in fs.emails(settings.source, settings.pattern, settings.exclusive))
    return {name: placeholder.from_email_name(name, settings.source) for name in names}


def save_email_placeholders(settings, placeholders):
    settings = _update_settings(settings)
    placeholder.generate_config(settings)
    placeholder._read_placeholders_file.cache_clear()


def placeholders_filepath(settings):
    return fs.path(settings.source, placeholder.PLACEHOLDERS_FILENAME)
