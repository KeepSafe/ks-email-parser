import os
from setuptools import setup, find_packages

version = '0.3.2'


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()


with open('requirements.txt', 'r') as f:
    install_reqs = [
        s for s in [
            line.strip('\r\n') for line in f
        ] if not s.startswith('#') and s != ''
    ]

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
    install_requires=install_reqs,
    entry_points={'console_scripts': ['ks-email-parser = email_parser.cmd:main']},
    include_package_data=True)
