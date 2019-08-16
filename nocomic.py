#!/usr/bin/env python3


from argparse import (
        ArgumentParser,
)

from http.server import (
        BaseHTTPRequestHandler, 
        HTTPServer, 
        HTTPStatus,
)

from os import (
        listdir,
)

from pathlib import (
        Path,
)

from urllib.parse import (
        urlparse,
        parse_qs,
)

from PIL import (
        Image,
)


IP_ADDR = 'localhost'
PORT = 8080
SERVER_ADDR = (IP_ADDR, PORT)

HTML_START = """
<!DOCTYPE html>
<html>
  <head>
    <style>
      html, body {
        height: 100%;
        margin: 0;
        padding: 0;
      }
      img {
        padding: 0;
        display: block;
        margin: 0 auto;
        max-height: 100%;
        max-width: 100%;
      }
    </style>
  </head>
  <body>
"""

HTML_END= """
  </body>
</html>
"""


class FileCollection:

    def files(self):
        raise NotImplementedError

    def read(self, filename):
        raise NotImplementedError


class FileFolder(FileCollection):

    def __init__(self, path):
        self.root = Path(path)

    def files(self):
        return sorted(listdir(self.root))

    def read(self, name):
        fullname = self.root / Path(name)
        with open(fullname, 'rb') as f:
            return f.read()


class ImageCache:

    def __init__(self, files):
        self.files = files

        # print(self.files.files())

    def imgnum(self):
        return len(self.files.files())

    def get(self, ind):
        assert ind >= 0 and ind < self.imgnum()

        fs = self.files.files()

        fname = fs[ind]

        # TODO get filetype and wrap in PIL image
        return self.files.read(fname)

    def prefetch(self, ind):
        pass
    

class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        cache = self.server.cache

        print('path:', self.path)
        request = urlparse(self.path)
        params = parse_qs(request.query)
        print('dir:', request.path)
        print('params:', params)
        
        if request.path == '/reader':
            self.send_response(HTTPStatus.OK)

            self.send_header('Content-type', 'text/html')
            self.end_headers()

            page = params['p'][0] if 'p' in params else 0

            msgtemplate = '<img src="img?id={}">'

            self.sendbody(msgtemplate.format(page))

        elif request.path == '/img':
            self.send_response(HTTPStatus.OK)

            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()

            imgid = int(params['id'][0])

            self.wfile.write(cache.get(imgid))

        else:

            self.send_error(HTTPStatus.NOT_FOUND)

    def sendbody(self, body):
        self.sendstr(HTML_START)
        self.sendstr(body)
        self.sendstr(HTML_END)

    def sendstr(self, txt):
        self.wfile.write(bytes(txt, 'utf8'))


class ImageHTTPServer(HTTPServer):

    def __init__(self, cache, *args, **kwargs):

        self.cache = cache

        super().__init__(*args, **kwargs)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("image", help="Image thats displayed by the server")

    args = parser.parse_args()

    fileprovider = FileFolder(args.image)
    cache = ImageCache(fileprovider)

    server = ImageHTTPServer(cache, SERVER_ADDR, RequestHandler)
    server.serve_forever()
