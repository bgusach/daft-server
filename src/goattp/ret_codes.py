# coding: utf-8

from __future__ import unicode_literals


class HTTPError(Exception):
    pass


class BadRequest(HTTPError):
    status_code = b'400 Bad Request'

