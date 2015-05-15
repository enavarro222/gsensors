#!/usr/bin/env python
from setuptools import setup, find_packages

#TODO; better setup
# see https://bitbucket.org/mchaput/whoosh/src/999cd5fb0d110ca955fab8377d358e98ba426527/setup.py?at=default
# for ex

setup(
    name='gsensors',
    version='1.0',
    description=' Collection of data sources wrapper (with associated gevent autonomous pseudo-thread)',
    author='Emmanuel Navarro',
    author_email='enavarro222@gmail.com',
    url='https://github.com/enavarro222/gsensors',
    packages=['gsensors'] + ['gsensors.%s' % submod for submod in find_packages('gsensors')],
)
