# coding: utf-8

from __future__ import unicode_literals


import socket as soc
import time
import os
import sys
import signal
import errno
import traceback
from itertools import chain

from goattp.tools import parse_http_socket
from goattp.tools import CRLF

from .tools import Headers
from .tools import log
from . import ret_codes


def on_child_signal(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except OSError:
            return

        if pid == 0:
            return


class GoatTTPSever(object):

    def __init__(self, host, port, queue_size, app, delay=0):
        self._host = host
        self._port = port
        self._queue_size = queue_size
        self._app = app
        self._delay = delay

    def serve(self):
        with soc.socket(soc.AF_INET, soc.SOCK_STREAM) as socket_server:
            socket_server.setsockopt(soc.SOL_SOCKET, soc.SO_REUSEADDR, 1)
            socket_server.bind((self._host, self._port))
            socket_server.listen(self._queue_size)

            log('Serving on %s' % self._port)

            signal.signal(signal.SIGCHLD, on_child_signal)

            while True:

                try:
                    client_socket, client_address = socket_server.accept()

                except IOError as exc:
                    # This will be triggered if a SIGCHLD comes while waiting
                    if exc.errno == errno.EINTR:
                        continue

                    raise

                pid = os.fork()

                if pid == 0:  # Kiddo process
                    socket_server.close()
                    self._handle_request(client_socket)
                    time.sleep(self._delay)
                    client_socket.close()
                    sys.exit(0)

                else:  # Daddy process
                    client_socket.close()

    def _handle_request(self, client_socket):
        metadata_sent = False
        metadata_set = False
        status = None
        headers = None

        def start_response(_status, _headers, exc_info=None):
            # TODO [bgusach 26.10.2018]: check that no hop-by-hop headers have been sent
            # or other errors in the headers
            nonlocal status
            nonlocal headers
            nonlocal metadata_set

            if exc_info and metadata_sent:
                # Well, too late to change your mind!
                raise exc_info[1].with_traceback(exc_info[2])

            if metadata_set and not exc_info:
                raise Exception('Status/headers already set!! (and no error provided)')

            status = _status
            headers = Headers(_headers)
            metadata_set = True

        try:
            req = parse_http_socket(client_socket)
            body = self._app(self._get_env_for_request(req), start_response)

            if not metadata_set:
                raise Exception('App did not set status/headers with `start_response`')

        except ret_codes.BadRequest:
            status = ret_codes.BadRequest.status_code
            headers = Headers()
            body = [traceback.format_exc().encode('ascii')]

        except Exception:
            status = b'500 Server Error'
            headers = Headers()
            body = [traceback.format_exc().encode('ascii')]

        # TODO [bgusach 26.10.2018]: supply missing headers like date or server

        body = iter(body)  # It may not be an iterator

        # Delay sending metadata until we get some real data
        try:
            first_chunk = next(chunk for chunk in body if chunk)
        except StopIteration:
            first_chunk = b''

        log('Sending start line and headers')
        client_socket.send(f'HTTP/1.1 {status}\r\n'.encode('ascii'))

        for header_line in headers.to_lines():
            client_socket.send(f'{header_line}\r\n'.encode('ascii'))

        client_socket.send(CRLF)

        metadata_sent = True

        for line in chain([first_chunk], body):
            print(repr(line))
            client_socket.send(line)

    def _get_env_for_request(self, req):
        return {
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': req.body,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
            'REQUEST_METHOD': req.verb,
            'SCRIPT_NAME': '',
            'PATH_INFO': req.resource,
            'CONTENT_TYPE': req.headers.get('Content-Type'),
            'CONTENT_LENGTH': int(req.headers.get('Content-Length', 0)),
            'SERVER_NAME': self._host,
            'SERVER_PORT': self._port,
        }
