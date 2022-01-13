import os
from setuptools import setup, find_packages

version = '0.3.2'

install_requires = [
    'Markdown==2.6.11',
    'beautifulsoup4==4.4.1',
    'inlinestyler==0.2.1',
    'pystache==0.5.4',
    'parse==1.8.2'
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
    long_description='\n\n'.join((read('README.md'), read('CHANGELOG'))),
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

