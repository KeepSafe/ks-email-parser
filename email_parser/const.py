SUBJECT_EXTENSION = '.subject'
SUBJECT_RESEND_EXTENSION = '.resend.subject'
SUBJECT_A_EXTENSION = '.a.subject'
SUBJECT_B_EXTENSION = '.b.subject'
TEXT_EXTENSION = '.text'
HTML_EXTENSION = '.html'
SUBJECTS_PLACEHOLDERS = ['subject', 'subject_a', 'subject_b', 'subject_resend']

GLOBALS_EMAIL_NAME = 'global'
GLOBALS_PLACEHOLDER_PREFIX = 'global_'
PLACEHOLDERS_FILENAME = 'placeholders_config.json'

INLINE_TEXT_PATTERN = r'\[{2}(.+)\]{2}'
IMAGE_PATTERN = '![{}]({}/{})'
SEGMENT_REGEX = r'\<string[^>]*>'
SEGMENT_NAME_REGEX = r' name="([^"]+)"'

TEXT_EMAIL_PLACEHOLDER_SEPARATOR = '\n\n'
HTML_PARSER = 'lxml'
LOCALE_PLACEHOLDER = '{link_locale}'

DEFAULT_LOCALE = 'en'
DEFAULT_WORKER_POOL = 10
