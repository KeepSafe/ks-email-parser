import re
import bs4
import os
import os.path
import asyncio
from . import service
from .. import fs, utils, placeholder as place_holders
from ..renderer import HtmlRenderer
from ..reader import Template, read as reader_read
import fnmatch
import cherrypy
from functools import lru_cache
from collections import namedtuple
import random
import string
import urllib.parse
import time
from html import escape as html_escape
import jinja2
import pkgutil
import requests
import threading
import subprocess
import logging
import sys
from multiprocessing import Manager


RESOURCE_PACKAGE = 'email_parser.resources.gui'


DOCUMENT_TIMEOUT = 24 * 60 * 60  # 24 hours

HTML_PARSER = 'lxml'

STYLES_PARAM_NAME = 'HIDDEN__styles'
TEMPLATE_PARAM_NAME = 'HIDDEN__template'
EMAIL_PARAM_NAME = 'HIDDEN__saved_email_filename'
WORKING_PARAM_NAME = 'HIDDEN__working_name'
LAST_ACCESS_PARAM_NAME = 'HIDDEN__last_access_time'
FINAL_INCOMPLETE_CODE = 'HIDDEN__preview_incomplete_code'

OVERWRITE_PARAM_NAME = 'overwrite'
SAVEAS_PARAM_NAME = 'saveas_filename'

CONTENT_TYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
}


# Dealing with documents, in our cache & invented from POST params


Document = namedtuple('Document', ['working_name', 'email_name', 'template_name', 'styles', 'args'])


RECENT_DOCUMENTS = dict()


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


# Dealing with HTML & soup


def _get_body_content_string(soup, comments=True):
    if not isinstance(soup, bs4.BeautifulSoup):
        soup = bs4.BeautifulSoup(soup, HTML_PARSER)
    return ''.join(
        ('<!--{}-->'.format(C) if comments else '') if isinstance(C, bs4.Comment)
        else str(C)
        for C in soup.body.contents
    )


# Utilities


def _read_template(settings, template_name):
    return fs.read_file(settings.templates, template_name)


def _list_files_recursively(path, hidden=False, relative_to_path=False):
    result = set()
    for dirpath, _, filenames in os.walk(path):
        if hidden or not dirpath.startswith('.'):
            for filename in filenames:
                if hidden or not filename.startswith('.'):
                    name = os.path.join(dirpath, filename)
                    if relative_to_path:
                        name = os.path.relpath(name, path)
                    result.add(name)
    return sorted(result)


def _pop_styles(args):
    styles = args.pop(STYLES_PARAM_NAME, [])
    if isinstance(styles, str):
        styles = styles.split(',')
    styles = [S for S in styles if S.lower().endswith('.css')]
    return styles


def _unplaceholder(placeholders):
    def fix_item(item):
        if item.startswith('[[') and item.endswith(']]'):
            return item[2:-2]
        else:
            return item
    return {K: fix_item(V) for K, V in placeholders.items()}


def _get_email_locale_n_name(email_name):
    match = re.match(r'([^/]+)/([^/]+).xml', email_name)
    return match.group(1, 2)


def _get_email_from_cms_service(settings, email_name):
    locale, name = _get_email_locale_n_name(email_name)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = service.Client(settings.cms_service_host, loop)
    req = client.get_template(locale, name)
    res = loop.run_until_complete(req)
    return res


def _push_email_to_cms_service(settings, email_name, email_path):
    locale, name = _get_email_locale_n_name(email_name)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = service.Client(settings.cms_service_host, loop)
    req = client.push_template(locale, name, email_path)
    res = loop.run_until_complete(req)
    return res


def _set_logging_handler():
    logger = logging.getLogger()
    error_msgs_queue = Manager().Queue()
    warning_msgs_queue = Manager().Queue()
    handler = utils.ProgressConsoleHandler(error_msgs_queue, warning_msgs_queue, stream=sys.stdout)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return handler


# Editing & rendering


