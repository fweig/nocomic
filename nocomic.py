#!/usr/bin/env python3

from http.server import (
        BaseHTTPRequestHandler, 
        HTTPServer, 
        HTTPStatus,
)


IP_ADDR = 'localhost'
PORT = 8080
SERVER_ADDR = (IP_ADDR, PORT)


class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        print(self.path)

        self.send_response(HTTPStatus.OK)

        self.send_header('Content-type', 'text/html')
        self.end_headers()

        message = "Hello, world!"

        self.wfile.write(bytes(message, 'utf8'))



if __name__ == '__main__':
    server = HTTPServer(SERVER_ADDR, RequestHandler)

    server.serve_forever()
