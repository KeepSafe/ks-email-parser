import re
import bs4
import http.server
import os, os.path
from .. import fs
from ..renderer import HtmlRenderer
from ..reader import Template, read as reader_read
import fnmatch
import cherrypy


STYLES_PARAM_NAME = 'styles'
EDIT_PARAM_NAME = 'edit'
EDITED_PARAM_NAME = 'edited'


def soup_fragment(html_fragment):
    # http://stackoverflow.com/a/15981476
    soup = bs4.BeautifulSoup(html_fragment)
    if soup.body:
        return soup.body.next
    elif soup.html:
        return soup.html.next
    else:
        return soup


def _make_fields(names, values):
    result = list()
    if names:
        result.append('<fieldset class="generated-fields"><ul>')
        for name in names:
            result.append((
                '<li><label>{0}: ' +
                '<input type="text" name="{0}" placeholder="{0}" value="{1}" style="width: 60%" />' +
                '</label></li>').format(
                name, values.get(name, '')
            ))
        result.append('</ul></fieldset>')
    return '\n'.join(result)


def _make_hidden_fields(*args):
    result = list()
    result.append('<div class="generated-hidden">')
    for values in args:
        for name, value in values.items():
            result.append('<input type="hidden" name="{0}" value="{1}"/>'.format(name, value))
    result.append('</div>')
    return '\n'.join(result)


def _make_actions(items):
    result = list()
    if items:
        result.append('<fieldset class="generated-actions">')
        for name, action in items:
            result.append('<input type="submit" value="{0}" formaction="{1}" />'.format(name, action))
        result.append('</fieldset>')
    return '\n'.join(result)


def _directory(description, root, path, href, accepts=(lambda name: not name.startswith('.'))):

    full_path = os.path.join(root, path)
    soup = bs4.BeautifulSoup('''<html>
<head><title>Template index of {0}</title></head>
<body>
<h1>Contents of <span class="index-path">{0}</span></h1>
<ul>
</ul>
</body>
</html>'''.format(description))
    ul = soup.find('ul')
    for name in sorted(os.listdir(full_path)):
        if accepts(name):
            name_path = os.path.join(path, name)
            ul.append(soup_fragment('<li><a href="{href}">{name}</a></li>'.format(
                href=href(name_path), name=name
            )))
    return soup.prettify()


def _wrap_body_in_form(html, prefixes=[], postfixes=[]):
    soup = bs4.BeautifulSoup(html)
    body = soup.find('body')
    new_form = soup.new_tag('form', **{'method': 'POST'})
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


def _make_subject_line(subject):
    return '<h1 class="subject" style="text-align: center">{}</h1>'.format(subject)


def _unplaceholder(placeholders):
    def fix_item(item):
        if item.startswith('[[') and item.startswith(']]'):
            return item[2:-2]
        else:
            return item
    X = {K: fix_item(V) for K, V in placeholders.items()}
    print(X)
    return X


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

    def require(self, name):
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
            return before + (self.require(name) or ('{{' + name + '}}'))
        else:
            return before + self._textarea(name)

    def _textarea(self, name):
        return ('<textarea name="{0}" placeholder="{0}"' +
                ' style="resize: vertical; width: 95%; height: 160px;">{1}</textarea>').format(name, self.require(name))

    def replace(self, template_html):
        return self.CONTENT_REGEX.sub(self._sub, template_html)

    def placeholders(self):
        return {
            K: '[[{0}]]'.format(V) if K in self.attrs else V
            for K, V in self.values.items()
        }


class InlineFormRenderer(object):
    def __init__(self, settings):
        self.settings = settings

    def _read_template(self, template_name):
        return fs.read_file(self.settings.templates, template_name)

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

    def render(self, template_name, styles=(), force_edit=False,
               editing_actions=[],
               preview_actions=[],
               **args
               ):
        replacer = InlineFormReplacer({'base_url': self.settings.images}, args)
        replacer.require('subject')
        template_html = self._read_template(template_name)
        html = replacer.replace(template_html)

        if force_edit or replacer.required or not styles:
            # Some things are missing, show form with stuff still required
            html = _wrap_body_in_form(
                html,
                prefixes=[
                    self._style_list(styles),
                    _make_fields(['subject'] + list(replacer.attrs), args),
                    _make_subject_line(args.get('subject'))
                ],
                postfixes=[
                    _make_actions(editing_actions)
                ]
            )
            return html
        else:
            # Everything filled in, use "real" renderer
            placeholders = replacer.placeholders()
            html = HtmlRenderer(Template(template_name, styles), self.settings, '').render(placeholders)
            return _wrap_body_in_form(
                html,
                prefixes=[
                    _make_subject_line(args.get('subject'))
                ],
                postfixes=[
                    _make_hidden_fields(args, {STYLES_PARAM_NAME: styles[0]}),
                    _make_actions(preview_actions)
                ]
            )


