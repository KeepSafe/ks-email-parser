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

from . import markdown_ext, errors, fs, link_shortener

TEXT_EMAIL_PLACEHOLDER_SEPARATOR = '\n\n'
HTML_PARSER = 'lxml'

def _md_to_html(text, base_url=None):
    extensions = [markdown_ext.inline_text()]
    if base_url:
        extensions.append(markdown_ext.base_url(base_url))
    return markdown.markdown(text, extensions=extensions)


def _split_subject(placeholders):
    return placeholders.get('subject'), OrderedDict((k, v) for k, v in placeholders.items() if k != 'subject')


class HtmlRenderer(object):

    """
    Renders email' body as html.
    """

    def __init__(self, template, settings, locale):
        self.template = template
        self.settings = settings
        self.locale = locale

    def _read_template(self):
        return fs.read_file(self.settings.templates, self.template.name)

    def _read_css(self):
        css = [fs.read_file(self.settings.templates, f) or ' ' for f in self.template.styles]
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
            if body is None:
                raise ValueError()
            body = body.text

        return body.strip()

    def _wrap_with_text_direction(self, html):
        if self.locale in self.settings.right_to_left:
            soup = bs4.BeautifulSoup(html, 'html.parser')
            for element in soup.contents:
                try:
                    element['dir'] = 'rtl'
                    break
                except TypeError:
                    continue
            return soup.prettify()
        else:
            return html

    def _render_placeholder(self, placeholder, css):
        if not placeholder.strip():
            return placeholder
        html = _md_to_html(placeholder, self.settings.images)
        return self._inline_css(html, css)

    def _concat_parts(self, subject, parts):
        html = self._read_template()
        strict = 'strict' if self.settings.strict else 'ignore'
        # pystache escapes html by default, we pass escape option to disable this
        renderer = pystache.Renderer(escape=lambda u: u, missing_tags=strict)
        try:
            # add subject for rendering as we have it in html
            return renderer.render(
                html, dict(parts.items() | {'subject': subject}.items() | {'base_url': self.settings.images}.items()))
        except pystache.context.KeyNotFoundError as e:
            message = 'template {} for locale {} has missing placeholders: {}'.format(
                self.template.name, self.locale, e)
            raise errors.MissingTemplatePlaceholderError(message) from e

    def render(self, placeholders):
        subject, contents = _split_subject(placeholders)
        css = self._read_css()
        parts = {k: self._render_placeholder(v, css) for k, v in contents.items()}
        html = self._concat_parts(subject, parts)
        html = self._wrap_with_text_direction(html)
        return html


class TextRenderer(object):

    """
    Renders email's body as text.
    """

    def __init__(self, ignored_plceholder_names, shortener_config=None):
        self.ignored_plceholder_names = ignored_plceholder_names
        self.shortener = link_shortener.shortener(shortener_config)

    def _html_to_text(self, html):
        soup = bs4.BeautifulSoup(html, HTML_PARSER)

        # replace the value in <a> with the href because soup.get_text() takes the value inside <a> instead or href
        anchors = soup.find_all('a')
        for anchor in anchors:
            text = anchor.string or ''
            href = anchor.get('href') or text
            href = self.shortener.shorten(href)
            if href != text:
                anchor.replace_with('{} ({})'.format(text, href))
            elif href:
                anchor.replace_with(href)

        # add prefix to lists, it wont be added automatically
        unordered_lists = soup('ul')
        for unordered_list in unordered_lists:
            for element in unordered_list('li'):
                if element.string:
                    element.replace_with('- ' + element.string)
        ordered_lists = soup('ol')
        for ordered_list in ordered_lists:
            for idx, element in enumerate(ordered_list('li')):
                element.replace_with('%s. %s' % (idx + 1, element.string))

        return soup.get_text()

    def _md_to_text(self, text, base_url=None):
        html = _md_to_html(text, base_url)
        return self._html_to_text(html)

    def render(self, placeholders):
        _, contents = _split_subject(placeholders)
        parts = [self._md_to_text(v) for k, v in contents.items() if k not in self.ignored_plceholder_names]
        return TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(v for v in filter(bool, parts))


class SubjectRenderer(object):

    """
    Renders email's subject as text.
    """

    def render(self, placeholders):
        subject, _ = _split_subject(placeholders)
        if subject is None:
            raise errors.MissingSubjectError('Subject is required for every email')
        return subject


def render(email, template, placeholders, ignored_plceholder_names, settings):
    subject_renderer = SubjectRenderer()
    subject = subject_renderer.render(placeholders)

    text_renderer = TextRenderer(ignored_plceholder_names, settings.shortener)
    text = text_renderer.render(placeholders)

    html_renderer = HtmlRenderer(template, settings, email.locale)
    try:
        html = html_renderer.render(placeholders)
    except errors.MissingTemplatePlaceholderError as e:
        raise errors.RenderingError(
            'failed to generate html content for {} with message: {}'.format(email.full_path, e)) from e

    return subject, text, html
