"""
Different ways of rendering emails.
"""

import markdown
import bs4
import pystache
import logging
import inlinestyler.utils as inline_styler
import xml.etree.ElementTree as ET
from collections import OrderedDict

from . import markdown_ext, consts, errors, fs


def _md_to_html(text, base_url=None):
    extensions = [markdown_ext.inline_text()]
    if base_url:
        extensions.append(markdown_ext.base_url(base_url))
    return markdown.markdown(text, extensions=extensions)


def _html_to_text(html):
    soup = bs4.BeautifulSoup(html)

    # replace the value in <a> with the href because soup.get_text() takes the value inside <a> instead or href
    anchors = soup.find_all('a')
    for anchor in anchors:
        text = anchor.string or ''
        href = anchor.get('href') or text
        if href != text:
            anchor.replace_with('{} {}'.format(text, href))
        elif href:
            anchor.replace_with(href)

    return soup.get_text()


def _md_to_text(text, base_url=None):
    html = _md_to_html(text, base_url)
    return _html_to_text(html)


def _split_subject(placeholders):
    return placeholders.get('subject'), OrderedDict((k, v) for k, v in placeholders.items() if k != 'subject')


class HtmlRenderer(object):
    """
    Renders email' body as html.
    """

    def __init__(self, template, options, locale):
        self.template = template
        self.options = options
        self.locale = locale

    def _read_template(self):
        return fs.read_file(self.options[consts.OPT_TEMPLATES], self.template.name)

    def _read_css(self):
        css = [fs.read_file(self.options[consts.OPT_TEMPLATES], f) or ' ' for f in self.template.styles]
        return ''.join(['<style>{}</style>'.format(c) for c in css])

    def _inline_css(self, html, css):
        if not self.template.styles:
            return html

        # an empty style will cause an error in inline_styler so we use a space instead
        html_with_css = inline_styler.inline_css(css + html)

        # inline_styler will return a complete html filling missing html and body tags which we don't want
        if html.startswith('<'):
            body = ET.fromstring(html_with_css).find('.//body')
            body = ''.join(ET.tostring(e, encoding='unicode') for e in body)
        else:
            body = ET.fromstring(html_with_css).find('.//body/p')
            body = body.text

        return body.strip()

    def _wrap_with_text_direction(self, html):
        return '<div dir="rtl">\n' + html + '\n</div>'

    def _render_placeholder(self, placeholder, css):
        html = _md_to_html(placeholder, self.options[consts.OPT_IMAGES])
        if self.locale in self.options[consts.OPT_RIGHT_TO_LEFT]:
            html = self._wrap_with_text_direction(html)
        return self._inline_css(html, css)

    def _concat_parts(self, subject, parts):
        html = self._read_template()
        strict = 'strict' if self.options[consts.OPT_STRICT] else 'ignore'
        # pystache escapes html by default, pass escape option to disable this
        renderer = pystache.Renderer(escape=lambda u: u, missing_tags=strict)
        try:
            # add subject for rendering as we have it in html
            return renderer.render(html, dict(parts.items() | {'subject': subject}.items() | {'base_url': self.options[consts.OPT_IMAGES]}.items()))
        except pystache.context.KeyNotFoundError as e:
            message = 'template {} for locale {} has missing placeholders: {}'.format(self.template.name, self.locale, e)
            raise errors.MissingTemplatePlaceholderError(message) from e


    def render(self, placeholders):
        subject, contents = _split_subject(placeholders)
        css = self._read_css()
        parts = {k: self._render_placeholder(v, css) for k, v in contents.items()}
        return self._concat_parts(subject, parts)



class TextRenderer(object):
    """
    Renders email' body as text.
    """

    def __init__(self, ignored_plceholder_names):
        self.ignored_plceholder_names = ignored_plceholder_names

    def render(self, placeholders):
        _, contents = _split_subject(placeholders)
        parts = [_md_to_text(v) for k, v in contents.items() if k not in self.ignored_plceholder_names]
        return consts.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(_md_to_text(v) for v in filter(bool, parts))


class SubjectRenderer(object):
    """
    Renders email's subject as text.
    """

    def render(self, placeholders):
        subject, _ = _split_subject(placeholders)
        if subject is None:
            raise errors.MissingSubjectError('Subject is required for every email')
        return subject


def render(email, template, placeholders, ignored_plceholder_names, options):
    subject_renderer = SubjectRenderer()
    subject = subject_renderer.render(placeholders)

    text_renderer = TextRenderer(ignored_plceholder_names)
    text = text_renderer.render(placeholders)

    html_renderer = HtmlRenderer(template, options, email.locale)
    try:
        html = html_renderer.render(placeholders)
    except errors.MissingTemplatePlaceholderError as e:
        raise errors.RenderingError('failed to generate html content for {} with message: {}'.format(email.full_path, e)) from e

    return subject, text, html