class InlineFormReplacer(object):

    """
    Reads template files & inserts values to approximate rendered format (or editor-style format)
    """
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
        self.required = list()  # Only valid after we've done a replacement on a template
        self.html = None

    @classmethod
    def make(cls, settings, args, template_name):
        print(settings.images)
        replacer = cls({'base_url': settings.images}, args)
        replacer.require('subject')
        # Generate our filled-in template
        template_html = _read_template(settings, template_name)
        # We have to run replacer to populate its attrs
        replacer.replace(template_html)
        return replacer

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
        self.html = self.CONTENT_REGEX.sub(self._sub, template_html)
        return self.html

    def _should_make_placeholder(self, key):
        return key in self.names and key not in self.builtins

    def _format_placeholder(self, key, value):
        return '[[{0}]]'.format(value) if key in self.attrs else value

    def placeholders(self, fill_missing=None):
        """
        Generate placeholder dict.
        :param fill_missing: A function taking a missing placeholder name & returning a temporary fill value.
                May be `None` indicating not to return such replacements.
        :return: Dict of placeholder names to values.
        """
        result = {
            K: self._format_placeholder(K, V)
            for K, V in self.values.items()
            if self._should_make_placeholder(K)
        }
        print('Making result!')
        if fill_missing is not None:
            for key in self.required:
                print('Checking out {}'.format(key))
                if self._should_make_placeholder(key) and not result.get(key):
                    result[key] = self._format_placeholder(key, fill_missing(key))
                    print('Added!', key, result[key])
        return result

    def make_value_list(self):
        values = list()
        written_names = set()
        for name in self.names:
            if name in written_names or name in self.builtins:
                continue
            written_names.add(name)
            value = self.require(name)
            values.append([name, value])
        return values


class GenericRenderer(object):

    """
    Render directories and simple documents.
    """

    def __init__(self, settings):
        self.settings = settings
        self._resource_cache = dict()

    def resource(self, resource_name):
        resource = pkgutil.get_data(RESOURCE_PACKAGE, resource_name).decode('utf-8')
        return resource

    def gui_template(self, template_name, **args):
        resource = self.resource(template_name)
        return jinja2.Template(resource).render(**args)

    def directory(
            self,
            description, root, path, href,
            accepts=(lambda path: not os.path.basename(path).startswith('.')),
            old_filename='',
            actions=()
    ):
        root_path = os.path.join(root, path)
        parent = href(os.path.dirname(path)) if path else None
        files = list()
        for name in sorted(os.listdir(root_path)):
            name_path = os.path.join(path, name)
            if accepts(name):
                if os.path.isdir(os.path.join(root, path, name)):
                    files.append([href(name_path), "\U0001f4c2", name])
                else:
                    files.append([href(name_path), "\U0001f4c4", name])
        return self.gui_template(
            'directory.html.jinja2',
            title=description,
            old_filename=old_filename,
            parent=parent,
            actions=actions,
            files=files,
        )

    def question(self, title, description, actions):
        return self.gui_template(
            'question.html.jinja2',
            title=title,
            description=description,
            actions=actions,
        )

    def error(self, title, description, actions):
        return self.gui_template(
            'error.html.jinja2',
            title=title,
            description=description,
            actions=actions,
        )


