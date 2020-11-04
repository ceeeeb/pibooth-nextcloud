#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from io import open
import os.path as osp
from setuptools import setup


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
import pibooth_nextcloud as plugin


def main():
    setup(
        name=plugin.__name__,
        version=plugin.__version__,
        description=plugin.__doc__,
        long_description=open(osp.join(HERE, 'README.rst'), encoding='utf-8').read(),
        long_description_content_type='text/x-rst',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Other Environment',
            'Intended Audience :: Developers',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: MIT License',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.6',
            'Natural Language :: English',
            'Topic :: Multimedia :: Graphics :: Capture :: Digital Camera',
        ],
        author="Ceeeeb",
        url="https://github.com/ceeeeb/pibooth-nextcloud",
        download_url="https://github.com/ceeeeb/pibooth-nextcloud/archive/{}.tar.gz".format(plugin.__version__),
        license='MIT license',
        platforms=['unix', 'linux'],
        keywords=[
            'Raspberry Pi',
            'camera',
            'photobooth' ,
            'nextcloud'
        ],
        py_modules=['pibooth_nextcloud'],
        install_requires=[
            'pibooth>=2.0.0',
            'pyocclient==0.4',
            'qrcode>=6.1'
        ],
        options={
            'bdist_wheel':
                {'universal': True}
        },
        zip_safe=False,  # Don't install the lib as an .egg zipfile
        entry_points={'pibooth': ["pibooth_nextcloud = pibooth_nextcloud"]},
    )


if __name__ == '__main__':
    main()
