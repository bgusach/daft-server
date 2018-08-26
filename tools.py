# coding: utf-8

from __future__ import unicode_literals


from collections import defaultdict


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
