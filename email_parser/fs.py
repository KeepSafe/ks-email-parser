import logging
import os

EMAIL_EXTENSION = '.xml'


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
