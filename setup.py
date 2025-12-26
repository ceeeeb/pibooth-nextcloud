#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from io import open
import os.path as osp
from setuptools import setup


HERE = osp.abspath(osp.dirname(__file__))

# Read version from module without importing it
with open(osp.join(HERE, 'pibooth_nextcloud.py'), encoding='utf-8') as f:
    content = f.read()
    version = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content).group(1)


def main():
    setup(
        name='pibooth_nextcloud',
        version=version,
        description="Pibooth plugin to upload photos to Nextcloud",
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
        download_url="https://github.com/ceeeeb/pibooth-nextcloud/archive/{}.tar.gz".format(version),
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
