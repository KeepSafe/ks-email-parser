import os
from setuptools import setup, find_packages
from pip.download import PipSession

try:
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirements

version = '0.2.15'


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()


install_reqs = parse_requirements('requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]
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
    install_requires=reqs,
    entry_points={'console_scripts': ['ks-email-parser = email_parser.cmd:main']},
    include_package_data=True)
