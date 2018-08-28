# coding: utf-8

import socket as soc
import argparse
from textwrap import dedent


CRLF = b'\r\n'


def main(host, port, connection_count):
    print(locals())

    socks = []

    for _ in range(connection_count):
        client_socket = soc.socket(soc.AF_INET, soc.SOCK_STREAM)

        client_socket.connect((host, port))
        raw_request = CRLF.join([
            x.encode('utf-8')
            for x in ['GET / HTTP/1.1', f'Host: {host}:{port}', '', '']
        ])

        client_socket.sendall(raw_request)
        client_socket.recv(2000)

        socks.append(client_socket)

        print('Socket count:', len(socks))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default=8888, type=int)
    parser.add_argument('--connections', default=1, type=int)

    args = parser.parse_args()
    main(args.host, args.port, args.connections)

