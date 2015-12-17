import re
import bs4
import os, os.path
from .. import fs
from ..renderer import HtmlRenderer
from ..reader import Template, read as reader_read
import fnmatch
import cherrypy
from collections.abc import Sequence
from functools import lru_cache
from collections import namedtuple
import random, string
import time


DOCUMENT_TIMEOUT = 24 * 60 * 60  # 24 hours


STYLES_PARAM_NAME = 'HIDDEN__styles'
TEMPLATE_PARAM_NAME = 'HIDDEN__template'
EMAIL_PARAM_NAME = 'HIDDEN__saved_email_filename'
WORKING_PARAM_NAME = 'HIDDEN__working_name'
LAST_ACCESS_PARAM_NAME = 'HIDDEN__last_access_time'

OVERWRITE_PARAM_NAME = 'overwrite'
SAVEAS_PARAM_NAME = 'saveas_filename'


Document = namedtuple('Document', ['working_name', 'email_name', 'template_name', 'styles', 'args'])


CONTENT_TYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
}


RECENT_DOCUMENTS = dict()


def _html_encode(text):
    # This is wrong, fix when on the ground
    return text.replace('<', '&lt;').replace('>', '&gt;')


def _clean_documents():
    expired_keys = set()
    for key, value in RECENT_DOCUMENTS.items():
        last_access = value.setdefault(LAST_ACCESS_PARAM_NAME, time.time())
        if last_access < time.time() - DOCUMENT_TIMEOUT:
            expired_keys.add(key)
    for key in expired_keys:
        del RECENT_DOCUMENTS[key]


@lru_cache(maxsize=64)
def _get_working_args(working_name):
    result = RECENT_DOCUMENTS.get(working_name, {WORKING_PARAM_NAME: working_name})
    RECENT_DOCUMENTS[working_name] = result
    return result


def _new_working_args():
    working_name = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(8))
    _clean_documents()
    return _get_working_args(working_name)


def _extract_document(args=None, working_name=None, email_name=None, template_name=None, template_styles=None):
    # Return working_name, email_name, template_name, styles, args
    args = args or dict()
    working_name = working_name or args.pop(WORKING_PARAM_NAME, working_name)
    if working_name:
        working_args = _get_working_args(working_name)
    else:
        working_args = _new_working_args()
    working_args.update(args)
    working_args[LAST_ACCESS_PARAM_NAME] = time.time()
    if email_name:
        working_args.update({EMAIL_PARAM_NAME: email_name})
    if template_name:
        working_args.update({TEMPLATE_PARAM_NAME: template_name})

    result_args = dict(working_args)
    working_name = result_args.pop(WORKING_PARAM_NAME)
    email_name = result_args.pop(EMAIL_PARAM_NAME, None)
    template_name = result_args.pop(TEMPLATE_PARAM_NAME, None)
    styles = template_styles or _pop_styles(result_args) or []
    working_args.update({STYLES_PARAM_NAME: ','.join(styles)})
    return Document(working_name, email_name, template_name, styles, result_args)


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
            value = values.get(name, '')
            result.append((
                '<li><label>{2}: ' +
                '<input type="text" class="{3}" name="{0}" placeholder="{0}" value="{1}" style="width: 60%" />' +
                '</label></li>').format(
                name, value, friendly_names.get(name, name), 'present' if value else 'absent'
            ))
        result.append('</ul></fieldset>')
    return '\n'.join(result)


def _make_hidden_fields(*args):
    result = list()
    result.append('<div class="generated-hidden">')
    for values in args:
        for name, value in values.items():
            if isinstance(value, Sequence) and not isinstance(value, str):
                value = ','.join(value)
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


def _list_files_recursively(path, hidden=False):
    result = set()
    for dirpath, _, filenames in os.walk(path):
        if hidden or not dirpath.startswith('.'):
            for filename in filenames:
                if hidden or not filename.startswith('.'):
                    result.add(os.path.join(dirpath, filename))
    return sorted(result)


