from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
import re

INLINE_TEXT_PATTERN = r'\[{2}(.+)\]{2}'


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


class InlineTextExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.parser.blockprocessors.add('inline_text', InlineBlockProcessor(md.parser), '<paragraph')


def inline_text():
    return InlineTextExtension()
