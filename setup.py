import os
from setuptools import setup, find_packages

version = '0.3.2'

install_requires = [
    'Markdown < 3',
    'beautifulsoup4 < 5',
    'inlinestyler==0.2.1',
    'pystache < 0.6',
    'parse < 2'
]

tests_require = [
    'nose',
    'flake8==2.5.4',
    'coverage',
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
    tests_require=tests_require,
    extras_require={
        'tests': tests_require,
        'devtools': devtools_require,
    },
    entry_points={'console_scripts': ['ks-email-parser = email_parser.cmd:main']},
    include_package_data=True)

