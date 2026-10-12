from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from markdown.inlinepatterns import (
    IMAGE_LINK_RE,
    LINK_RE,
    ImageInlineProcessor,
    LinkInlineProcessor,
    SimpleTagInlineProcessor,
)
import re

from . import const


MUSTACHE_ENCODED_SPACES_RE = re.compile(r'{{%20([^{}]+?)%20}}', re.IGNORECASE)
BIDI_URL_PREFIX_RE = re.compile(r'^(?:(?:%E2%80%8[EF])|[\u200e\u200f])+', re.IGNORECASE)
BIDI_URL_SUFFIX_RE = re.compile(r'(?:(?:%E2%80%8[EF])|[\u200e\u200f])+$', re.IGNORECASE)
LEGACY_STRONG_RE = r'(\*{2})(.+?)\1'


def _strip_bidi_url_wrappers(url):
    url = BIDI_URL_PREFIX_RE.sub('', url)
    return BIDI_URL_SUFFIX_RE.sub('', url)


class InlineBlockProcessor(BlockProcessor):
    """
    Inlines the content instead of parsing it as markdown.
    """
    RE = re.compile(const.INLINE_TEXT_PATTERN)

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.match(block)
        if m:
            text = m.group(1)
            parent.text = text


class BaseUrlImageProcessor(ImageInlineProcessor):
    """
    Adds base url to images which have relative path.
    """

    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE)

    def __init__(self, pattern, md, images_dir):
        super().__init__(pattern, md)
        if images_dir:
            self.images_dir = images_dir.strip('/')
        else:
            self.images_dir = ''

    def _is_url(self, text):
        url = text.strip().strip('/').split(' ')[0]
        return self.url_pattern.match(url)

    def handleMatch(self, m, data):
        el, start, end = super().handleMatch(m, data)
        if el is None:
            return el, start, end

        src = MUSTACHE_ENCODED_SPACES_RE.sub(r'{{ \1 }}', el.get('src', ''))
        if self._is_url(src):
            image = src
        elif src.strip().startswith('{{'):
            image = src
        else:
            image = f'{self.images_dir}/{src.strip("/")}' if self.images_dir else src.strip('/')
        el.set('src', self.unescape(image))
        # each markdown image should have default style
        el.set('style', self.unescape('max-width: 100%;'))
        return el, start, end


class NoTrackingLinkProcessor(LinkInlineProcessor):
    def handleMatch(self, m, data):
        el, start, end = super().handleMatch(m, data)
        if el is None:
            return el, start, end

        href = _strip_bidi_url_wrappers(el.get('href', ''))
        if href.startswith('!'):
            href = href[1:]
            el.set('clicktracking', 'off')
        el.set('href', href)
        return el, start, end


class InlineTextExtension(Extension):
    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(InlineBlockProcessor(md.parser), 'inline_text', 175)


class BaseUrlExtension(Extension):
    def __init__(self, images_dir):
        super().__init__()
        self.images_dir = images_dir

    def extendMarkdown(self, md):
        md.inlinePatterns.register(BaseUrlImageProcessor(IMAGE_LINK_RE, md, self.images_dir), 'base_url_image', 175)


class NoTrackingLinkExtension(Extension):
    def __init__(self):
        super().__init__()

    def extendMarkdown(self, md):
        md.inlinePatterns.register(NoTrackingLinkProcessor(LINK_RE, md), 'no_tracking_link', 175)


class LegacyStrongExtension(Extension):
    def extendMarkdown(self, md):
        # Markdown 2 accepted whitespace and newlines immediately inside strong delimiters.
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(LEGACY_STRONG_RE, 'strong'),
            'legacy_strong',
            71,
        )


def inline_text():
    return InlineTextExtension()


def base_url(base_url):
    return BaseUrlExtension(base_url)


def no_tracking():
    return NoTrackingLinkExtension()


def legacy_strong():
    return LegacyStrongExtension()
