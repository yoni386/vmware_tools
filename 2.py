#!/usr/bin/python

import SocketServer, string, socket, time

total_requests = 0


class RequestServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = 1


class RequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        global total_requests
        # ACCEPT :
        host, port = self.client_address
        request = ""
        while 1:
            line = self.rfile.readline()
            if line in (None, "\r\n", ""):
                break
            request = request + line
        request = string.rstrip(request)
        self.wfile.write("Received OK")
        total_requests += total_requests + 1
        if total_requests % 100 == 0:
            print ("%s - %s" % (total_requests, time.time()))


def main():
    server = RequestServer(("127.0.0.1", 8888), RequestHandler)
    print ("Listening to socket [%s:%s]" % ("127.0.0.1", 8888))
    server.serve_forever()
