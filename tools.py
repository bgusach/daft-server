# coding: utf-8

from __future__ import unicode_literals


class Headers(dict):

    def __setitem__(self, key, value):
        super(Headers, self).__setitem__(self._normalize_key(key), value)

    def __getitem__(self, key):
        return super(Headers, self).__getitem__(self._normalize_key(key))

    @staticmethod
    def _normalize_key(key):
        return b'-'.join(segment.title() for segment in key.split('-'))

    def get_formatted_lines(self):
        return [
            b'%s: %s' % pair
            for pair in self.items()
        ]
