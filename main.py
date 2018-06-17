# coding: utf-8

from __future__ import unicode_literals

import socket as soc
import time
import os
import sys
import typing
import click


class Request(typing.NamedTuple):
    verb: str
    resource: str
    version: str
    headers: typing.Mapping[str, str]


CRLF = b'\r\n'
DOUBLE_CRLF = CRLF + CRLF


def split_request(socket):
    buff = []

    while True:
        chunk = socket.recv(1024)

        head, success, tail = chunk.partition(DOUBLE_CRLF)

        buff.append(head)

        if success:
            return b''.join(buff), tail


def parse_headers(raw_headers: bytes):
    request_line, *header_lines = raw_headers.decode('ascii').split(CRLF.decode('ascii'))

    verb, resource, version = (it.strip().upper() for it in request_line.split(' '))

    pairs = [x.partition(':') for x in header_lines]
    headers = {key.strip(): value.strip() for (key, _, value) in pairs}

    return verb, resource, version, headers


def parse_request(client_socket: soc.socket):
    raw_headers, body_head = split_request(client_socket)

    # Ignore the body
    return Request._make(parse_headers(raw_headers))


def handle_request(client_socket):
    print('WOOOOOOWWW we\'ve got a request!!!')
    request = parse_request(client_socket)
    print(request)

    # chunk = client_socket.recv(1024)
    # raw_headers, _, body = chunk.partition(b'\r\n\r\n')
    # request_line, *header_pairs = raw_headers.decode('ascii').splitlines()
    # method, resource, http_version = request_line.split(' ')
    #
    # headers = {}
    #
    # for header_pair in header_pairs:
    #     key, _, value = header_pair.partition(':')
    #     headers[key.strip()] = value.strip()
    #
    # response = dedent(f'''\
    #     HTTP/1.1 200 OK
    #
    #     You made a {method} {http_version} request on the resource {resource}.
    #     Parsed headers: {headers}
    # ''').encode('utf-8')
    #
    # client_socket.sendall(response)


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
