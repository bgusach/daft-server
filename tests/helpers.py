# coding: utf-8


class MockSocket(object):
    """
    Socket-like class for testing purposes

    """

    def __init__(self, contents):
        self._contents = contents

    def recv(self, len):
        result = self._contents[:len]
        self._contents = self._contents[len:]

        return result

