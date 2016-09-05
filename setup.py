# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

import codecs

__version__ = '0.1.0'

def file_content(filename):
    return codecs.open(filename, 'r', 'utf-8').read()

setup(
    name='ertza',
    version=__version__,
    packages = find_packages(),
    description="Firmware found in Eisla product range by ExMachina SAS.",
    long_description=file_content('README.md'),
    author="Benoit Rapidel, ExMachina SAS",
    author_email="benoit.rapidel+devs@exmachina.fr",
    url="http://github.org/exmachina-dev/ertza.git",
    package_data={'': ['LICENSE']},
    include_package_data=True,
    install_requires=[],
    license=file_content('LICENSE'),
    platforms = ["Beaglebone"],
    entry_points = {
        'console_scripts': [
            'ertza = ertza.ertza:main'
        ]
    },
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ),
)
