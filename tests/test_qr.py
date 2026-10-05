# -*- coding: utf-8 -*-

"""Tests of the QR code kept on the wait screen."""

from unittest import mock

import pygame

import pibooth_nextcloud as plugin


def make_app(position='top-left', margin=62, shown=True):
    nextcloud = mock.Mock(printQrCode=shown, qr_image=pygame.Surface((185, 185)),
                          qr_position=position, qr_margin=margin)
    return mock.Mock(nextcloud=nextcloud)


def make_win():
    win = mock.Mock()
    win.get_rect.return_value = pygame.Rect(0, 0, 1600, 900)
    return win


def test_qr_code_is_drawn_again_at_each_frame():
    app, win = make_app(), make_win()
    plugin.state_wait_do(app, win)
    plugin.state_wait_do(app, win)
    assert win.surface.blit.call_count == 2
    assert win.surface.blit.call_args[0][1] == (62, 62)


def test_bottom_left_position():
    app, win = make_app('bottom-left'), make_win()
    plugin.state_wait_do(app, win)
    assert win.surface.blit.call_args[0][1] == (62, 900 - 185 - 62)


def test_hidden_qr_code_is_not_drawn():
    app, win = make_app(shown=False), make_win()
    plugin.state_wait_do(app, win)
    win.surface.blit.assert_not_called()
