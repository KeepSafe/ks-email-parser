"""
Different ways of rendering emails.
"""

import logging
import markdown
import bs4
import pystache
import inlinestyler.utils as inline_styler
import xml.etree.ElementTree as ET
from collections import OrderedDict

from . import markdown_ext, const, utils, config
from .model import *

logger = logging.getLogger(__name__)


def _md_to_html(text, base_url=None):
    extensions = [markdown_ext.inline_text()]
    if base_url:
        extensions.append(markdown_ext.base_url(base_url))
    return markdown.markdown(text, extensions=extensions)


def _split_subjects(placeholders):
    return ([placeholders.get(subject) for subject in const.SUBJECTS_PLACEHOLDERS], OrderedDict(
        (k, v) for k, v in placeholders.items() if k not in const.SUBJECTS_PLACEHOLDERS))


class HtmlRenderer(object):
    """
    Renders email' body as html.
    """

    def __init__(self, template, email):
        self.template = template
        self.locale = utils.normalize_locale(email.locale)

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

    def _render_placeholder(self, placeholder):
        if not placeholder.content.strip():
            return placeholder
        content = placeholder.content.replace(const.LOCALE_PLACEHOLDER, self.locale)
        html = _md_to_html(content, config.base_img_path)
        return self._inline_css(html, self.template.styles)

    def _concat_parts(self, subject, parts):
        subject = subject[0].content if subject[0] is not None else ''
        placeholders = dict(parts.items() | {'subject': subject, 'base_url': config.base_img_path}.items())
        try:
            # pystache escapes html by default, we pass escape option to disable this
            renderer = pystache.Renderer(escape=lambda u: u, missing_tags='strict')
            # add subject for rendering as we have it in html
            return renderer.render(self.template.content, placeholders)
        except pystache.context.KeyNotFoundError as e:
            message = 'template %s for locale %s has missing placeholders: %s' % (self.template.name, self.locale, e)
            raise MissingTemplatePlaceholderError(message) from e

    def render(self, placeholders):
        subjects, contents = _split_subjects(placeholders)
        parts = {k: self._render_placeholder(v) for k, v in contents.items()}
        html = self._concat_parts(subjects, parts)
        html = self._wrap_with_text_direction(html)
        return html


class TextRenderer(object):
    """
    Renders email's body as text.
    """

    def __init__(self, template, email):
        # self.shortener = link_shortener.shortener(settings.shortener)
        self.template = template
        self.locale = utils.normalize_locale(email.locale)

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

    def render(self, placeholders):
        _, contents = _split_subjects(placeholders)
        parts = [
            self._md_to_text(contents[p].content.replace(const.LOCALE_PLACEHOLDER, self.locale))
            for p in self.template.placeholders if p in contents and contents[p].is_text
        ]
        return const.TEXT_EMAIL_PLACEHOLDER_SEPARATOR.join(v for v in filter(bool, parts))


class SubjectRenderer(object):
    """
    Renders email's subject as text.
    """

    def render(self, placeholders):
        subjects, _ = _split_subjects(placeholders)
        if subjects[0] is None:
            raise MissingSubjectError('Subject is required for every email')
        return list(map(lambda s: s.content if s else None, subjects))


def render(email, template, placeholders):
    subject_renderer = SubjectRenderer()
    subjects = subject_renderer.render(placeholders)

    text_renderer = TextRenderer(template, email)
    text = text_renderer.render(placeholders)

    html_renderer = HtmlRenderer(template, email)
    try:
        html = html_renderer.render(placeholders)
    except MissingTemplatePlaceholderError as e:
        raise RenderingError('failed to generate html content for {} with message: {}'.format(email.path, e)) from e

    return subjects, text, html
