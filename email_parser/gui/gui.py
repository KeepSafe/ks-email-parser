import re
import bs4
import os, os.path
from .. import fs
from ..renderer import HtmlRenderer
from ..reader import Template, read as reader_read
import fnmatch
import cherrypy


STYLES_PARAM_NAME = 'styles'
EDIT_PARAM_NAME = 'edit'
EDITED_PARAM_NAME = 'edited'
TEMPLATE_PARAM_NAME = 'template'
SAVEAS_PARAM_NAME = 'saveas_filename'


def soup_fragment(html_fragment):
    # http://stackoverflow.com/a/15981476
    soup = bs4.BeautifulSoup(html_fragment)
    if soup.body:
        return soup.body.next
    elif soup.html:
        return soup.html.next
    else:
        return soup


def _make_fields(names, values=None, friendly_names=None):
    values = values or dict()
    friendly_names = friendly_names or dict()
    result = list()
    if names:
        result.append('<fieldset class="generated-fields"><ul>')
        for name in names:
            result.append((
                '<li><label>{2}: ' +
                '<input type="text" name="{0}" placeholder="{0}" value="{1}" style="width: 60%" />' +
                '</label></li>').format(
                name, values.get(name, ''), friendly_names.get(name, name)
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


def _make_actions(actions):
    result = list()
    if actions:
        result.append('<fieldset class="generated-actions" style="text-align: center; padding-bottom: 200px" >')
        for name, action in actions:
            result.append('<input type="submit" value="{0}" formaction="{1}" style="font-size: large" />'.format(name, action))
        result.append('</fieldset>')
    return '\n'.join(result)


def _make_index(title, description):
    html = '''<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<div class="description">{description}</div>
</body>
</html>'''.format(title=title, description=description)
    return html


def _directory(
        description, root, path, href,
        accepts=(lambda path: not os.path.basename(path).startswith('.'))
):

    root_path = os.path.join(root, path)
    soup = bs4.BeautifulSoup('''<html>
<head><title>Directory of {0}</title></head>
<body>
<h1>Contents of <span class="index-path">{0}</span></h1>
<ul>
</ul>
</body>
</html>'''.format(description))
    ul = soup.find('ul')
    if path:
        ul.append(soup_fragment('<li><a href="{}">&#8593; <em>Parent Directory</em></a></li>'.format(
            href(os.path.dirname(path))
        )))
    for name in sorted(os.listdir(root_path)):
        name_path = os.path.join(path, name)
        if accepts(name):
            if os.path.isdir(os.path.join(root, path, name)):
                ul.append(soup_fragment('<li><a href="{href}">&#128194; <code>{name}</code></a></li>'.format(
                    href=href(name_path), name=name
                )))
            else:
                ul.append(soup_fragment('<li><a href="{href}">&#128196; <code>{name}</code></a></li>'.format(
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
    return '<h1 class="subject" style="text-align: center">{}</h1>'.format(subject or '<em>&lt;no subject&gt;</em>')


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
    def index(self):
        return _wrap_body_in_form(_make_index(
            'KS-Email-Parser GUI',
            'Do you want to create a new email from a template, or edit an existing email?'
        ), [],
            [
                _make_actions([
                    ['Create new', '/template'],
                    ['Edit', '/email'],
                ])
            ]
        )

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
                                            ['Save', '/save?{0}={1}'.format(TEMPLATE_PARAM_NAME, template_name)],
                                            ['Edit', self._edit_template(template_name)],
                                        ],
                                        **args)

    @cherrypy.expose
    def save(self, *email_paths, **args):
        template_name = args.pop(TEMPLATE_PARAM_NAME, None)
        if not template_name:
            raise Exception('Requires template name to save!')
        email_name = '/'.join(email_paths)
        saveas = args.pop(SAVEAS_PARAM_NAME, None)
        if saveas:
            email_name = '/'.join((email_name, saveas))
        email_path = os.path.join(self.settings.source, email_name)
        if not os.path.exists(email_path):
            # Create and save
            raise NotImplemented
        elif os.path.isdir(email_path):
            # Show directory or allow user to create new file
            html = _directory('Select save name/directory: ' + email_path,
                              self.settings.source, email_name,
                              (lambda path: '/save/{0}?{1}={2}'.format(path, TEMPLATE_PARAM_NAME, template_name))
                              )
            html = _wrap_body_in_form(html,
                                      [],
                                      [
                                          _make_hidden_fields(args),
                                          _make_fields([SAVEAS_PARAM_NAME], {}, {SAVEAS_PARAM_NAME: 'New filename'}),
                                          _make_actions([
                                              ['Save', '/save/{0}?{1}={2}'.format(email_name, TEMPLATE_PARAM_NAME, template_name)]
                                          ])
                                      ])
            return html
        else:
            # File already exists: overwrite?
            return _wrap_body_in_form(_make_index(
                'Overwriting ' + email_name,
                'Are you sure you want to overwrite the existing email <code>{}</code>?'.format(email_name),
            ), [],
                [
                    _make_hidden_fields(args),
                    _make_actions([
                        ['No, I\'m not sure',
                         '/save/{0}?{1}={2}'.format(os.path.dirname(email_name), TEMPLATE_PARAM_NAME, template_name)],
                        ['Yes, how dare you question me!',
                         '/overwrite/{0}?{1}={2}'.format(email_name, TEMPLATE_PARAM_NAME, template_name)],
                    ])
                ]
            )


    @cherrypy.expose
    def overwrite(self, *email_paths, **args):
        raise NotImplemented

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
                                                ['Save', '/save/{2}?{0}={1}'.format(
                                                    TEMPLATE_PARAM_NAME, template.name, email_name
                                                )],
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
