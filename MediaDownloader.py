
import hashlib
import thread
import urllib2
import base64
import os
import errno
import logging
import time

from Database import get_database

logger = logging.getLogger('watransport.mediadownloader')

from Jid import Jid

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

class MediaDownloader:

    account = None
    config = None

    def __init__(self, account, config):
        self.config = config
        self.account = account

    def download(self, message):
        mime = message.getMimeType().split("/")[0]
        name = message.fileName
        path = os.path.join(self.config.data_dir, str(self.account.number), mime)
        mkdir_p(path)

        waTransportJid = Jid(message.getFrom())
        waTransportJid.server = self.config.transport_domain
        waTransportJid = waTransportJid.bare

        filepath = path + "/" + name

        def do():
            while True:
                try:
                    req = urllib2.urlopen(message.getMediaUrl())
                    hashsum = hashlib.sha256()
                    with open(filepath, "wb") as f:
                        while True:
                            chunk = req.read(4096)
                            if not chunk: break
                            f.write(chunk)
                            hashsum.update(chunk)
    
                        computed_hashsum = base64.b64encode(hashsum.digest())
                        logger.debug("Downloaded file "+filepath+" with hashsum "+computed_hashsum)
                        if message.fileHash != computed_hashsum:
                            logger.info("hashsum mismatch: %s /= %s" % (message.fileHash, computed_hashsum))
                            raise Exception()
                        else:
                            db = get_database(self.config.database)
                            (id1, id2) = db.save_path(filepath, message.getId())
                            # TODO: maybe add .jpg or similar
                            url = "http://%s:%s/%s/%s" % (self.config.http_host, self.config.http_port, id2, id1)
                            logger.debug("MediaDownloader url: "+url)
                            # we are in a thread context and need locking
                            with self.account.xmpp.lock:
                                self.account.sendToJabber(url, waTransportJid)
                                self.account.markWAMessageAsReceived(msg = message)
                except:
                    logger.exception("Unknown exception: ")
                    # don't use to much cpu in case of endless loop
                    time.sleep(5.0)

        thread.start_new_thread(do, ())
