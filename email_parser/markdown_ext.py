from markdown.inlinepatterns import Pattern, ImagePattern, LinkPattern, LINK_RE, IMAGE_LINK_RE
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
import re

INLINE_TEXT_PATTERN = r'\[{2}(.+)\]{2}'
IMAGE_PATTERN = '![{}]({}/{})'


class InlineBlockProcessor(BlockProcessor):

    """
    Inlines the content instead of parsing it as markdown.
    """
    RE = re.compile(INLINE_TEXT_PATTERN)

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.match(block)
        if m:
            text = m.group(1)
            parent.text = text


class BaseUrlImagePattern(Pattern):

    """
    Adds base url to images which have relative path.
    """

    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, images_dir, *args):
        super().__init__(*args)
        if images_dir:
            self.images_dir = images_dir.strip('/')
        else:
            self.images_dir = ''
        self.image_pattern = ImagePattern(*args)

    def _is_url(self, text):
        url = text.strip().strip('/').split(' ')[0]
        return self.url_pattern.match(url)

    def handleMatch(self, m):
        if self._is_url(m.group(10)):
            image = m.string
        else:
            image = IMAGE_PATTERN.format(m.group(2), self.images_dir, m.group(10).strip('/'))
        pattern = re.compile("^(.*?)%s(.*?)$" % self.image_pattern.pattern, re.DOTALL | re.UNICODE)
        match = re.match(pattern, ' ' + image + ' ')
        return self.image_pattern.handleMatch(match)


class NoTrackingLinkPattern(LinkPattern):
    def __init__(self, *args):
        super().__init__(*args)

    def handleMatch(self, m):
        el = super().handleMatch(m)
        if el.get('href') and el.get('href').startswith('!'):
            el.set('href', el.get('href')[1:])
            el.set('clicktracking', 'off')
        return el


class InlineTextExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.parser.blockprocessors.add('inline_text', InlineBlockProcessor(md.parser), '<paragraph')


class BaseUrlExtension(Extension):

    def __init__(self, images_dir):
        super().__init__()
        self.images_dir = images_dir

    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add('base_url_image', BaseUrlImagePattern(self.images_dir, IMAGE_LINK_RE, md), '<image_link')


class NoTrackingLinkExtension(Extension):
    def __init__(self):
        super().__init__()

    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add('no_tracking_link', NoTrackingLinkPattern(LINK_RE, md), '<link')


def inline_text():
    return InlineTextExtension()


def base_url(base_url):
    return BaseUrlExtension(base_url)


def no_tracking():
    return NoTrackingLinkExtension()
