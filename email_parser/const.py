SUBJECT_EXTENSION = '.subject'
SUBJECT_RESEND_EXTENSION = '.resend.subject'
SUBJECT_A_EXTENSION = '.a.subject'
SUBJECT_B_EXTENSION = '.b.subject'
TEXT_EXTENSION = '.text'
HTML_EXTENSION = '.html'
GLOBAL_PLACEHOLDERS_EMAIL_NAME = 'global'

PLACEHOLDERS_FILENAME = 'placeholders_config.json'

INLINE_TEXT_PATTERN = r'\[{2}(.+)\]{2}'
IMAGE_PATTERN = '![{}]({}/{})'

LINK_LOCALE_MAPPINGS_FILENAME = 'link_locale_mappings.json'
SEGMENT_REGEX = r'\<string[^>]*>'
SEGMENT_NAME_REGEX = r' name="([^"]+)"'
SUBJECTS_PLACEHOLDERS = ['subject_b', 'subject_a', 'subject_resend', 'subject']

TEXT_EMAIL_PLACEHOLDER_SEPARATOR = '\n\n'
HTML_PARSER = 'lxml'
SUBJECTS_PLACEHOLDERS = ['subject', 'subject_a', 'subject_b', 'subject_resend']
LINK_LOCALE = '{link_locale}'
