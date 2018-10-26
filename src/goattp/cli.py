# coding: utf-8

from __future__ import unicode_literals

import click

from . import core


@click.command()
@click.argument('wsgi-callable')
@click.option('-h', '--host', default='localhost')
@click.option('-p', '--port', default=8888)
@click.option('-q', '--queue-size', default=5)
@click.option('-d', '--delay', default=0)
def serve(wsgi_callable, host, port, queue_size, delay):
    """
    WSGI_CALLABLE: WSGI App in path/to/module.py:callable

    """
    mod_path, _, py_path = wsgi_callable.partition(':')
    from importlib import util
    # TODO [bgusach 26.10.2018]: pass proper first arg
    spec = util.spec_from_file_location('hehe', mod_path)
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    app = getattr(mod, py_path)

    # app = import_by_fqpn(wsgi_callable)
    server = core.GoatTTPSever(host, port, queue_size, app, delay)
    server.serve()


if __name__ == '__main__':
    serve()
