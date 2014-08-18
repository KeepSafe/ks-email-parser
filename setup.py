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
      py_modules=['parser'],
      namespace_packages=[],
      install_requires = [],
      entry_points={
          'console_scripts': ['ks-email-parser = parser:main']
      },
      include_package_data = False)
