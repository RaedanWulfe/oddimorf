#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Subsystem package setup file.
"""

from setuptools import setup, find_packages


setup(name='oddimorf',
      version='1.0.0',
      description='',
      long_description='',
      url='https://github.com/RaedanWulfe/oddimorf',
      author='W.L. Carstens',
      license='MIT',
      packages=find_packages(),
      keywords=[],
      classifiers=[],
      install_requires=[
          'paho-mqtt'],
      python_requires='>=3.8',
      project_urls={
          'Source': 'https://github.com/RaedanWulfe/oddimorf',
      })
