class HtmlRenderer(object):
    def __init__(self, template):
        self.template = template

    def render(self, placeholders):
        pass


class TextRenderer(object):
    def render(self, placeholders):
        pass


class SubjectRenderer(object):
    def render(self, placeholders):
        pass


def render(template, placeholders):
    html_renderer = Html
