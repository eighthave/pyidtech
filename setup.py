#!/usr/bin/env python

from setuptools import setup
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='pyidtech',
      version='0.1',
      description='read data from ID TECH credit card readers',
      long_description=read('README.txt'),
      license='PSF License',
      author='Hans-Christoph Steiner',
      author_email='hans@eds.org',
      url='https://github.com/eighthave/pyidtech',
      py_modules = ['idtech'],
      install_requires = ['pyserial'],
      classifiers = [
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Python Software Foundation License',
          'Programming Language :: Python :: 2',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Office/Business :: Financial :: Point-Of-Sale',
          'Topic :: System :: Hardware'],
)

