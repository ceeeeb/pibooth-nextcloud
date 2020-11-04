
=================
pibooth-nextcloud
=================

|PythonVersions| |PypiPackage| |Downloads|

``pibooth-nextcloud`` is a plugin for the `pibooth <https://github.com/pibooth/pibooth>`_
application.

This plugin adds the photo upload to a `Nextcloud Server`_.
It requires an internet connection to work

Install
-------

::

    $ pip3 install pibooth-nextcloud


Configuration
-------------

This is the extra configuration options that can be added in the ``pibooth``
configuration):

.. code-block:: ini


    [NEXTCLOUD]
    # Enable upload on  Nextcloud
    activate = True

    # URL of server to upload
    host_nextcloud = https://<Server nextcloud>

    # Root directory where Nextcloud stores photos
    rep_photos_nextcloud = Photos

    # Album where pictures are uploaded
    album_name = suubdir

    # User login for nextcloud account
    user_nextcloud = user_nextcloud

    # User password for nextcloud account
    pass_nextcloud = pwd_nextcloud



.. note:: Edit the configuration by running the command ``pibooth --config``.


Note
-----


.. |PythonVersions| image:: https://img.shields.io/badge/python-3.0+-red.svg
   :target: https://www.python.org/downloads
   :alt: Python 3.0+

.. |PypiPackage| image:: https://badge.fury.io/py/pibooth-nextcloud.svg
   :target: https://pypi.org/project/pibooth-nextcloud
   :alt: PyPi package

.. |Downloads| image:: https://img.shields.io/pypi/dm/pibooth-nextcloud?color=purple
   :target: https://pypi.org/project/pibooth-nextcloud
   :alt: PyPi downloads
