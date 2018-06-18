# coding: utf-8

from __future__ import unicode_literals

import socket as soc
import time
import os
import sys
import typing
import click
import traceback
from textwrap import dedent


class Request(typing.NamedTuple):
    verb: str
    resource: str
    version: str
    headers: typing.Mapping[str, str] = None


class Response(typing.NamedTuple):
    status_code: str
    body: typing.List[str] = ''
    headers: typing.Mapping[str, str] = None


class HTTPError(Exception):
    pass


class BadRequest(HTTPError):
    status_code = '400 Bad Request'


CRLF = b'\r\n'
DOUBLE_CRLF = CRLF + CRLF


def split_request(socket):
    print('We got a request!!')
    buff = b''

    while True:
        buff += socket.recv(1024)

        head, success, tail = buff.partition(DOUBLE_CRLF)

        if success:
            return buff, tail


def parse_headers(raw_headers: bytes):
    request_line, *header_lines = raw_headers.decode('ascii').split(CRLF.decode('ascii'))

    verb, resource, version = (it.strip() for it in request_line.split(' '))

    pairs = [x.partition(':') for x in header_lines]
    headers = {key.strip(): value.strip() for (key, _, value) in pairs}

    return verb.upper(), resource, version.upper(), headers


def parse_request(client_socket: soc.socket):

    try:
        raw_headers, body_head = split_request(client_socket)

        # Ignore the body for the moment
        return Request._make(parse_headers(raw_headers))

    except Exception:
        print('Ouch, bad request')
        traceback.print_exc()

        raise BadRequest


def get_response(req: Request):
    return Response(
        status_code='200 OK',
        body=[
            f'You made a {req.verb} {req.version} request on the resource {req.resource}.',
            f'Parsed headers: {req.headers}',
        ]
    )


def handle_request(client_socket):

    try:
        req = parse_request(client_socket)
        resp = get_response(req)

    except BadRequest as exc:
        resp = Response(status_code=exc.status_code)

    lines = ['HTTP/1.1 {resp.status_code}', ''] + resp.body + ['']
    raw_response = CRLF.join([l.encode('utf-8') for l in lines])

    client_socket.sendall(raw_response)


@click.command()
@click.option('-h', '--host', default='localhost')
@click.option('-p', '--port', default=8888)
@click.option('-q', '--queue-size', default=5)
@click.option('-d', '--delay', default=0)
def serve(host, port, queue_size, delay):

    with soc.socket(soc.AF_INET, soc.SOCK_STREAM) as socket_server:
        socket_server.setsockopt(soc.SOL_SOCKET, soc.SO_REUSEADDR, 1)
        socket_server.bind((host, port))
        socket_server.listen(queue_size)

        print('Serving on %s' % port)

        while True:
            client_socket, client_address = socket_server.accept()

            pid = os.fork()

            if pid == 0:  # Kiddo process
                socket_server.close()
                handle_request(client_socket)
                time.sleep(delay)
                client_socket.close()
                sys.exit(0)

            else:  # Daddy process
                client_socket.close()


if __name__ == '__main__':
    serve()
