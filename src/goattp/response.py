# coding: utf-8

from __future__ import unicode_literals

from . tools import log
from . tools import Request
from . tools import Headers
import traceback


def get_response(req: Request, app):

    returned_status = None
    returned_headers = None

    def start_response(status, response_headers, exc_info=None):
        # TODO [bgusach 22.10.2018]: process exc_info
        nonlocal returned_status
        returned_status = status

        nonlocal returned_headers
        returned_headers = Headers(response_headers)

    body_lines = iter(app(self._get_env_for_request(req), start_response))

    if not returned_status or returned_headers is None:
        raise Exception('App did not provide status or headers')

    # Delay till the very last moment sending metadata
    first_line = next(body_lines)

    log('Sending start line and headers')
    client_socket.send(f'HTTP/1.1 {returned_status}\r\n'.encode('ascii'))

    for header_line in returned_headers.to_lines():
        client_socket.send(f'{header_line}\r\n'.encode('ascii'))

    client_socket.send(CRLF)

    for line in chain([first_line], body_lines):
        client_socket.send(line)


