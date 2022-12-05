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

from urllib.parse import (
        urlparse,
        parse_qs,
)

from zipfile import (
        ZipFile,
)

import PIL.Image


DO_DEBUG = False
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
        background-color: DarkGrey;
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
        height: 99.5%;
      }
      .column {
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
  <div class="column">
    <img src="img?id={}" align="right">
  </div>
  <div class="column">
    <img src="img?id={}" align="left">
  </div>
</div>
  <a id="prev" href="reader?p={}"></a>
  <a id="next" href="reader?p={}"></a>
'''

IMG_EXTENSIONS = [
    '.jpg',
    '.jpeg',
    '.png',
    '.bmp',
]


def isimg(fn):
    return Path(fn).suffix in IMG_EXTENSIONS

def clamp(x, left, right):
    return min(right, max(x, left))


class FileCollection:

    def __init__(self, files):
        self.filecache = [Path(f) for f in sorted(files) if isimg(f)]

    def files(self):
        return self.filecache

    def read(self, filename):
        raise NotImplementedError


class FileFolder(FileCollection):

    def __init__(self, path):
        super().__init__(listdir(path))
        self.root = path

    def read(self, name):
        fullname = self.root / name
        with open(fullname, 'rb') as f:
            return f.read()


class ZipArchive(FileCollection):

    def __init__(self, fname):
        self.file = ZipFile(fname)

        super().__init__(self.file.namelist())

    def __del__(self):
        if 'file' in self.__dict__:
            self.file.close()

    def read(self, name):
        return self.file.read(str(name))
    

# TODO: Add support for rar-archives
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

    def prefetchAll(self):
        for i in range(self.imgnum()):
            self.prefetch(i)

    def prefetch(self, ind):
        log.debug("Prefetch image {}".format(ind))
        self._loadimg(ind)


    def _loadimg(self, ind):
        fs = self.files.files()

        fname = fs[ind]

        imgtype = fname.suffix

        data = self.files.read(fname)

        img = PIL.Image.open(BytesIO(data))
        width, height = img.size

        self.cache[ind] = Image(width, height, imgtype, data)


class NocomicRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        cache = self.server.cache

        request = urlparse(self.path)
        params = parse_qs(request.query)
        
        if request.path == '/reader':
            self.send_response(HTTPStatus.OK)

            self.send_header('Content-type', 'text/html')
            self.end_headers()

            page = int(params['p'][0]) if 'p' in params else 0

            pagenum = cache.imgnum()

            page = clamp(page, 0, pagenum-1)

            img1 = cache.get(page)

            # TODO check if prev page is double or not, 
            # to determine if we have to go back by 2 or 1 page
            if img1.width >= img1.height or page == 0:
                log.debug("Double page")
                nextpage = clamp(page+1, 0, pagenum-1)
                prevpage = clamp(page-1, 0, pagenum-1)
                msg = SINGLE_IMG.format(page, prevpage, nextpage)
            else:
                leftpage = clamp(page+1, 0, pagenum-1)
                img2 = cache.get(leftpage)
                if img2.width >= img2.height:
                    nextpage = leftpage
                    prevpage = clamp(page-2, 0, pagenum-1)
                    msg = SINGLE_IMG.format(page, prevpage, nextpage)
                else:
                    nextpage = clamp(page+2, 0, pagenum-1)
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

    def log_message(self, fmt, *args):
        log.debug(fmt % args)

    def sendbody(self, body):
        self.sendstr(HTML_START)
        self.sendstr(body)
        self.sendstr(HTML_END)

    def sendstr(self, txt):
        self.wfile.write(bytes(txt, 'utf8'))


class NocomicServer(HTTPServer):

    def __init__(self, cache, *args, **kwargs):

        self.cache = cache

        super().__init__(*args, **kwargs)


if __name__ == '__main__':

    if DO_DEBUG:
      log.basicConfig(level=log.DEBUG, format='%(levelname)s:%(asctime)s: %(message)s')
    else:
        log.basicConfig(level=log.INFO, format='%(message)s')

    parser = ArgumentParser()
    parser.add_argument("file", help="Comic file")

    args = parser.parse_args()
    
    f = Path(args.file)

    backendname = 'folder' if f.is_dir() else f.suffix

    fileprovider = FILE_BACKENDS[backendname](args.file)

    cache = ImageCache(fileprovider)

    server = NocomicServer(cache, SERVER_ADDR, NocomicRequestHandler)

    log.info("Read @ http://{}:{}/reader".format(IP_ADDR, PORT))
    server.serve_forever()
