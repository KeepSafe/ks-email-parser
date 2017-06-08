import os
from collections import namedtuple

Paths = namedtuple('Paths', ['root', 'source', 'destination', 'templates', 'images'])

_default_paths = Paths('', 'src', 'target', 'templates_html', 'templates_html/img')
_default_pattern = '{locale}/{name}.xml'
_default_base_img_path = 'http://www.getkeepsafe.com/emails/img'
_default_rlt = ['ar', 'he']
_root_path = '.'


def _build_paths():
    return Paths(* [os.path.join(_root_path, p) for p in _default_paths])


paths = _build_paths()
pattern = _default_pattern
base_img_path = _default_base_img_path
rtl_locales = _default_rlt


def init(*,
         root_path=_root_path,
         _pattern=_default_pattern,
         _base_img_path=_default_base_img_path,
         _rtl_locales=_default_rlt):
    global _root_path, paths, pattern, base_img_path, rtl_locales
    _root_path = root_path
    paths = _build_paths()
    pattern = _pattern
    base_img_path = _base_img_path
    rtl_locales = _rtl_locales
