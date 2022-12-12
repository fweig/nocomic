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
  <a id="prev" href="?action={}"></a>
  <a id="next" href="?action={}"></a>
'''
DOUBLE_IMG = ''' <div class="row">
  <div class="column">
    <img src="img?id={}" align="right">
  </div>
  <div class="column">
    <img src="img?id={}" align="left">
  </div>
</div>
  <a id="prev" href="?action={}"></a>
  <a id="next" href="?action={}"></a>
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

def sortAndFilterComicFilesInDir(directory):
    return [directory / x.name for x in sorted(directory.iterdir()) if not x.name.startswith('.')]


class FileCollection:

    def __init__(self, files):
        self.filecache = [Path(f) for f in sorted(files) if isimg(f)]

    def files(self):
        return self.filecache

    def read(self, filename):
        raise NotImplementedError


class FileFolder(FileCollection):

    def __init__(self, path):
        super().__init__(path.iterdir())
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

    def isdoublepage(self):
        return self.width >= self.height


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


class Nocomic:

    def __init__(self, userargs):
        f = Path(args.file)

        self.active_file = f
        self.traverse_dir = False
        self.progress_file = None
        self.pagenr = 0

        if f.is_dir():
            self.progress_file = f / '.nocomic_progress'

            files = sortAndFilterComicFilesInDir(f)

            if files[0].suffix in FILE_BACKENDS:
                self.traverse_dir = True

            if self.traverse_dir:
                if self.progress_file.exists():
                    filename, page = self.loadprogress()
                    log.info("Continuing from {}, page {}".format(filename, page))
                    self.active_file = f / filename
                    self.pagenr = page
                else:
                    log.info("Starting to read {}".format(filename))
                    self.active_file = files[0]
            else:
                self.active_file = f

        backendname = 'folder' if self.active_file.is_dir() else self.active_file.suffix
        fileprovider = FILE_BACKENDS[backendname](self.active_file)
        self.cache = ImageCache(fileprovider)

    def saveprogress(self):
        if self.progress_file is None:
            return

        with open(self.progress_file, "w") as f:
            f.write("{}\n{}\n".format(self.active_file.name, self.pagenr))

    def loadprogress(self):
        with open(self.progress_file, "r") as f:
            filename = f.readline().rstrip()
            page = f.readline().rstrip()
        return filename, int(page)

    def loadnextfile(self):
        if not self.traverse_dir:
            return

        workDir = self.active_file.parent
        files = sortAndFilterComicFilesInDir(workDir)

        index = files.index(self.active_file)

        # Active file is the last file in this directory? No other files to load.
        if index == len(files) - 1:
            return

        self.active_file = files[index + 1]

        log.debug("Opening file '{}'".format(self.active_file))

        backendname = 'folder' if self.active_file.is_dir() else self.active_file.suffix
        fileprovider = FILE_BACKENDS[backendname](self.active_file)
        self.cache = ImageCache(fileprovider)
        self.pagenr = 0

    def currentimage(self):
        return self.cache.get(self.pagenr)

    def advancepage(self):
        if self.pagenr >= self.cache.imgnum():
            self.pagenr = self.cache.imgnum()-1
            return

        currImgIsDoublePage = self.currentimage().isdoublepage()
        nextImgIsDoublePage = self.cache.get(self.pagenr + 1).isdoublepage() if self.pagenr < self.cache.imgnum()-1 else False
        if self.pagenr == 0 or currImgIsDoublePage or nextImgIsDoublePage:
            self._incrementpagenr(1)
        else:
            self._incrementpagenr(2)

    def gobackpage(self):
        if self.pagenr <= 1:
            self._incrementpagenr(-1)
        else:
            previmg = self.cache.get(self.pagenr - 1)
            previmg2 = self.cache.get(self.pagenr - 2)

            if previmg.isdoublepage() or previmg2.isdoublepage():
                self._incrementpagenr(-1)
            else:
                self._incrementpagenr(-2)

    def atend(self):
        if self.pagenr >= self.cache.imgnum()-1:
            return True

        if self.pagenr < self.cache.imgnum()-2:
            return False

        nextimg = self.cache.get(self.pagenr+1)
        return not nextimg.isdoublepage()

    def visibleImages(self):

        img1 = self.currentimage()

        if img1.isdoublepage() or self.pagenr == 0 or self.pagenr == self.cache.imgnum()-1:
            log.debug("Double page")
            return self.pagenr, None
        else:
            leftpage = clamp(self.pagenr+1, 0, self.cache.imgnum()-1)
            img2 = self.cache.get(leftpage)

            if img2.isdoublepage():
                return self.pagenr, None
            else:
                return self.pagenr, leftpage

    def _incrementpagenr(self, incr):
        self.pagenr = clamp(self.pagenr+incr, 0, self.cache.imgnum()-1)


class NocomicRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        nocomic = self.server.nocomic

        request = urlparse(self.path)
        params = parse_qs(request.query)

        if request.path == '/':
            self.send_response(HTTPStatus.OK)

            self.send_header('Content-type', 'text/html')
            self.end_headers()

            action = params['action'][0] if 'action' in params else 'none'

            if action == 'nextpage':
                if nocomic.atend():
                    nocomic.loadnextfile()
                else:
                    nocomic.advancepage()
            elif action == 'prevpage':
                nocomic.gobackpage()
            elif action == 'none':
                pass
            else:
                log.debug("Unknow action '{}'".format(action))

            rightimage, leftimage = nocomic.visibleImages()
            if leftimage is None:
                log.debug("DOUBLE PAGE {}".format(rightimage))
                msg = SINGLE_IMG.format(rightimage, 'prevpage', 'nextpage')
            else:
                log.debug("left {}, right {}".format(leftimage, rightimage))
                msg = DOUBLE_IMG.format(leftimage, rightimage, 'prevpage', 'nextpage')

            self.sendbody(msg)

            nocomic.saveprogress()

        elif request.path == '/img':
            self.send_response(HTTPStatus.OK)

            imgid = int(params['id'][0])
            img = nocomic.cache.get(imgid)

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

    def __init__(self, nocomic, *args, **kwargs):

        self.nocomic = nocomic

        super().__init__(*args, **kwargs)


if __name__ == '__main__':

    if DO_DEBUG:
        log.basicConfig(level=log.DEBUG, format='%(levelname)s:%(asctime)s: %(message)s')
    else:
        log.basicConfig(level=log.INFO, format='%(message)s')

    parser = ArgumentParser()
    parser.add_argument("file", help="Comic file")

    args = parser.parse_args()

    nocomic = Nocomic(args)

    server = NocomicServer(nocomic, SERVER_ADDR, NocomicRequestHandler)

    log.info("Read @ http://{}:{}".format(IP_ADDR, PORT))
    server.serve_forever()
