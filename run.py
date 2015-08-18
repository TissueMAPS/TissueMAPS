#!/usr/bin/env python
# encoding: utf-8

import webbrowser
import threading

def open_browser(port, path='', delay=0.5):
    """Start a browser after waiting for `delay` seconds
    and point it to localhost:`port`/`path`."""
    def open_browser_helper():
        url = 'http://localhost:%s/%s' % (port, path)
        webbrowser.open(url)
        # webbrowser.get("open %s").open(url)
    thread = threading.Timer(delay, open_browser_helper)
    thread.start()


if __name__ == "__main__":
    import argparse
    import tmaps.appfactory

    parser = argparse.ArgumentParser(description='TissueMAPS server')
    parser.add_argument(
        '--port', action='store', type=int, default=8080,
        help='the port on which the server should listen')
    parser.add_argument(
        '--browser', action='store_true', default=False,
        help='if a browser window should be opened automatically')
    args = parser.parse_args()

    if args.browser:
        open_browser(port=args.port)

    # start `flask` development server

    from wsgi import app
    # application = appfactory.create_app('dev')
    # application.run(debug=True, port=args.port)

    app.run(debug=True, port=8080, gevent=100)
