from collections import namedtuple

Paths = namedtuple('Paths', ['source', 'destination', 'templates', 'images', 'sections'])

_default_paths = Paths('src', 'target', 'templates_html', 'templates_html/img', 'templates_html/sections')
_default_pattern = '{locale}/{name}.xml'
_default_base_img_path = 'http://app.getkeepsafe.com/emails/img'
_default_rtl = ['ar', 'he']
_default_lang_mappings = {'pt-BR': 'pt', 'zh-TW-Hant': 'zh-TW'}

paths = _default_paths
pattern = _default_pattern
base_img_path = _default_base_img_path
rtl_locales = _default_rtl
lang_mappings = _default_lang_mappings


def init(*,
         _paths=_default_paths,
         _pattern=_default_pattern,
         _base_img_path=_default_base_img_path,
         _rtl_locales=_default_rtl,
         _lang_mappings=_default_lang_mappings):
    global paths, pattern, base_img_path, rtl_locales, lang_mappings
    paths = _default_paths
    pattern = _pattern
    base_img_path = _base_img_path
    rtl_locales = _rtl_locales
    lang_mappings = _lang_mappings
