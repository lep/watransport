
import asynchat
import asyncore
import socket
import re

class HttpRequest(asynchat.async_chat):
    def __init__(self, sock):
        asynchat.async_chat.__init__(self, sock=sock)
        self.set_terminator("\r\n\r\n")
        self.after_headers = False
        self.ibuffer = []
        self.headers = {}


    def collect_incoming_data(self, data):
        if self.after_headers:
            self.onData(data)
        else:
            self.ibuffer.append(data)


    def found_terminator(self):
        self.parseHeaders()
        self.ibuffer = []
        self.after_headers = True
        self.set_terminator(None)

    def handle_close(self):
        self.close()

    def parseHeaders(self):
        headerRe = re.compile(r'^([^:]+):(.+)$')
        lines = iter("".join(self.ibuffer).splitlines())
        self.method, self.path = lines.next().split(" ")[:2]

        for line in lines:
            m = headerRe.match(line)
            if not m:
                continue
            self.headers[m.group(1).lower()] = m.group(2)
        self.onHeaders()

    def onData(self, data):
        pass

    def onHeaders(self):
        pass



class HttpServer(asyncore.dispatcher):

    def __init__(self, host, port, handler = HttpRequest):
        asyncore.dispatcher.__init__(self)
        self.handler = handler
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind( (host, port) )
        self.listen(5)


    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            (sock, _) = pair
            self.handler(sock)
