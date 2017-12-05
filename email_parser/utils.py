_LOCALES_MAPPING = {'pt-BR': 'pt', 'zh-TW-Hant': 'zh-TW'}
from . import config


def normalize_locale(locale):
    if locale in config.lang_mappings:
        return config.lang_mappings[locale]
    return locale
