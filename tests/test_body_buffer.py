# coding: utf-8

from goattp.tools import BodyBuffer

from helpers import MockSocket


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
        content_length=9,
    )

    assert b.read(500) == b'live long'
    assert b.read(500) == b''


def test_read_all():
    b = BodyBuffer(
        preallocated=b'live',
        socket=MockSocket(b' long and prosper'),
        content_length=9,
    )

    assert b.read() == b'live long'
