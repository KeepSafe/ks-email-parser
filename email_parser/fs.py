import logging
import os
import parse
from pathlib import Path
from string import Formatter
from collections import namedtuple

from . import errors, consts

Email = namedtuple('Email', ['name', 'locale', 'path', 'full_path'])


def _parse_params(pattern):
    params = [p for p in map(lambda e: e[1], Formatter().parse(pattern)) if p]
    if 'name' not in params:
        raise errors.MissingPatternParamError(
            '{{name}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    if 'locale' not in params:
        raise errors.MissingPatternParamError(
            '{{name}} is a required parameter in the pattern but it is not present in {}'.format(pattern))
    return params


def emails(src_dir, pattern):
    params = _parse_params(pattern)

    wildcard_params = {k: '*' for k in params}
    wildcard_pattern = pattern.format(**wildcard_params)
    parser = parse.compile(pattern)

    for path in Path(src_dir).glob(wildcard_pattern):
        if not path.is_dir():
            str_path = str(path.relative_to(src_dir))
            result = parser.parse(str_path)
            result.named['path'] = str_path
            result.named['full_path'] = str(path.resolve())
            yield Email(**result.named)


def read_file(*path_parts):
    path = os.path.join(*path_parts)
    with open(path) as fp:
        return fp.read()

def save_file(content, *path_parts):
    path = os.path.join(*path_parts)
    with open(path, 'w') as fp:
        return fp.write(content)


def save(email, subject, text, html, dest_dir):
    os.makedirs(os.path.join(dest_dir, email.locale), exist_ok=True)
    save_file(subject, dest_dir, email.locale, email.name + consts.SUBJECT_EXTENSION)
    save_file(text, dest_dir, email.locale, email.name + consts.TEXT_EXTENSION)
    save_file(html, dest_dir, email.locale, email.name + consts.HTML_EXTENSION)


def list_locales(src_dir):
    logging.debug('reading locales from %s', src_dir)
    return [locale for locale in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, locale))]


def list_emails(src_dir, locale, rtl_codes):
    emails_path = os.path.join(src_dir, locale)
    logging.debug('reading emails from %s', emails_path)
    emails = [email for email in os.listdir(emails_path) if os.path.isfile(
        os.path.join(emails_path, email)) and email.endswith(EMAIL_EXTENSION)]
    return [Email.from_xml(emails_path, email, locale, rtl_codes) for email in emails]


def read_css(email, templates_dir):
    css = []
    if email.css:
        for style in email.css:
            style_path = os.path.join(templates_dir, style)
            with open(style_path) as style_file:
                css.append(style_file.read())
    return css


def save_email_subject(dest_dir, email):
    email_path = os.path.join(dest_dir, email.name + SUBJECT_EXTENSION)
    logging.debug('Saving email subject to %s', email_path)
    with open(email_path, 'w') as email_file:
        email_file.write(email.subject)


def save_email_content_as_text(dest_dir, email, images_dir):
    email_path = os.path.join(dest_dir, email.name + TEXT_EXTENSION)
    logging.debug('Saving email as text to %s', email_path)
    with open(email_path, 'w') as email_file:
        content_text = email.content_to_text(images_dir)
        for content_key, _ in email.order:
            email_file.write(content_text[content_key])
            # End with new paragraph start in case we have more to write
            email_file.write('\n\n')


def save_email_content_as_html(dest_dir, templates_dir, email, images_dir, strict):
    email_path = os.path.join(dest_dir, email.name + HTML_EXTENSION)
    template_path = os.path.join(templates_dir, email.template)
    with open(email_path, 'w') as email_file, open(template_path) as template_file:
        logging.debug('Saving email as html to %s using template %s', email_path, template_path)
        template = template_file.read()
        css = read_css(email, templates_dir)
        email_html = email.to_html(template, css, images_dir, strict)
        email_file.write(email_html)
