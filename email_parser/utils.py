_LOCALES_MAPPING = {'he': 'en', 'pt-BR': 'pt', 'zh-TW-Hant': 'zh-TW'}


def normalize_locale(locale):
    if locale in _LOCALES_MAPPING:
        return _LOCALES_MAPPING[locale]
    return locale
