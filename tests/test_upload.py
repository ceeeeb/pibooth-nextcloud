# -*- coding: utf-8 -*-

"""Tests of the choice between synchronization and upload, and of the
upload thread error handling."""

import threading
from unittest import mock

import pytest

import pibooth_nextcloud as plugin


class Config(object):

    def __init__(self, synchronize):
        self.synchronize = synchronize

    def getboolean(self, section, option):
        assert (section, option) == ('NEXTCLOUD', 'useSynchronize')
        return self.synchronize


@pytest.mark.parametrize('synchronize, which, expected', [
    (True, '/usr/bin/nextcloudcmd', True),
    (True, None, False),
    (False, '/usr/bin/nextcloudcmd', False),
])
def test_synchronize_only_with_nextcloudcmd(monkeypatch, synchronize, which, expected):
    monkeypatch.setattr(plugin.shutil, 'which', lambda name: which)
    assert plugin._use_synchronize(Config(synchronize)) is expected


class ImmediateThread(object):

    def __init__(self, target, daemon=None):
        self.target = target

    def start(self):
        self.target()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(plugin.threading, 'Thread', ImmediateThread)
    nextcloud = mock.Mock(_upload_lock=threading.Lock(), check_quota=False, useSynchronize=False,
                          rep_photos_nextcloud='/Photos/', album_name='TEST')
    return mock.Mock(nextcloud=nextcloud, previous_picture_file='/tmp/2026-10-05_pibooth.jpg')


def test_picture_is_uploaded(app):
    plugin.state_processing_exit(app, None)
    app.nextcloud.upload_photos.assert_called_once_with(
        '/tmp/2026-10-05_pibooth.jpg', '/Photos/TEST/2026-10-05_pibooth.jpg', app.nextcloud.activate_state)


def test_upload_error_is_logged_and_releases_the_lock(app, caplog):
    app.nextcloud.upload_photos.side_effect = FileNotFoundError('nextcloudcmd')
    plugin.state_processing_exit(app, None)
    assert 'Nextcloud upload failed' in caplog.text
    assert app.nextcloud.last_error == 'Erreur upload'
    assert app.nextcloud._upload_lock.acquire(blocking=False)