class InlineFormRenderer(GenericRenderer):

    """
    Render editors and previews
    """

    def __init__(self, settings, verify_image_url=None):
        super().__init__(settings)
        self.settings = settings
        self._verified_images = set()

        verify_image_url = verify_image_url or self.settings.images
        threading.Thread(target=self._prepare_verified_images, args=(verify_image_url,)).start()

    def save(self, email_name, template_name, styles, **args):
        """
        Saves email in XML format
        :param email_name:
        :param template_name:
        :param styles:
        :param args:
        :return:
        """
        xml = self.content_to_save(email_name, template_name, styles, **args)

        fs.save_file(xml, self.settings.source, email_name)
        place_holders.generate_config(self.settings)
        place_holders._read_placeholders_file.cache_clear()

    def content_to_save(self, email_name, template_name, styles, **args):
        replacer = InlineFormReplacer.make(self.settings, args, template_name)
        xml = self.gui_template(
            'email.xml.jinja2',
            template=template_name,
            style=','.join(styles),
            attrs=replacer.attrs,
            values=replacer.make_value_list(),
        )
        return xml

        if self.settings.save:
            abspath = os.path.abspath(os.path.join(self.settings.source, email_name))
            return subprocess.check_output([self.settings.save, abspath], stderr=subprocess.STDOUT)
        else:
            return None

    def render_preview(self, template_name, styles, **args):
        replacer = InlineFormReplacer.make(self.settings, args, template_name)
        if styles:
            # Use "real" renderer, replace missing values with ???
            placeholders = replacer.placeholders(lambda missing_key: '???')
            html = HtmlRenderer(Template(template_name, styles), self.settings, '').render(placeholders)
        else:
            html = self.resource('preview.no.styles.html')
        return html, (styles and not replacer.required)

    def render_editor(
            self, template_name,
            styles=(),
            actions={},
            **args
    ):
        replacer = InlineFormReplacer.make(self.settings, args, template_name)

        edit_html = replacer.html
        edit_column = _get_body_content_string(edit_html).strip()
        image_attrs = self._find_image_attrs(edit_html)
        image_filenames = self._find_images()

        print(image_attrs)
        print(image_filenames)
        print(self._verified_images)

        return self.gui_template(
            "editor.html.jinja2",
            view_url=actions.get('preview_fragment'),
            title='Editing {}'.format(template_name),
            subject=args.get('subject', ''),
            content=edit_column,
            all_styles=self._find_styles(),
            styles=styles,
            save_url=actions.get('save'),
            attrs=replacer.attrs,
            values=args,
            dropdowns={A: image_filenames for A in image_attrs},
            verified_dropdowns={A: self._verified_images for A in image_attrs}
        )

    def render_email(self, email_path):
        template, placeholders, _ = reader_read(email_path)
        args = _unplaceholder(placeholders)

        html = HtmlRenderer(template, self.settings, '').render(placeholders)
        return html, args.get('subject')

    def _find_styles(self, path_glob='*.css'):
        return list(fnmatch.filter(os.listdir(self.settings.templates), path_glob))

    def _find_images(self, local_dir=None):
        if local_dir is None:
            local_dir = self.settings.local_images
        return _list_files_recursively(local_dir, relative_to_path=True)

    def _verify_images(self, image_path_list, verify_image_url):
        if not verify_image_url or not verify_image_url.startswith('http'):
            return image_path_list
        verified = set()
        image_url = verify_image_url.rstrip('/') + '/'
        for image_path in image_path_list:
            url = urllib.parse.urljoin(image_url, image_path)
            print('Verifying {}'.format(url))
            r = requests.head(url)
            if r.status_code == 200:
                verified.add(image_path)
        return verified

    def _prepare_verified_images(self, verify_image_url):
        self._verified_images = self._verify_images(self._find_images(), verify_image_url)
        print(self._verified_images)

    def _find_image_attrs(self, html):
        base_url = self.settings.images
        soup = bs4.BeautifulSoup(html, HTML_PARSER)
        pattern = re.compile('^.*\{\{(.*)\}\}.*$')

        attrs = set()
        for image in soup.find_all(
                'img',
                attrs={
                    'src': (lambda x: x.startswith(base_url) and pattern.match(x))
                }
        ):
            src = image.get('src')
            attr = pattern.match(src).group(1).strip()
            attrs.add(attr)
        return attrs


# Server


