from xml.etree              import ElementTree as ET
from xml.etree.ElementTree  import XMLParser

import asyncore
import hashlib
import socket
import inspect
import logging

from Jid import Jid
from HttpServer import HttpServer
from MediaServer import serve_file
from Database import get_database
from Account import Account

logger = logging.getLogger('watransport.component')

message_tag = "{jabber:component:accept}message"
iq_tag = "{jabber:component:accept}iq"
presence_tag = "{jabber:component:accept}presence"
handshake_tag = "{jabber:component:accept}handshake"

class On:
    def __init__(self, typ):
        self.typ = typ

    def __call__(self, fn):
        fn.callback = self.typ
        return fn

"""
Verbindet sich mit dem Jabberserver.
Liest alle bestehen Accounts aus der Datenbank und erstellt Accountobjekte.
Verteilt jede eingehende Nachricht an den richtigen Account.
"""
class XMPPComponent(asyncore.dispatcher_with_send):

    root = None
    current = None
    depth = 0

    parser = None
    ystack = None

    accounts = dict()

    config = None
    database = None

    mapping = dict()

    def __init__(self, config):
        asyncore.dispatcher_with_send.__init__(self)
        self.config = config
        self.database = get_database(self.config.database)
        self.parser = XMLParser(target = self)

        members = inspect.getmembers(self, predicate=inspect.ismethod)
        for m in members:
            if hasattr(m[1], "callback"):
                fn = m[1]
                fname = m[0]
                self.mapping[fn.callback] = getattr(self, fname)

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (self.config.xmpp_host, self.config.xmpp_port) )

    def shutdown(self):
        for account in self.accounts.values():
            account.shutdown()

    def update(self):
        for jid, number, password in self.database.read_accounts():
            if jid not in self.accounts:
                logger.info("Found new account: %s" % jid)
                number = number.encode("UTF-8")
                password = password.encode("UTF-8")
                self.accounts[jid] = Account(jid, number, password, self, self.config)

    @On(handshake_tag)
    def streamReady(self, _):
        for jid, number, password in self.database.read_accounts():
            number = number.encode("UTF-8")
            password = password.encode("UTF-8")
            self.accounts[jid] = Account(jid, number, password, self, self.config)
        self.httpserver = HttpServer( self.config.http_host
                                    , self.config.http_port
                                    , serve_file(self.accounts, self.config)
                                    )

    @On("stream:error")
    def streamError(self, msg):
        raise Exception(msg)

    @On(presence_tag)
    def handlePresence(self, message):
        jabberFrom = Jid(message.get("from")).bare
        if jabberFrom not in self.accounts:
            return
        self.accounts[jabberFrom].incomingXMPPPresence(message)

    @On(iq_tag)
    def handleIq(self, msg):
        logger.debug("Unhandled Iq Stanza: %s" % ET.tostring(msg))

    @On(message_tag)
    def handleMessage(self, message):
        jabberFrom = Jid(message.get("from")).bare
        if jabberFrom not in self.accounts:
            return
        self.accounts[jabberFrom].incomingXMPPMessage(message)

    def handle_connect(self):
        self.write("<?xml version='1.0' encoding='UTF-8'?>")
        self.write("<stream:stream to='%s' "\
                   "xmlns:stream='http://etherx.jabber.org/streams' "\
                   "xmlns='jabber:component:accept'>" % self.config.transport_domain )

    def write(self, buf):
        logger.debug("to server: %s" % buf)
        self.send(buf)

    def handle_read(self):
        buf = self.recv(4096)
        logger.debug("from server:  %s" % buf)
        self.parser.feed(buf)

    def start(self, tag, attrib):
        if self.current is None:
            self.current = ET.Element(tag, attrib)
        else:
            tmp = ET.SubElement(self.current, tag, attrib)
            tmp.parent = self.current
            self.current = tmp

        if self.root is None:
            self.root = self.current
        self.depth += 1

        if self.depth == 1:
            pw = self.config.transport_password
            handshake = ET.Element("handshake")
            handshake.text = hashlib.sha1(attrib['id'] + pw).hexdigest()
            handshake = ET.tostring(handshake)
            self.write(handshake)

    def end(self, tag):
        if self.depth == 2:
            if tag in self.mapping:
                self.mapping[tag](self.current)
        try:
            self.root.remove(self.current)
        except:
            pass
        self.current = self.current.parent
        self.depth -= 1

    def data(self, data):
        if self.current.text is None:
            self.current.text = data
        else:
            self.current.text += data
