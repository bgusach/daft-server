# coding: utf-8

from __future__ import unicode_literals


from operator import itemgetter
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


class Request(typing.NamedTuple):
    verb: bytes
    resource: bytes
    version: bytes
    headers: typing.Mapping[bytes, bytes]
    body: bytes


class Response(typing.NamedTuple):
    status_code: str
    body: typing.List[str] = ()
    headers: typing.Mapping[str, str] = None


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
            status, headers, body_lines = self._get_response(req)

        except BadRequest as exc:
            status = b'400 Bad Request'

            # TODO: extend headers
            headers = Headers()
            body_lines = []

        # From WSGI specification: response headers must not be sent until there
        # is actual body data available, or until the application's returned
        # iterable is exhausted

        # TODO: handle all necessary headers (content-length & friends)
        headers_sent = False

        for line in body_lines:
            if line and not headers_sent:
                # Send headers
                client_socket.send(b' '.join([b'HTTP/1.1', status, CRLF]))

                log('Sending headers:')
                for header_line in headers.get_formatted_lines():
                    client_socket.send(header_line + CRLF)
                    log(header_line)

                client_socket.send(CRLF)
                headers_sent = True

            client_socket.send(line + CRLF)

    def _parse_request(self, client_socket: soc.socket):

        try:
            start_line, raw_headers, body_head = self._split_request(client_socket)
            verb, resource, version = self._parse_start_line(start_line)
            headers = self._parse_headers(raw_headers)
            log(headers)

            # Easy hack: push everything in memory. Should actually use a buffer
            content_len = int(headers.get('Content-Length', 0))
            body = body_head + client_socket.recv(content_len - len(body_head))

            return Request(
                verb,
                resource,
                version,
                headers,
                body,
            )

        except Exception:
            log('Ouch, bad request')
            traceback.print_exc()

            raise BadRequest

    @staticmethod
    def _parse_start_line(line):
        verb, resource, version = (it.strip() for it in line.split(b' '))
        return verb.upper(), resource, version.upper()

    @staticmethod
    def _split_request(socket: soc.socket):
        """
        Returns a tuple (start line, raw headers, head of body)
        """
        pprint('We got a request!!')
        buff = b''

        # Get start line
        while True:
            buff += socket.recv(1024)
            head, success, tail = buff.partition(CRLF)

            if success:
                start_line = head
                buff = tail
                break

        # Split headers and body
        while True:
            head, success, tail = buff.partition(DOUBLE_CRLF)

            if success:
                return start_line, buff, tail

            buff += socket.recv(1024)

    @staticmethod
    def _parse_headers(raw_headers: bytes):
        header_lines = raw_headers.split(CRLF)

        get_key_and_value = itemgetter(0, 2)
        pairs = [get_key_and_value(x.partition(b':')) for x in header_lines]
        return Headers(pairs)

    def _get_response(self, req: Request):

        returned_status = None
        returned_headers = None

        def start_response(status, response_headers, exc_info=None):
            nonlocal returned_status
            # TODO: think of a reasonable encoding approach
            returned_status = to_bytes(status)

            nonlocal returned_headers
            log(response_headers)
            returned_headers = [(to_bytes(k), to_bytes(v)) for k, v in response_headers]
            log(returned_headers)

            def write(data):
                raise Exception('Sorry mate, we don\'t support the imperative write API')

            return write

        body_lines = self._app(
            {
                'wsgi.version': (1, 0),
                'wsgi.url_scheme': 'http',
                'wsgi.input': io.BytesIO(req.body),
                'wsgi.errors': sys.stderr,
                'wsgi.multithread': False,
                'wsgi.multiprocess': True,
                'wsgi.run_once': False,
                'REQUEST_METHOD': req.verb,
                'SCRIPT_NAME': '',
                'PATH_INFO': req.resource,
                'CONTENT_TYPE': req.headers.get(b'Content-Type', ''),
                'CONTENT_LENGTH': req.headers.get(b'Content-Length', ''),
                'SERVER_NAME': self._host,
                'SERVER_PORT': str(self._port),
            },
            start_response,
        )

        if not returned_status or not returned_headers:
            raise Exception('App did not provide status or headers')

        return returned_status, Headers(returned_headers), body_lines


def to_bytes(val):
    if isinstance(val, str):
        return val.encode('ascii')

    if isinstance(val, numbers.Number):
        return str(val).encode('ascii')

    return bytes(val)  # And hope for the best


def wsgi_app(env, start_response):
    print('WSGI APP CALLED!!')
    print(env)
    response = [b'heeeeey', b'amigooo']

    # TODO: fix the content-length. it should be based on bytes and not unicode strings
    start_response(
        '200 OK',
        [('Content-Type', 'text/html'), ('Content-Length', sum(map(len, response)))]
    )
    return response


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
    mod, _, callable = wsgi_callable.partition(':')

    if not mod or not callable:
        raise Exception('Could not parse path to WSGI app')

    app = getattr(__import__(mod), callable)

    server = DaftServer(host, port, queue_size, app, delay)

    server.serve()


if __name__ == '__main__':
    serve()
