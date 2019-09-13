#!/usr/bin/env python3


from argparse import (
        ArgumentParser,
)

from http.server import (
        BaseHTTPRequestHandler, 
        HTTPServer, 
        HTTPStatus,
)

from io import (
        BytesIO,
)

import logging as log

from os import (
        listdir,
)

from pathlib import (
        Path,
)

import subprocess

from urllib.parse import (
        urlparse,
        parse_qs,
)

from zipfile import (
        ZipFile,
)


import PIL.Image


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
        height: 100%;
        max-width: 100%;
      }
      a {
        display: hidden;
      }
      .row {
        display: flex;
        height: 99%;
      }
      .column_left {
        flex: 50%;
        height: 100%;
        padding: 2px;
      }
      .column_right {
        flex: 50%;
        height: 100%;
        padding: 2px;
      }
    </style>
    <script>
      document.addEventListener("keyup", function(e) {
        var key = e.which || e.keyCode;
        switch (key) {
          case 37: // left arrow
            document.getElementById("prev").click();
            break;
          case 39: // right arrow
            document.getElementById("next").click();
            break;
        }
      });
    </script>
  </head>
  <body>
"""

HTML_END= """ 
  </body>
</html>
"""

SINGLE_IMG = '''<img src="img?id={}">
  <a id="prev" href="reader?p={}"></a>
  <a id="next" href="reader?p={}"></a>
'''
DOUBLE_IMG = ''' <div class="row">
  <div class="column_left">
    <img src="img?id={}" align="right">
  </div>
  <div class="column_right">
    <img src="img?id={}" align="left">
  </div>
</div>
  <a id="prev" href="reader?p={}"></a>
  <a id="next" href="reader?p={}"></a>
'''


def clamp(x, left, right):
    return min(right, max(x, left))

class FileCollection:

    def files(self):
        raise NotImplementedError

    def read(self, filename):
        raise NotImplementedError


class FileFolder(FileCollection):

    def __init__(self, path):
        self.root = path
        self.filecache = [Path(pathname) for pathname in sorted(listdir(self.root))]

    def files(self):
        return self.filecache

    def read(self, name):
        fullname = self.root / name
        with open(fullname, 'rb') as f:
            return f.read()

class ZipArchive(FileCollection):

    def __init__(self, fname):
        self.file = ZipFile(fname)
        self.filecache = self.file.namelist()

    def files(self):
        return self.filecache

    def read(self, name):
        return self.file.read(name)
    
    def __del__(self):
        self.file.close()


FILE_BACKENDS = {
    'folder': FileFolder,
    '.zip': ZipArchive,
    '.cbz': ZipArchive,
}

class Image:

    def __init__(self, width, height, type_, data):

        self.width  = width
        self.height = height
        self.type_  = type_
        self.data   = data


class ImageCache:

    def __init__(self, files):
        self.files = files
        self.cache = {}

        # print(self.files.files())

    def imgnum(self):
        return len(self.files.files())

    def get(self, ind):
        assert ind >= 0 and ind < self.imgnum()

        if ind in self.cache:
            log.debug("Cache hit on index {}".format(ind))
        else:
            log.debug("Cache miss on index {}".format(ind))
            self._loadimg(ind)

        return self.cache[ind]

    def prefetch(self, ind):
        log.debug("Prefetch image {}".format(ind))
        self._loadimg(self, ind)


    def _loadimg(self, ind):
        fs = self.files.files()

        fname = fs[ind]

        imgtype = Path(fname).suffix

        data = self.files.read(fname)

        img = PIL.Image.open(BytesIO(data))
        width, height = img.size

        self.cache[ind] = Image(width, height, imgtype, data)


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

            page = int(params['p'][0]) if 'p' in params else 0

            pagenum = cache.imgnum()

            page = clamp(page, 0, pagenum-1)

            img1 = cache.get(page)

            if img1.width >= img1.height or page == 0:
                log.debug("Double page")
                nextpage = clamp(page+1, 0, pagenum-1)
                prevpage = clamp(page-1, 0, pagenum-1)
                msg = SINGLE_IMG.format(page, prevpage, nextpage)
            else:
                leftpage = clamp(page+1, 0, pagenum-1)
                nextpage = clamp(page+2, 0, pagenum-1)
                img2 = cache.get(leftpage)
                if img2.width >= img2.height:
                    msg = SINGLE_IMG.format(page)
                else:
                    prevpage = clamp(page-2, 0, pagenum-1)
                    msg = DOUBLE_IMG.format(leftpage, page, prevpage, nextpage)

            self.sendbody(msg)

        elif request.path == '/img':
            self.send_response(HTTPStatus.OK)

            imgid = int(params['id'][0])
            img = cache.get(imgid)

            self.send_header('Content-type', 'image/{}'.format(img.type_[1:]))
            self.end_headers()

            self.wfile.write(img.data)

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
    parser.add_argument("file", help="Comic file")

    args = parser.parse_args()
    
    f = Path(args.file)

    if f.is_dir():
        backendname = 'folder'
    else:
        backendname = f.suffix

    fileprovider = FILE_BACKENDS[backendname](args.file)

    cache = ImageCache(fileprovider)

    server = ImageHTTPServer(cache, SERVER_ADDR, RequestHandler)
    server.serve_forever()
