import os
from setuptools import setup

version = '0.0.1'


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()


setup(name='email-localization',
      version=version,
      description=('A command line tool to render HTML and text emails of markdown content.'),
      long_description='\n\n'.join((read('README.md'), read('CHANGELOG'))),
      classifiers=[
          'License :: OSI Approved :: BSD License',
          'Intended Audience :: Developers',
          'Programming Language :: Python'],
      author='Keepsafe',
      author_email='support@getkeepsafe.com',
      url='https://github.com/KeepSafe/email-localization',
      license='Apache',
      py_modules=['email_parser'],
      namespace_packages=[],
      install_requires = ['Markdown==2.4.1', 'beautifulsoup4==4.3.2', 'nose==1.3.3', 'pystache==0.5.4'],
      entry_points={
          'console_scripts': ['ks-email-parser = email_parser:main']
      },
      include_package_data = False)
