#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
import os.path as p

VERSION = open(p.join(p.dirname(p.abspath(__file__)), 'VERSION')).read().strip()

setup(
    name='zrpc',
    version=VERSION,
    description='Simple ZeroMQ-based RPC.',
    author='Zachary Voase',
    author_email='z@dvxhouse.com',
    url='http://github.com/zacharyvoase/zrpc',
    packages=find_packages(where='lib'),
    package_dir={'': 'lib'},
    install_requires=[
        'pyzmq>=2.1.10',
        'Logbook==0.3',
        'PyMongo==2.1',
    ],
)