def _insert_image_selectors(html, base_url, local_dir=None):
    local_dir = local_dir or base_url
    if not os.path.isdir(local_dir):
        return html
    soup = bs4.BeautifulSoup(html)
    pattern = re.compile('^.*\{\{.*\}\}.*$')
    for image in soup.find_all(
            'img',
            attrs={
                'src': (lambda x: x.startswith(base_url) and pattern.match(x))
            }
    ):
        src = image.get('src')
        parent = image.parent
        index = parent.index(image)
        image.extract()

        selector = list()
        selector.append('<select>')
        for item in _list_files_recursively(local_dir):
            selector.append('<option value="{0}">{0}</option>'.format(item))
        selector.append('</select>')

        parent.insert(index, soup_fragment('\n'.join(selector)))
    return str(soup)


def _make_index(title, description):
    html = '''<html>
<head><title>{title}</title></head>
<body>
<h1 class="text-align: center;">{title}</h1>
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


def _wrap_body_in_form(html, prefixes=[], postfixes=[], highlight=True):
    soup = bs4.BeautifulSoup(html)
    body = soup.find('body')
    new_form = soup.new_tag('form', **{'method': 'POST'})
    if highlight:
        soup.find('head').insert(0, soup_fragment(
            '<style type="text/css">.absent {border-size: 4px; border-color: #ff4444;}</style>'
        ))
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


def _pop_styles(args):
    styles = args.pop(STYLES_PARAM_NAME, [])
    if isinstance(styles, str):
        styles = styles.split(',')
    styles = [S for S in styles if S.lower().endswith('.css')]
    return styles


def _make_subject_line(subject):
    subject = _html_encode(subject) if subject else '<em>&lt;no subject&gt;</em>'
    return '<h1 class="subject" style="text-align: center">{}</h1>'.format(subject)


def _unplaceholder(placeholders):
    def fix_item(item):
        if item.startswith('[[') and item.endswith(']]'):
            return item[2:-2]
        else:
            return item
    X = {K: fix_item(V) for K, V in placeholders.items()}
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
        elif self.builtins.get(name):
            return self.builtins[name]
        else:
            self.required.append(name)
            return ''

    def _sub(self, match):
        before, prefix, name, postfix = match.groups()

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
        value = self.require(name)
        return ('<textarea class="{2}" name="{0}" placeholder="{0}"' +
                ' style="resize: vertical; width: 95%; height: 160px;">{1}</textarea>'
                ).format(name, value, 'present' if value else 'absent')

    def replace(self, template_html):
        return self.CONTENT_REGEX.sub(self._sub, template_html)

    def placeholders(self):
        return {
            K: '[[{0}]]'.format(V) if K in self.attrs else V
            for K, V in self.values.items()
            if K in self.names and K not in self.builtins
        }

    def make_xml(self, template_name, styles):
        result = list()
        result.append('<?xml version="1.0" encoding="UTF-8"?>')
        result.append(
            '<resources xmlns:tools="http://schemas.android.com/tools" template="{0}" style="{1}">'.format(
                template_name, ','.join(styles)
            )
        )
        written_names = set()
        for name in self.names:
            if name in written_names or name in self.builtins:
                continue
            written_names.add(name)
            value = self.require(name)
            if name == 'subject':
                result.append('    <string name="{0}">{1}</string>'.format(name, value))
            elif name in self.attrs:
                result.append('    <string name="{0}" isText="false"><![CDATA[[[{1}]]]]></string>'.format(name, value))
            else:
                result.append('    <string name="{0}"><![CDATA[{1}]]></string>'.format(name, value))
        result.append('</resources>')
        return '\n'.join(result)


class InlineFormRenderer(object):
    def __init__(self, settings):
        self.settings = settings

    def _read_template(self, template_name):
        return fs.read_file(self.settings.templates, template_name)

    def _style_list(self, styles=(), path_glob='*.css'):
        result = list()
        styles_found = 0
        for path in fnmatch.filter(os.listdir(self.settings.templates), path_glob):
            if path in styles:
                styles_found += 1
            result.append(
                '    <option {1} value="{0}">{0}</option>'.format(
                    path, 'selected' if path in styles else ''
                )
            )
        result.insert(0, '<fieldset><select multiple class="{1}" name="{0}">'
                      .format(STYLES_PARAM_NAME, 'present' if styles_found else 'absent')
                      )
        result.append('</select></fieldset>')
        if len(result) > 2:
            return '\n'.join(result)
        else:
            return ''

    def save(self, email_name, template_name, styles, **args):
        replacer = InlineFormReplacer({'base_url': self.settings.images}, args)
        replacer.require('subject')
        template_html = self._read_template(template_name)
        replacer.replace(template_html)
        xml = replacer.make_xml(template_name, styles)

        fs.save_file(xml, self.settings.source, email_name)

    def render(self, template_name, styles=(),
               editing_actions=[],
               preview_actions=[],
               **args
               ):
        replacer = InlineFormReplacer({'base_url': self.settings.images}, args)
        replacer.require('subject')
        template_html = self._read_template(template_name)
        html = replacer.replace(template_html)

        force_edit = not preview_actions
        if force_edit or replacer.required or not styles:
            # Some things are missing, show form with stuff still required
            html = _insert_image_selectors(html, self.settings.images)
            html = _wrap_body_in_form(
                html,
                prefixes=[
                    self._style_list(styles),
                    _make_fields(['subject'] + list(replacer.attrs), args),
                    _make_subject_line(args.get('subject'))
                ],
                postfixes=[
                    _make_actions(editing_actions)
                ],
                highlight=True if preview_actions else False
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
                    _make_actions(preview_actions)
                ]
            )


class Server(object):
    def __init__(self, settings, renderer):
        self.settings = settings
        self.renderer = renderer

    @cherrypy.expose
    def img(self, *path):
        img_name = os.path.join(*path) if path else ''
        img_path = os.path.join(self.settings.images, *path)
        if os.path.isdir(img_path):
            return _directory(img_name or 'image directory',
                              self.settings.images,
                              img_name,
                              '/img/{}'.format,
                              )
        else:
            _, ext = os.path.splitext(os.path.join(*path))
            content_type = CONTENT_TYPES.get(
                ext.lower(),
                'image/{}'.format(ext[1:].lower())
            )

            data = fs.read_file(self.settings.images, *path, mode='rb')
            cherrypy.response.headers['Content-Type'] = content_type
            return data

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
    def timeout(self, *_ignored, **_also_ignored):
        return _wrap_body_in_form(_make_index(
            '&#x1f62d; SORRY &#x1f62d;',
            'Your session has timed out! Do you want to create a new email from a template, or edit an existing email?'
        ), [],
            [
                _make_actions([
                    ['Create new', '/template'],
                    ['Edit', '/email'],
                ])
            ]
        )

    @cherrypy.expose
    def template(self, *paths, **_ignored):
        template_name = '/'.join(paths)
        template_path = os.path.join(self.settings.templates, template_name)
        if os.path.isdir(template_path):
            return _directory(template_name or 'template directory',
                              self.settings.templates,
                              template_name,
                              '/template/{}'.format,
                              (lambda path: os.path.isdir(path) or '.htm' in path.lower())
                              )
        else:  # A file
            document = _extract_document({}, template_name=template_name)
            if not document.template_name:
                raise cherrypy.HTTPRedirect('/timeout')
            return self.renderer.render(document.template_name,
                                        document.styles,
                                        editing_actions=[
                                            ['Preview', '/preview/{}'.format(document.working_name)],
                                        ],
                                        preview_actions=[
                                            ['Save', '/save/{}'.format(document.working_name)],
                                            ['Edit', '/edit/{}'.format(document.working_name)],
                                        ],
                                        )

    @cherrypy.expose
    def preview(self, working_name, **args):
        document = _extract_document(args, working_name)
        print(document)
        if not document.template_name:
            raise cherrypy.HTTPRedirect('/timeout')

        preview_actions = []
        if document.email_name:
            preview_actions.append(['Save', '/save/{}/{}'.format(document.working_name, document.email_name)])
        else:
            preview_actions.append(['Save', '/save/{}'.format(document.working_name)])
        preview_actions.append(['Edit', '/edit/{}'.format(document.working_name)])
        if document.email_name:
            preview_actions.append(['Reset', '/email/{}'.format(document.email_name)])

        return self.renderer.render(document.template_name,
                                    document.styles,
                                    editing_actions= [
                                        ['Preview', '/preview/{}'.format(document.working_name)],
                                    ],
                                    preview_actions=preview_actions,
                                    **document.args
                                    )

    @cherrypy.expose
    def edit(self, working_name, **args):
        document = _extract_document(args, working_name)
        if not document.template_name:
            raise cherrypy.HTTPRedirect('/timeout')

        return self.renderer.render(document.template_name,
                                    document.styles,
                                    editing_actions=[
                                        ['Preview', '/preview/{}'.format(document.working_name)],
                                    ],
                                    **document.args
                                    )

    @cherrypy.expose
    def email(self, *paths, **_ignored):
        email_name = '/'.join(paths)
        email_path = os.path.join(self.settings.source, email_name)
        if os.path.isdir(email_path):
            return _directory(email_name or 'source directory',
                              self.settings.source, email_name, '/email/{}'.format)
        else:  # A file
            template, placeholders, _ = reader_read(email_path)
            args = _unplaceholder(placeholders)

            html = HtmlRenderer(template, self.settings, '').render(placeholders)
            return _wrap_body_in_form(
                html,
                prefixes=[
                    _make_subject_line(args.get('subject'))
                ],
                postfixes=[
                    _make_actions([
                            ['Edit', '/alter/{}'.format(email_name)],
                    ])
                ]
            )

    @cherrypy.expose
    def alter(self, *paths, **_ignored):
        email_name = '/'.join(paths)
        email_path = os.path.join(self.settings.source, email_name)
        template, placeholders, _ = reader_read(email_path)
        args = _unplaceholder(placeholders)
        document = _extract_document(args,
                                     email_name=email_name,
                                     template_name=template.name,
                                     template_styles=template.styles
                                     )
        raise cherrypy.HTTPRedirect('/edit/{}'.format(document.working_name))

    @cherrypy.expose
    def saveas(self, working_name, *email_paths, **args):
        email_name = '/'.join(email_paths)
        saveas = args.pop(SAVEAS_PARAM_NAME, None)
        if saveas:
            email_name = '/'.join((email_name, saveas))
        raise cherrypy.HTTPRedirect('/save/{0}/{1}'.format(working_name, email_name))

    @cherrypy.expose
    def save(self, working_name, *email_paths, **args):
        email_name = '/'.join(email_paths)
        email_path = os.path.join(self.settings.source, email_name)
        document = _extract_document({}, working_name, email_name=email_name)
        if not document.template_name:
            raise cherrypy.HTTPRedirect('/timeout')

        overwrite = args.pop(OVERWRITE_PARAM_NAME, False)
        if overwrite or not os.path.exists(email_path):
            # Create and save
            self.renderer.save(email_name, document.template_name, document.styles, **document.args)
            raise cherrypy.HTTPRedirect('/email/{}'.format(email_name))
        elif os.path.isdir(email_path):
            # Show directory or allow user to create new file
            html = _directory('Select save name/directory: ' + email_name,
                              self.settings.source, email_name,
                              (lambda path: '/save/{0}/{1}'.format(working_name, path))
                              )
            html = _wrap_body_in_form(html,
                                      [],
                                      [
                                          _make_fields([SAVEAS_PARAM_NAME], {}, {SAVEAS_PARAM_NAME: 'New filename'}),
                                          _make_actions([
                                              ['Save', '/saveas/{0}/{1}'.format(working_name, email_name)],
                                              ['Return to Preview', '/preview/{}'.format(working_name)]
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
                    _make_actions([
                        ['No, save as a new file',
                         '/save/{0}/{1}'.format(
                             working_name, os.path.dirname(email_name)
                         )],
                        ['Yes, how dare you question me!',
                         '/save/{0}/{1}?{2}=1'.format(
                             working_name, email_name, OVERWRITE_PARAM_NAME
                         )],
                    ])
                ]
            )


def serve(args):
    from ..cmd import read_settings
    settings = read_settings(args)

    renderer = InlineFormRenderer(settings)
    cherrypy.config.update({'server.socket_port': args.port or 8080})
    cherrypy.quickstart(Server(settings, renderer), '/')