class Server(object):
    def __init__(self, settings, renderer):
        self.settings = settings
        self.renderer = renderer

    def _edit_template(self, name):
        return '/template/{0}?{1}=1'.format(name, EDIT_PARAM_NAME)

    def _edit_email(self, name):
        return '/email/{0}?{1}=1'.format(name, EDIT_PARAM_NAME)

    def _edited_email(self, name):
        return '/email/{0}?{1}=1'.format(name, EDITED_PARAM_NAME)

    def _editing_email(self, name):
        return '/email/{0}?{1}=1&{2}=1'.format(name, EDIT_PARAM_NAME, EDITED_PARAM_NAME)

    @cherrypy.expose
    def template(self, *paths, **args):
        template_name = '/'.join(paths)
        template_path = os.path.join(self.settings.templates, template_name)
        if os.path.isdir(template_path):
            return _directory(template_name or 'template directory',
                              self.settings.templates, template_name, '/template/{}'.format)
        else:  # A file
            styles = [args.pop(STYLES_PARAM_NAME)] if STYLES_PARAM_NAME in args else []
            force_edit = args.pop(EDIT_PARAM_NAME, False)
            return self.renderer.render(template_name, styles, force_edit,
                                        editing_actions=[
                                            ['Preview', '/template/{}'.format(template_name)],
                                        ],
                                        preview_actions=[
                                            ['Save', '/saveas/{}'.format(template_name)],
                                            ['Edit', self._edit_template(template_name)],
                                        ],
                                        **args)

    @cherrypy.expose
    def saveas(self, *template_paths, **args):
        template_name = '/'.join(template_paths)
        raise NotImplemented
        # Request path to save under, save it, & forward to complete rendered email

    @cherrypy.expose
    def save(self, *email_paths, **args):
        email_name = '/'.join(email_paths)
        raise NotImplemented
        # Choose to overwrite or save as

    @cherrypy.expose
    def email(self, *paths, **args):
        email_name = '/'.join(paths)
        email_path = os.path.join(self.settings.source, email_name)
        if os.path.isdir(email_path):
            return _directory(email_name or 'source directory',
                              self.settings.source, email_name, '/email/{}'.format)
        else:  # A file
            force_edit = args.pop(EDIT_PARAM_NAME, False)
            was_edited = args.pop(EDITED_PARAM_NAME, False)
            template, placeholders, _ = reader_read(email_path)
            edited_args = _unplaceholder(placeholders)
            if was_edited:
                edited_args.update(args)
            styles = [edited_args.pop(STYLES_PARAM_NAME)] if STYLES_PARAM_NAME in edited_args else template.styles
            print(styles)
            print(template.styles)

            if force_edit or was_edited:
                return self.renderer.render(template.name, styles, force_edit,
                                            editing_actions=[
                                                ['Preview', self._edited_email(email_name)],
                                                ['Edit', self._editing_email(email_name)],
                                                ['Reset', self._edit_email(email_name)],
                                            ],
                                            preview_actions=[
                                                ['Save', '/save/{}'.format(email_name)],
                                                ['Edit', self._editing_email(email_name)],
                                                ['Reset', '/email/{}'.format(email_name)],
                                            ],
                                            **edited_args
                                            )
            else:  # Show existing email
                html = HtmlRenderer(template, self.settings, '').render(placeholders)
                return _wrap_body_in_form(
                    html,
                    prefixes=[
                        _make_subject_line(edited_args.get('subject'))
                    ],
                    postfixes=[
                        _make_hidden_fields(edited_args, {STYLES_PARAM_NAME: template.styles[0]}),
                        _make_actions([
                                ['Edit', self._edit_email(email_name)],
                        ])
                    ]
                )


def render(args):
    from ..cmd import read_settings
    settings = read_settings(args)

    renderer = InlineFormRenderer(settings)
    if args.port:
        cherrypy.config.update({'server.socket_port': args.port})
        cherrypy.quickstart(Server(settings, renderer), '/')

    elif args.template:
        print(renderer.render(args.template))
