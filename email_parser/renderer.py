"""
Different ways of rendering emails.
"""

import logging
import re
import xml.etree.ElementTree as ET

import bs4
import inlinestyler.utils as inline_styler
import markdown
import pystache

from . import markdown_ext, const, utils, config
from .model import *
from .reader import parse_placeholder

logger = logging.getLogger(__name__)


def _md_to_html(text, base_url=None):
    extensions = [markdown_ext.inline_text(), markdown_ext.no_tracking()]
    if base_url:
        extensions.append(markdown_ext.base_url(base_url))
    return markdown.markdown(text, extensions=extensions)


def _split_subject(placeholders):
    return (placeholders.get(const.SUBJECT_PLACEHOLDER),
            dict((k, v) for k, v in placeholders.items() if k != const.SUBJECT_PLACEHOLDER))


def _transform_extended_tags(content):
    regex = r"{{(.*):(.*):(.*)}}"
    return re.sub(regex, lambda match: '{{%s}}' % match.group(2), content)


class HtmlRenderer(object):
    """
    Renders email' body as html.
    """

    def __init__(self, template, email_locale):
        self.template = template
        self.locale = utils.normalize_locale(email_locale)

    def _inline_css(self, html, css):
        # an empty style will cause an error in inline_styler so we use a space instead
        css = css or ' '
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
        if self.locale in config.rtl_locales:
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

    def _wrap_with_highlight(self, html, highlight):
        attr_id = highlight.get('id', '')
        attr_style = highlight.get('style', '')

        soup = bs4.BeautifulSoup(html, 'html.parser')
        tag = soup.new_tag('div', id=attr_id, style=attr_style)
        tag.insert(0, soup)
        return tag.prettify()

    def _render_placeholder(self, placeholder, variant=None, highlight=None):
        content = placeholder.get_content(variant)
        if not content.strip():
            return content
        content = content.replace(const.LOCALE_PLACEHOLDER, self.locale)
        if placeholder.type == PlaceholderType.raw:
            return content
        else:
            html = _md_to_html(content, config.base_img_path)
            html = self._inline_css(html, self.template.styles)
            if highlight and highlight.get('placeholder') == placeholder.name and highlight.get('variant') == variant:
                html = self._wrap_with_highlight(html, highlight)
            return html

    def _concat_parts(self, subject, parts, variant):
        subject = subject.get_content(variant) if subject is not None else ''
        placeholders = dict(parts.items() | {'subject': subject, 'base_url': config.base_img_path}.items())
        try:
            # pystache escapes html by default, we pass escape option to disable this
            renderer = pystache.Renderer(escape=lambda u: u, missing_tags='strict')
            # since pystache tags parsing cant be easily extended: transform all tags extended with types to names only
            content = _transform_extended_tags(self.template.content)
            return renderer.render(content, placeholders)
        except pystache.context.KeyNotFoundError as e:
            message = 'template %s for locale %s has missing placeholders: %s' % (self.template.name, self.locale, e)
            raise MissingTemplatePlaceholderError(message) from e

    def render(self, placeholders, variant=None, highlight=None):
        subject, contents = _split_subject(placeholders)
        parts = {k: self._render_placeholder(v, variant, highlight) for k, v in contents.items()}
        html = self._concat_parts(subject, parts, variant)
        html = self._wrap_with_text_direction(html)
        return html


class TextRenderer(object):
    """
    Renders email's body as text.
    """

    def __init__(self, template, email_locale):
        # self.shortener = link_shortener.shortener(settings.shortener)
        self.template = template
        self.locale = utils.normalize_locale(email_locale)

    def _html_to_text(self, html):
        soup = bs4.BeautifulSoup(html, const.HTML_PARSER)

        # replace the value in <a> with the href because soup.get_text() takes the value inside <a> instead or href
        anchors = soup.find_all('a')
        for anchor in anchors:
            text = anchor.string or ''
            href = anchor.get('href') or text
            # href = self.shortener.shorten(href)
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

    def render(self, placeholders, variant=None):
        _, contents = _split_subject(placeholders)
        parts = [
            self._md_to_text(contents[p].get_content(variant).replace(const.LOCALE_PLACEHOLDER, self.locale))
            for p in self.template.placeholders if p in contents if contents[p].type != PlaceholderType.attribute]
        return const.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(v for v in filter(bool, parts))


class SubjectRenderer(object):
    """
    Renders email's subject as text.
    """

    def render(self, placeholders, variant=None):
        subject, _ = _split_subject(placeholders)
        if subject is None:
            raise MissingSubjectError('Subject is required for every email')
        return subject.get_content(variant)


def render(email_locale, template, placeholders, variant=None, highlight=None):
    subject_renderer = SubjectRenderer()
    subject = subject_renderer.render(placeholders, variant)

    text_renderer = TextRenderer(template, email_locale)
    text = text_renderer.render(placeholders, variant)

    html_renderer = HtmlRenderer(template, email_locale)
    try:
        html = html_renderer.render(placeholders, variant, highlight)
    except MissingTemplatePlaceholderError as e:
        message = 'failed to generate html content for locale: {} with message: {}'.format(email_locale, e)
        raise RenderingError(message) from e

    return subject, text, html
