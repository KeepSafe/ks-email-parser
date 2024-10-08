import os
from setuptools import setup, find_packages

version = '0.3.2'

install_requires = [
    'Markdown < 3',
    'beautifulsoup4 < 5',
    'inlinestyler==0.2.1',
    'pystache < 0.7',
    'lxml < 5',
    'parse < 2'
]

tests_require = [
    'pytest >= 8',
    'coverage >= 7',
    'flake8 < 4',
]

devtools_require = [
    'twine',
    'build',
]


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()

setup(
    name='ks-email-parser',
    version=version,
    description=('A command line tool to render HTML and text emails of markdown content.'),
    classifiers=[
        'License :: OSI Approved :: BSD License', 'Intended Audience :: Developers', 'Programming Language :: Python'
    ],
    author='Keepsafe',
    author_email='support@getkeepsafe.com',
    url='https://github.com/KeepSafe/ks-email-parser',
    license='Apache',
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        'tests': tests_require,
        'devtools': devtools_require,
    },
    entry_points={'console_scripts': ['ks-email-parser = email_parser.cmd:main']},
    include_package_data=True)

