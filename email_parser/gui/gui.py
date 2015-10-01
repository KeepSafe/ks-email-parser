import re
import bs4
import http.server
import os, os.path
from .. import fs
from ..renderer import HtmlRenderer
from ..reader import Template
import fnmatch
import cherrypy


STYLES_PARAM_NAME = 'styles'


def soup_fragment(html_fragment):
    # http://stackoverflow.com/a/15981476
    soup = bs4.BeautifulSoup(html_fragment)
    if soup.body:
        return soup.body.next
    elif soup.html:
        return soup.html.next
    else:
        return soup


class InlineFormReplacer(object):
    # Group 1: spaces and preceding non-space character: must be returned with replacement
    # Group 2: preceding non-space character (if any)
    # Group 3: replace tag
    # Group 4: lookahead: following non-space character (if any)
    CONTENT_REGEX = re.compile(r'(([">]?)[^">{}]*)\{\{\s*(\w+)\s*\}\}(?=[^"<{}]*(["<]?))')

    def __init__(self, builtins=None, values=None):
        self.builtins = builtins or dict()
        self.values = values or dict()
        self.names = list()
        self.attrs = list()
        self.required = list()

    def get(self, name):
        if name not in self.names:
            self.names.append(name)
        if self.values.get(name):
            return self.values[name]
        else:
            self.required.append(name)
            return ''

    def _sub(self, match):
        before, prefix, name, postfix = match.groups()
        print(match.groups())

        self.names.append(name)

        if name in self.builtins:
            return before + self.builtins[name]
        elif prefix == '>' or postfix == '<':
            return before + self._textarea(name)
        elif '"' in (prefix, postfix):
            self.attrs.append(name)
            return before + (self.get(name) or ('{{' + name + '}}'))
        else:
            return before + self._textarea(name)

    def _textarea(self, name):
        return ('<textarea name="{0}" placeholder="{0}"' +
                ' style="resize: vertical; width: 95%; height: 160px;">{1}</textarea>'.format(name, self.get(name))
                )

    def replace(self, template_html):
        return self.CONTENT_REGEX.sub(self._sub, template_html)

    def placeholders(self):
        return {
            K: '[[{0}]]'.format(V) if K in self.attrs else V
            for K, V in self.values.items()
            }

    def _generate_fields(self, names=None, classname='names'):
        result = list()
        if names:
            result.append('<fieldset class="{0}"><ul>'.format(classname))
            for name in names:
                result.append('    <li><label>{0}: <input type="text" name="{0}" placeholder="{0}" value="{1}"/></label></li>'
                              .format(name, self.values.get(name, ''))
                              )
            result.append('</ul></fieldset>')
        return '\n'.join(result)

    def name_fields(self, extra_fields=()):
        return self._generate_fields(list(extra_fields) + list(self.names))

    def attr_fields(self, extra_fields=()):
        return self._generate_fields(list(extra_fields) + list(self.attrs))


class InlineFormRenderer(object):
    def __init__(self, settings):
        self.settings = settings

    def _read_template(self, template_name):
        return fs.read_file(self.settings.templates, template_name)

    def _wrap_body_in_form(self, html, prefixes=[], postfixes=[]):
        soup = bs4.BeautifulSoup(html)
        body = soup.find('body')
        new_form = soup.new_tag('form', **{'method': 'GET'})
        for content in reversed(body.contents):
            new_form.insert(0, content.extract())
        for prefix in reversed(prefixes):
            if prefix.strip():
                new_form.insert(0, soup_fragment(prefix))
        for postfix in postfixes:
            if postfix.strip():
                new_form.append(soup_fragment(postfix))

        body.append(new_form)
        return str(soup)

    def _style_list(self, styles=(), path_glob='*.css'):
        result = list()
        result.append('<fieldset><select multiple name="{0}">'.format(STYLES_PARAM_NAME))
        for path in fnmatch.filter(os.listdir(self.settings.templates), path_glob):
            result.append(
                '    <option {1} value="{0}">{0}</option>'.format(
                    path, 'selected' if path in styles else ''
                )
            )
        result.append('</select></fieldset>')
        if len(result) > 2:
            return '\n'.join(result)
        else:
            return ''

    def _index(self, path):
        template_path = os.path.join(self.settings.templates, path)
        soup = bs4.BeautifulSoup('''<html>
<head><title>Template index of {0}</title></head>
<body>
    <h1>Contents of <span class="index-path">{0}</span></h1>
    <ul>
    </ul>
</body>
</html>'''.format(path or 'template directory'))
        ul = soup.find('ul')
        for name in sorted(os.listdir(template_path)):
            if not name.startswith('.'):
                name_path = os.path.join(path, name)
                ul.append(soup_fragment('<li><a href="/template/{path}">{name}</a></li>'.format(
                    path=name_path, name=name
                )))
        return soup.prettify()

    def render(self, template_name=None, styles=(), **vars):
        if template_name:
            template_path = os.path.join(self.settings.templates, template_name)
        else:
            template_path = self.settings.templates
        if os.path.isdir(template_path):
            return self._index(template_name)
        else:
            replacer = InlineFormReplacer({'base_url': self.settings.images}, vars)
            replacer.get('subject')
            template_html = self._read_template(template_name)
            html = replacer.replace(template_html)
            subject_line = '<h1 class="subject" style="text-align: center">{}</h1>'.format(vars.get('subject'))
            html = self._wrap_body_in_form(
                html,
                prefixes=[
                    self._style_list(styles),
                    replacer.attr_fields(['subject']),
                    subject_line
                ],
                postfixes=['<fieldset><input type="submit" value="Render" /></fieldset>']
            )

            if replacer.required:
                print(replacer.required)
                return html
            else:  # Everything filled in, use "real" renderer
                placeholders = replacer.placeholders()
                print(placeholders)
                html = HtmlRenderer(Template(template_name, styles), self.settings, '').render(placeholders)
                return self._wrap_body_in_form(
                    html,
                    prefixes=[subject_line],
                    postfixes=['<fieldset><input type="submit" value="Save" /></fieldset>']
                )


class Server(object):
    def __init__(self, renderer):
        self.renderer = renderer

    @cherrypy.expose
    def template(self, *paths, **vars):
        path = '/'.join(paths)
        styles = [vars.pop(STYLES_PARAM_NAME)] if STYLES_PARAM_NAME in vars else []
        return self.renderer.render(path, styles, **vars)


def render(args):
    from ..cmd import read_settings
    settings = read_settings(args)

    renderer = InlineFormRenderer(settings)
    if args.port:
        cherrypy.config.update({'server.socket_port': args.port})
        cherrypy.quickstart(Server(renderer), '/')

    elif args.template:
        print(renderer.render(args.template))
