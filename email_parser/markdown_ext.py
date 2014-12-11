from markdown.inlinepatterns import Pattern, ImagePattern, IMAGE_LINK_RE
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
import re

INLINE_TEXT_PATTERN = r'\[{2}(.+)\]{2}'
IMAGE_PATTERN = '![{}]({}/{})'

class InlineBlockProcessor(BlockProcessor):
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
    def __init__(self, images_dir, *args):
        super().__init__(*args)
        if images_dir:
            self.images_dir = images_dir.strip('/')
        else:
            self.images_dir = ''
        self.image_pattern = ImagePattern(*args)

    def handleMatch(self, m):
        image = IMAGE_PATTERN.format(m.group(2), self.images_dir, m.group(10).strip('/'))
        pattern = re.compile("^(.*?)%s(.*?)$" % self.image_pattern.pattern, re.DOTALL | re.UNICODE)
        match = re.match(pattern, ' ' + image + ' ')
        return self.image_pattern.handleMatch(match)


class InlineTextExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.parser.blockprocessors.add('inline_text', InlineBlockProcessor(md.parser), '<paragraph')


class BaseUrlExtension(Extension):
    def __init__(self, images_dir):
        super().__init__()
        self.images_dir = images_dir

    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add('base_url_image', BaseUrlImagePattern(self.images_dir, IMAGE_LINK_RE, md), '<image_link')


def inline_text():
    return InlineTextExtension()

def base_url(images_dir):
    return BaseUrlExtension(images_dir)
