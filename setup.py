#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='rediset',
    version='0.12.0',
    description='Composable, cacheable, lazy trees of Redis set operations',
    author='Jamie Matthews',
    author_email='jamie.matthews@gmail.com',
    url='https://github.com/j4mie/rediset',
    license = 'Public Domain',
    packages=find_packages(),
    install_requires=['redis'],
    classifiers = [
        'Programming Language :: Python',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Operating System :: MacOS :: MacOS X',
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
    ],
)
