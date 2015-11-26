# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

import codecs

__version__ = '0.0.2'

def file_content(filename):
    return codecs.open(filename, 'r', 'utf-8').read()

setup(
    name='Ertza',
    version=__version__,
    packages = find_packages(),
    description="Firmware found in Eisla product range by ExMachina SAS.",
    long_description=file_content('README.rst'),
    author="Benoit Rapidel, ExMachina SAS",
    author_email="benoit.rapidel+devs@exmachina.fr",
    url="http://github.org/exmachina-dev/ertza.git",
    package_data={'': ['COPYING']},
    include_package_data=True,
    install_requires=[],
    license=file_content('COPYING'),
    platforms = ["Beaglebone"],
    entry_points = {
        'console_scripts': [
            'ertza = ertza.Ertza:main'
        ]
    },
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
