#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='rediset',
    version='0.0.1',
    description='Composable, cacheable, lazy trees of Redis set operations',
    author='Jamie Matthews',
    author_email='jamie.matthews@gmail.com',
    url='http://github.com/j4mie/rediset',
    py_modules=['rediset'],
    install_requires=['redis>=2.4.11'],
)
