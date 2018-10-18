# coding: utf-8

from __future__ import unicode_literals


from goattp.tools import BodyBuffer


class MockSocket(object):

    def __init__(self, contents):
        self._contents = contents

    def read(self, len):
        result = self._contents[:len]
        self._contents = self._contents[len:]

        return result


def test_basic():
    b = BodyBuffer(socket=MockSocket(b'hello there\r\namigo'))

    assert b.read(5) == b'hello'
    assert b.read(1) == b' '
    assert b.read(5) == b'there'


def test_line():
    b = BodyBuffer(socket=MockSocket(b'hello there\r\namigo'))

    assert b.readline() == b'hello there\r\n'
    assert b.readline() == b'amigo'


def test_lines():
    b = BodyBuffer(socket=MockSocket(b'hello there\r\namigo'))
    assert b.readlines() == [b'hello there\r\n', b'amigo']


def test_preallocated():
    b = BodyBuffer(preallocated=b'live', socket=MockSocket(b' long and prosper'))
    assert b.read(500) == b'live long and prosper'


def test_with_content_length():
    b = BodyBuffer(
        preallocated=b'live',
        socket=MockSocket(b' long and prosper'),
        content_length=8,
    )

    assert b.read(500) == b'live long'
    assert b.read(500) == b''
