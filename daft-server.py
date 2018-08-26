# coding: utf-8

from __future__ import unicode_literals


import socket as soc
import time
import os
import sys
import typing
import click
import traceback
import signal
import errno
import io
import numbers

from tools import Headers
from tools import import_by_fqpn

from pprint import pprint


def log(msg):
    print('daft-server:', msg, file=sys.stderr)


def on_child_signal(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except OSError:
            return

        if pid == 0:
            return


class BodyBuffer(object):

    def __init__(self, preallocated, socket, content_length, buffer_size=4096):
        self._buffered = preallocated
        self._socket = socket
        self._bytes_left = content_length - len(preallocated)
        self._buffer_size = buffer_size

    def read(self, size) -> bytes:

        while len(self._buffered) < size:
            # Avoid reading further than content length
            bytes_to_read = min(self._buffer_size, self._bytes_left)

            new_data = self._socket.read(bytes_to_read)

            if not new_data:
                break

            self._buffered += new_data
            self._bytes_left -= len(new_data)

        result = self._buffered[:size]
        self._buffered = self._buffered[size:]

        return result

    def readline(self):
        pass

    def readlines(self, hint):
        pass

    def __iter__(self):
        pass


class Request(typing.NamedTuple):
    verb: str
    resource: str
    version: str
    headers: Headers
    body: BodyBuffer


class HTTPError(Exception):
    pass


class BadRequest(HTTPError):
    status_code = '400 Bad Request'


CRLF = b'\r\n'
DOUBLE_CRLF = CRLF + CRLF


class DaftServer(object):

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

        try:
            req = self._parse_request(client_socket)
            status, headers, response_lines = self._get_response(req)

        except BadRequest:
            status = b'400 Bad Request'

            # TODO: extend headers
            headers = Headers()
            response_lines = []

        # From WSGI specification: response headers must not be sent until there
        # is actual body data available, or until the application's returned
        # iterable is exhausted

        # TODO: handle all necessary headers (content-length & friends)
        headers_sent = False

        for line in response_lines:

            if line and not headers_sent:
                log('Sending start line and headers')
                client_socket.send(b' '.join([b'HTTP/1.1', status.encode('ascii'), CRLF]))

                for header_line in headers.to_lines():
                    client_socket.send(header_line.encode('ascii') + CRLF)

                client_socket.send(CRLF)
                headers_sent = True

            client_socket.send(line)

    def _parse_request(self, client_socket: soc.socket):
        buff = b''

        while True:
            new_data = client_socket.recv(4096)

            if not new_data:
                # Somebody hung up on us :(
                raise BadRequest

            buff += new_data

            metadata, succ, body = buff.partition(DOUBLE_CRLF)

            if succ:
               break

        start_line, *header_lines = metadata.decode('ascii').split('\r\n')
        verb, resource, version = self._parse_start_line(start_line)
        headers = Headers.from_lines(header_lines)

        contents_length = int(headers.get('content-length', 0))

        return Request(
            verb,
            resource,
            version,
            headers,
            BodyBuffer(body, client_socket, contents_length)
        )

    @staticmethod
    def _parse_start_line(line):
        verb, resource, version = (it.strip() for it in line.split(' '))
        return verb.upper(), resource, version.upper()

    def _get_response(self, req: Request):

        returned_status = None
        returned_headers = None

        def start_response(status, response_headers, exc_info=None):
            nonlocal returned_status
            returned_status = status

            nonlocal returned_headers
            returned_headers = response_headers

            def write(data):
                raise Exception('Sorry mate, we don\'t support the imperative write API')

            return write

        try:
            body_lines = self._app(self._get_env_for_request(req), start_response)
        except Exception as exc:
            log('Error from app')
            import traceback
            traceback.print_exc()
            returned_status = '500 Server Error'
            # TODO: write proper headers
            returned_headers = []
            body_lines = []

        if not returned_status or returned_headers is None:
            raise Exception('App did not provide status or headers')

        return returned_status, Headers(returned_headers), body_lines

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


class RequestHandler(object):

    def __init__(self, send, recv):
        # self._socket = socket
        self._send = send
        self._recv = recv
        self.status = None
        self._headers = None
        self._start_response_called = False
        self._headers_sent = False

    def run(self):
        pass

    def start_response(self, status, response_headers, exc_info=None):
        self.status = status
        self._headers = Headers(response_headers)

        self._start_response_called = True
        return self.write

    def _send_headers(self):
        if self._headers_sent:
            raise Exception('Headers were already sent!')

        self._send(b' '.join([b'HTTP/1.1', self.status, CRLF]))

        for line in self._headers.get_formatted_lines():
            self._send(line + CRLF)

        self._headers_sent = True

    def write(self, data):
        raise Exception('Sorry mate, we don\'t support the imperative write API')


def to_bytes(val):
    if isinstance(val, str):
        return val.encode('ascii')

    if isinstance(val, numbers.Number):
        return str(val).encode('ascii')

    return bytes(val)  # And hope for the best


@click.command()
@click.argument('wsgi-callable')
@click.option('-h', '--host', default='localhost')
@click.option('-p', '--port', default=8888)
@click.option('-q', '--queue-size', default=5)
@click.option('-d', '--delay', default=0)
def serve(wsgi_callable, host, port, queue_size, delay):
    """
    WSGI_CALLABLE: WSGI App in form module.path:callable

    """
    app = import_by_fqpn(wsgi_callable)
    server = DaftServer(host, port, queue_size, app, delay)
    server.serve()


if __name__ == '__main__':
    serve()