class Server(object):

    def __init__(self, settings, edit_renderer, final_renderer):
        self.settings = settings
        self.edit_renderer = edit_renderer
        self.final_renderer = final_renderer

    @classmethod
    def _actions(cls, document, **args):
        qargs = '?' + urllib.parse.urlencode(args) if args else ''
        return {
            'preview': '/preview/{}{}'.format(document.working_name, qargs),
            'save': '{}{}'.format(cls._make_save_url(document), qargs),
            'edit': '/edit/{}{}'.format(document.working_name, qargs),
            'preview_fragment': '/preview_fragment/{}{}'.format(document.working_name, qargs),
        }

    @cherrypy.expose
    def img(self, *path):
        img_name = os.path.join(*path) if path else ''
        img_path = os.path.join(self.settings.local_images, *path)
        if os.path.isdir(img_path):
            return self.edit_renderer.directory(
                'Contents of ' + (img_name or 'image directory'),
                self.settings.local_images, img_name,
                '/img/{}'.format,
            )
        else:
            _, ext = os.path.splitext(os.path.join(*path))
            content_type = CONTENT_TYPES.get(
                ext.lower(),
                'image/{}'.format(ext[1:].lower())
            )

            data = fs.read_file(self.settings.local_images, *path, mode='rb')
            cherrypy.response.headers['Content-Type'] = content_type
            return data

    @cherrypy.expose
    def index(self):
        return self.edit_renderer.question(
            'KS-Email-Parser GUI',
            'Do you want to create a new email from a template, or edit an existing email?',
            [
                ['Create new', '/template'],
                ['Edit', '/email'],
            ]
        )

    @cherrypy.expose
    def push(self, *paths, **_ignored):
        email_name = '/'.join(paths)
        email_path = os.path.join(self.settings.source, email_name)

        try:
            res = _push_email_to_cms_service(self.settings, email_name, email_path)
            messages = ['SUCCES', res]
        except service.TimeoutError as e:
            messages = ['ERROR', str(e)]
        except service.ServiceError as e:
            messages = ['ERROR', 'Service respond with: <code>%s</code><br/><code>%s</code>' % (e.status, e.text)]

        return self.edit_renderer.question(
            messages[0],
            messages[1],
            [
                ['Go back', '/email/{}'.format(email_name)],
            ]
        )

    @cherrypy.expose
    def pull(self, *paths, **_ignored):
        email_name = '/'.join(paths)

        try:
            res = _get_email_from_cms_service(self.settings, email_name)
            fs.save_file(res, self.settings.source, email_name)
            place_holders.generate_config(self.settings)
            place_holders._read_placeholders_file.cache_clear()
            messages = ['SUCCES', '']
        except service.TimeoutError as e:
            messages = ['ERROR', str(e)]
        except service.ServiceError as e:
            messages = ['ERROR', 'Service respond with: <code>%s</code><br/><code>%s</code>' % (e.status, e.text)]

        return self.edit_renderer.question(
            messages[0],
            messages[1],
            [
                ['Go back', '/email/{}'.format(email_name)],
            ]
        )

    @cherrypy.expose
    def timeout(self, *_ignored, **_also_ignored):
        return self.edit_renderer.question(
            '\U0001f62d SORRY \U0001f62d',
            'Your session has timed out! Do you want to create a new email from a template, or edit an existing email?',
            [
                ['Create new', '/template'],
                ['Edit', '/email'],
            ]
        )

    @cherrypy.expose
    def template(self, *paths, **_ignored):
        template_name = '/'.join(paths)
        template_path = os.path.join(self.settings.templates, template_name)
        if os.path.isdir(template_path):
            return self.edit_renderer.directory(
                'Contents of ' + (template_name or 'template directory'),
                self.settings.templates, template_name,
                '/template/{}'.format,
                (lambda path: os.path.isdir(path) or '.htm' in path.lower())
            )
        else:  # A file
            document = _extract_document({}, template_name=template_name)
            if not document.template_name:
                raise cherrypy.HTTPRedirect('/timeout')
            return self.edit_renderer.render_editor(
                document.template_name,
                document.styles,
                actions=self._actions(document, **{TEMPLATE_PARAM_NAME: template_name}),
            )

    @cherrypy.expose
    def preview(self, working_name, **args):
        document = _extract_document(args, working_name)
        print(document)
        if not document.template_name:
            raise cherrypy.HTTPRedirect('/timeout')

        #  Could use `edit_renderer` here to serve images from local host
        html, _ = self.final_renderer.render_preview(
            document.template_name,
            document.styles,
            **document.args
        )
        return html

    @cherrypy.expose
    def preview_fragment(self, working_name, **args):
        document = _extract_document(args, working_name)
        print(document)
        if not document.template_name:
            raise cherrypy.HTTPRedirect('/timeout')

        #  Could use `final_renderer` here to verify images load correctly from remote host
        html, is_complete = self.edit_renderer.render_preview(
            document.template_name,
            document.styles,
            **document.args
        )
        fragment = _get_body_content_string(html).strip()
        if not is_complete:
            # Hack so client can tell from result that it's incomplete
            fragment += ' <!-- {} -->'.format(FINAL_INCOMPLETE_CODE)
        return fragment

    @cherrypy.expose
    def edit(self, working_name, **args):
        document = _extract_document(args, working_name)
        if not document.template_name:
            raise cherrypy.HTTPRedirect('/timeout')

        return self.edit_renderer.render_editor(
            document.template_name,
            document.styles,
            actions=self._actions(document),
            **document.args
        )

    @cherrypy.expose
    def email(self, *paths, **_ignored):
        email_name = '/'.join(paths)
        email_path = os.path.join(self.settings.source, email_name)
        if os.path.isdir(email_path):
            return self.edit_renderer.directory(
                'Contents of ' + (email_name or 'source directory'),
                self.settings.source, email_name,
                '/email/{}'.format
            )
        else:  # A file
            html, subject = self.final_renderer.render_email(email_path)
            return self.edit_renderer.question(
                title=html_escape(subject),
                description=_get_body_content_string(html),
                actions=[
                    ['Edit', '/alter/{}'.format(email_name)],
                    ['Push to repository', '/push/{}'.format(email_name)],
                    ['Update from repository', '/pull/{}'.format(email_name)],
                ]
            )

    @cherrypy.expose
    def alter(self, *paths, **_ignored):
        email_name = '/'.join(paths)
        email_path = os.path.join(self.settings.source, email_name)
        template, placeholders, _ = reader_read(email_path)
        args = _unplaceholder(placeholders)
        document = _extract_document(
            args,
            email_name=email_name,
            template_name=template.name,
            template_styles=template.styles
        )

        return self.edit_renderer.render_editor(
            document.template_name,
            document.styles,
            actions=self._actions(document, **{EMAIL_PARAM_NAME: email_name}),
            **document.args
        )

    @cherrypy.expose
    def saveas(self, working_name, *email_paths, **args):
        email_name = '/'.join(email_paths)
        saveas = args.pop(SAVEAS_PARAM_NAME, None)
        if saveas:
            email_name = '/'.join((email_name, saveas))
        raise cherrypy.HTTPRedirect('/save/{0}/{1}'.format(working_name, email_name))

    @cherrypy.expose
    def save(self, working_name, *paths, **args):
        rel_path = '/'.join(paths)
        full_path = os.path.join(self.settings.source, rel_path)
        document = _extract_document({}, working_name)
        if not document.template_name:
            raise cherrypy.HTTPRedirect('/timeout')

        overwrite = args.pop(OVERWRITE_PARAM_NAME, False)
        placeholders_change = False
        placeholders_messages = []

        if os.path.exists(full_path) and not os.path.isdir(full_path):
            handler = _set_logging_handler()
            content = self.final_renderer.content_to_save(
                rel_path, document.template_name, document.styles, **document.args)
            locale, name = _get_email_locale_n_name(rel_path)
            placeholders_change = not place_holders.validate_email_content(locale, name, content, self.settings.source)
            placeholders_messages = list(handler.error_msgs())

        if overwrite or not os.path.exists(full_path):
            # Create and save
            try:
                output = self.final_renderer.save(rel_path, document.template_name, document.styles, **document.args)
                if output:
                    output = str(output, 'utf-8')
                    return self.final_renderer.question(
                        title='Saved & postprocessed email: {}'.format(rel_path),
                        description=html_escape(output),
                        actions=[
                            ['View', '/email/{}'.format(rel_path), 2000],
                        ]
                    )

            except subprocess.CalledProcessError as err:
                output = str(err.output, 'utf-8') if err.output else 'Error #{}'.format(err.returncode)
                return self.final_renderer.error(
                    title='Postprocessing failed for email: {}'.format(rel_path),
                    description=html_escape(output),
                    actions=[
                        ['View', '/email/{}'.format(rel_path)],
                    ]
                )

            # No postprocessing performed/requested
            raise cherrypy.HTTPRedirect('/email/{}'.format(rel_path))
        elif os.path.isdir(full_path):
            # Show directory or allow user to create new file
            html = self.edit_renderer.directory(
                'Select save name/directory: ' + rel_path,
                self.settings.source, rel_path,
                (lambda path: '/save/{0}/{1}'.format(working_name, path)),
                old_filename=os.path.basename(document.email_name) if document.email_name else '',
                actions=[
                    ['Save', '/saveas/{0}/{1}'.format(working_name, rel_path)],
                    ['Return to Edit', '/edit/{}'.format(working_name)],
                ]
            )
            return html
        else:
            # File already exists or placeholders change: overwrite?
            question_str = 'Are you sure you want to overwrite the existing email <code>{}</code>?'.format(rel_path)
            if placeholders_change:
                question_str = 'Are you sure you want to overwrite the existing email <code>{0}</code>?\
                                <blockquote><b>WARNING</b><br/>{1}\
                                </blockquote>'.format(rel_path, '<br/>'.join(placeholders_messages))

            # File already exists: overwrite?
            return self.edit_renderer.question(
                'Overwriting ' + rel_path,
                question_str,
                [
                    ['No, save as a new file',
                     '/save/{0}/{1}'.format(
                         working_name, os.path.dirname(rel_path)
                     )],
                    ['Yes, how dare you question me!',
                     '/save/{0}/{1}?{2}=1'.format(
                         working_name, rel_path, OVERWRITE_PARAM_NAME
                     )],
                ]
            )

    @classmethod
    def _make_save_url(cls, document):
        if document.email_name:
            return '/save/{}/{}'.format(document.working_name, document.email_name)
        else:
            return '/save/{}'.format(document.working_name)


def serve(args):
    from ..cmd import read_settings

    path = '/'

    settings = read_settings(args)
    final_renderer = InlineFormRenderer(settings)

    edit_settings = settings._replace(images=path + 'img')  # Serve images from local host during edit step.
    edit_renderer = InlineFormRenderer(edit_settings, verify_image_url=settings.images)

    cherrypy.config.update({'server.socket_port': args.port or 8080})
    cherrypy.quickstart(Server(
        settings, edit_renderer=edit_renderer, final_renderer=final_renderer
    ), path)
