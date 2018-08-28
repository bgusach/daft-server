# coding: utf-8

from __future__ import unicode_literals


def app(env, start_response):
    print('WSGI APP CALLED!!')

    content_length = int(env.get('CONTENT_LENGTH') or '0')
    import html

    response = '''
        <html>
        <head></head>
        <body>
        {env}<br>
        body: {body}<br>
        </body>
        </html>
    '''.format(
        env='<br>'.join(['%s: %s' % (key, html.escape(repr(val))) for key, val in env.items()]),
        body=repr(env['wsgi.input'].read(content_length).decode('ascii'))
    ).encode('ascii')

    # TODO: fix the content-length. it should be based on bytes and not unicode strings
    start_response(
        '200 OK',
        [('Content-Type', 'text/html'), ('Content-Length', str(len(response)))]
    )

    return [response]


