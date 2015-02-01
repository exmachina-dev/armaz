# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import codecs

__version__ = '0.0.1'

packages = [
    'ertza',
    'ertza.remotes',
    'ertza.remotes.osc',
]

scripts = [
    'bin/ertza',
]

def file_content(filename):
    return codecs.open(filename, 'r', 'utf-8').read()

setup(
    name='ertza',
    version=__version__,
    description="Armaz main program",
    long_description=file_content('README.rst'),
    author="Benoit Rapidel",
    author_email="benoit.rapidel@exmachina.fr",
    url="http://libmodbus.org",
    keywords="python motor",
    packages=packages,
    package_data={'': ['COPYING']},
    include_package_data=True,
    install_requires=[],
    license=file_content('COPYING'),
    scripts=scripts,
    zip_safe=False,
    classifiers=(
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ),
)
