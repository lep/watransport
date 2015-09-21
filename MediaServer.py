
from HttpServer import HttpRequest
from Database import get_database


def serve_file(accounts, config):
    return lambda sock: MediaRequest(accounts, config, sock)

class MediaRequest(HttpRequest):

    accounts = None

    def __init__(self, accounts, config, sock):
        HttpRequest.__init__(self, sock)
        self.accounts = accounts
        self.database = get_database(self.config.database)

    def error(self, code, descr):
        self.push("HTTP/1.1 %s %s\r\n" % (code, descr))
        self.close()

    def onHeaders(self):
        if method != "GET":
            self.error(405, "Method not allowed")
            return

        ids = self.path.split("/")
        if len(ids) != 2:
            self.error(404, "Not found")
            return

        res = self.database.lookup_path(ids[0], ids[1])
        if res:
            self.error(404, "Not found")
            return

        fpath, to, frm, read = res
        self.serve_file(ids, fpath, read, to, frm)

    def serve_file(ids, fpath, read, to, frm):
        with open(self.path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                self.push(chunk)
        if read:
            self.database.set_file_read(ids[0], ids[1])
            with self.accounts[to].xmpp.lock:
                self.accounts[to].markWAMessageAsRead(to = frm, id = id)


    def onData(self, buff):
        pass


