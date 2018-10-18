# coding: utf-8

from goattp.tools import parse_http_socket

from helpers import MockSocket


def test_parse_get_request():
    sock = MockSocket(b'\r\n'.join([
        b'GET /resource HTTP/1.1',
        b'Accept: */*',
        b'Accept-Encoding: gzip, deflate, compress',
        b'Host: www.lol-example.com',
        b'User-Agent: troll-agent',
        b'\r\n',
    ]))

    req = parse_http_socket(sock)

    assert req.verb == 'GET'
    assert req.resource == '/resource'
    assert req.headers['accept'] == '*/*'
    assert req.headers['accept-encoding'] == 'gzip, deflate, compress'
    assert req.headers['host'] == 'www.lol-example.com'
    assert req.headers['user-agent'] == 'troll-agent'
    assert req.body.read() == b''

