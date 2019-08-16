#!/usr/bin/env python3

from http.server import (
        BaseHTTPRequestHandler, 
        HTTPServer, 
        HTTPStatus,
)

from base64 import (
        b64encode,
)


IP_ADDR = 'localhost'
PORT = 8080
SERVER_ADDR = (IP_ADDR, PORT)

TEST_IMAGE = '/home/felix/Pictures/large.png'

HTML_START = """
<!DOCTYPE html>
<html>
  <body>
"""

HTML_END= """
  </body>
</html>
"""


class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        print(self.path)

        self.send_response(HTTPStatus.OK)

        self.send_header('Content-type', 'text/html')
        self.end_headers()

        msgtemplate = '<img src="data:image/png;base64,{}">'

        # TODO serve images over sepereate http request, this save us from base64 encoding
        with open(TEST_IMAGE, 'rb') as imgfile:
            b64img = b64encode(imgfile.read())

        self.sendimg(b64img)

    def sendimg(self, b64img):
        self.wfile.write(bytes(HTML_START, 'utf8'))
        self.wfile.write(bytes('<img src="data:image/png;base64,', 'utf8'))
        self.wfile.write(b64img)
        self.sendstr('">')
        self.sendstr(HTML_END)

    def sendstr(self, txt):
        self.wfile.write(bytes(txt, 'utf8'))



if __name__ == '__main__':
    server = HTTPServer(SERVER_ADDR, RequestHandler)

    server.serve_forever()
