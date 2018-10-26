# coding: utf-8

from __future__ import unicode_literals

from typing import NamedTuple
import sys
import socket as soc

from . import ret_codes

CRLF = b'\r\n'
DOUBLE_CRLF = CRLF * 2
line_endings = [CRLF, b'\r', b'\n']


def log(msg):
    print('goattp:', msg, file=sys.stderr)


class Headers(object):

    def __init__(self, pairs=None):
        self._cont = {}

        if pairs is None:
            pairs = []

        for key, val in pairs:
            self.add(key, val)

    def add(self, header, value):
        header = self._normalize_key(header)
        self._cont.setdefault(header, []).append(value)

    def __getitem__(self, header):
        return ', '.join(self._cont[self._normalize_key(header)])

    def get(self, key, default=None):
        return ', '.join(self._cont.get(key, [self._normalize_value(default)]))

    def items(self):
        return self._cont.items()

    @staticmethod
    def _normalize_key(key):
        return '-'.join(segment.title() for segment in key.split('-'))

    @staticmethod
    def _normalize_value(key):
        return str(key)

    @classmethod
    def from_lines(cls, lines):
        self = cls()

        for line in lines:
            key, _, value = line.partition(':')
            self.add(key.strip(), value.strip())

        return self

    def to_lines(self):
        return [
            '%s: %s' % (key, ', '.join(values))
            for key, values in self.items()
        ]


def import_by_fqpn(fqpn):
    """
    Imports an object by FQPN in the form of module_fqpn:object_fqpn

    Both module and object FQPN can be as nested as desired, e.g.: pack.mod1:class3.member
    If no object_fqpn part is provided, module is returned.

    """
    mod_fqpn, _, obj_fqpn = fqpn.partition(':')

    obj = __import__(mod_fqpn)

    for segment in obj_fqpn.split('.'):
        obj = getattr(obj, segment)

    return obj


class BodyBuffer(object):

    def __init__(
        self,
        socket: soc.socket,
        content_length: int=float('inf'),
        preallocated: bytes=b'',
        buffer_size: int=4096,
    ):
        self._buffered = preallocated
        self._socket = socket
        self._socket_bytes_left = content_length - len(preallocated)
        self._buffer_size = buffer_size
        self._socket_exhausted = False

    def read(self, size: int=None) -> bytes:
        """
        Reads `size` bytes. If `size` not provided, all the contents will be delivered.

        """
        if size is None:
            size = len(self._buffered) + self._socket_bytes_left

        self._fill_buffer(size)
        result = self._buffered[:size]
        self._buffered = self._buffered[size:]

        return result

    def _fill_buffer(self, desired_buffered_size):
        """
        Reads from socket into buffer until buffer has at least the desired length
        or the socket is exhausted.


        """
        while len(self._buffered) < desired_buffered_size:
            # Avoid reading further than content length
            max_allowed = min(self._buffer_size, self._socket_bytes_left)
            new_data = self._socket.recv(max_allowed)

            if not new_data:
                self._socket_exhausted = True
                return

            self._socket_bytes_left -= len(new_data)
            self._buffered += new_data

        return True

    def readline(self) -> bytes:
        while True:

            for line_ending in line_endings:
                line, succ, rest = self._buffered.partition(line_ending)

                if succ:
                    self._buffered = rest
                    return line + succ

            if self._socket_exhausted:
                rest = self._buffered
                self._buffered = b''
                return rest

            # FIXME [bgu 27-08-2018]: this will loop forever on broken connections
            self._fill_buffer(self._buffer_size)

    def readlines(self, hint=None):
        return list(iter(self.readline, b''))

    def __iter__(self):
        pass


class Request(NamedTuple):
    verb: str
    resource: str
    version: str
    headers: Headers
    body: BodyBuffer


def parse_http_socket(soc: soc.socket) -> Request:
    """
    Given a freshly opened socket for an HTTP request, the headers and 
    a buffer containing the request body is returned
    
    """
    try:
        return _parse_socket(soc)

    except Exception as exc:
        raise ret_codes.BadRequest from exc


def _parse_socket(soc: soc.socket) -> Request:
    buff = b''

    while True:
        # Small buffer, we just want the headers
        new_data = soc.recv(512)

        if not new_data:
            # Somebody hung up on us :(
            raise Exception('implement error here!')

        buff += new_data

        metadata, succ, body_start = buff.partition(DOUBLE_CRLF)

        if succ:
            break

    start_line, *header_lines = metadata.decode('ascii').split('\r\n')
    verb, resource, version = _parse_start_line(start_line)
    headers = Headers.from_lines(header_lines)

    contents_length = int(headers.get('content-length', 0))

    return Request(
        verb,
        resource,
        version,
        headers,
        BodyBuffer(soc, contents_length, body_start),
    )


def _parse_start_line(line):
    verb, resource, version = (it.strip() for it in line.split(' '))
    return verb.upper(), resource, version.upper()

