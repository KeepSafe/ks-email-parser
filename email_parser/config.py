from collections import namedtuple

Paths = namedtuple('Paths', ['source', 'destination', 'templates', 'images'])

_default_paths = Paths('src', 'target', 'templates_html', 'templates_html/img')
_default_pattern = '{locale}/{name}.xml'
_default_base_img_path = 'http://www.getkeepsafe.com/emails/img'
_default_rlt = ['ar', 'he']

paths = _default_paths
pattern = _default_pattern
base_img_path = _default_base_img_path
rtl_locales = _default_rlt


def init(*,
         _paths=_default_paths,
         _pattern=_default_pattern,
         _base_img_path=_default_base_img_path,
         _rtl_locales=_default_rlt):
    global paths, pattern, base_img_path, rtl_locales
    paths = _default_paths
    pattern = _pattern
    base_img_path = _base_img_path
    rtl_locales = _rtl_locales
