#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='pibooth_forget_button',
    version='1.0.0',
    description="Pibooth plugin to add a third button for forgetting photos",
    long_description="Adds a dedicated GPIO button to move photos to the forget folder",
    author="Ceeeeb",
    url="https://github.com/ceeeeb/pibooth-nextcloud",
    license='MIT license',
    platforms=['unix', 'linux'],
    keywords=['Raspberry Pi', 'photobooth', 'pibooth', 'button'],
    py_modules=['pibooth_forget_button'],
    install_requires=['pibooth>=2.0.0'],
    zip_safe=False,
    entry_points={'pibooth': ["pibooth_forget_button = pibooth_forget_button"]},
)
