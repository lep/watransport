from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_contacts.protocolentities import GetSyncIqProtocolEntity
from yowsup.layers.protocol_media.protocolentities import LocationMediaMessageProtocolEntity
from yowsup.layers.protocol_presence.protocolentities import SubscribePresenceProtocolEntity
from yowsup.layers.protocol_profiles.protocolentities import GetPictureIqProtocolEntity

from yowsup.stacks import YowStack, YowStackBuilder, YOWSUP_CORE_LAYERS

from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.auth import AuthError

from xml.etree import ElementTree as ET

import re
import time
import hashlib
import base64
import thread
import logging

from Jid import Jid
from XMPPLayer import XMPPLayer
from MediaDownloader import MediaDownloader
from Database import get_database
from Stanzas import *

logger = logging.getLogger('watransport.account')

"""
Alle Accounts werden vom XMPP Komponent erstellt.
Dieser verteilt dann die richtigen Nachrichten an die Accounts.
Jeder Account hat einen Yowsup Stack mit dem Nachrichten ausgetauscht werden.

"""
class Account:

    jid = None
    password = None
    ystack = None
    xmpp = None
    connected = False

    roster = None

    config = None

    connected = False
    message_queue = list()

    media_downloader = None

    def __init__(self, jid, number, password, xmpp, config):
        self.jid = jid
        self.number = number
        self.xmpp = xmpp
        self.password = password
        self.config = config

        self.media_downloader = MediaDownloader(self, config)

        self.database = get_database(self.config.database)

        r= self.database.read_roster(self.number)
        jidPat = "%s@" + self.config.transport_domain
        self.roster = map(lambda nr: Jid(jidPat % nr), r)
        self._mkYStack()

    def shutdown(self):
        for buddy in self.roster:
            p = presence( pfrom = buddy.bare
                        , pto = self.jid
                        , ptype = "unavailable"
                        )
            self.xmpp.write(ET.tostring(p))


    def _mkYStack(self):
        creds = (self.number, self.password)

        stackBuilder = YowStackBuilder()
        self.stack = stackBuilder.\
                      pushDefaultLayers(True).\
                      push(XMPPLayer).\
                      build()

        self.stack.setProp("xmpp.transport.account", self)
        self.stack.setCredentials(creds)
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))

    def try_to_connect(self):
        try:
            self._mkYStack()
        except:
            return


    def __str__(self):
        return "Account: (%s, %s)" % (self.jid, self.password)

    def sendToJabber(self, txt, mfrom):
        msg = message( mtype = "chat"
                     , body = text
                     , mfrom = mfrom
                     , mto = self.jid
                     )
        self.xmpp.write(ET.tostring(msg))

    def _sendWAMessage(self, msg):
        if self.connected:
            self.ystack.toLower(msg)
        else:
            self.message_queue.append(msg)


    def markWAMessageAsReceived(self, **kwargs):
        logger.debug("mark wa message as received")
        if 'msg' in kwargs:
            msg = kwargs['msg']
            outgoing = OutgoingReceiptProtocolEntity( msg.get("id")
                                                    , msg.getFrom()
                                                    )
            #self._sendWAMessage(outgoing)
            self.ystack.toLower(outgoing)
        elif 'to' in kwargs and 'id' in kwargs:
            outgoing = OutgoingReceiptProtocolEntity( kwargs['id']
                                                    , kwargs['to']
                                                    )
            self.ystack.toLower(outgoing)
            #self._sendWAMessage(outgoing)

    def markWAMessageAsRead(self, **kwargs):
        if 'msg' in kwargs:
            msg = kwargs['msg']
            outgoing = OutgoingReceiptProtocolEntity( msg.get("id")
                                                    , msg.getFrom(True)
                                                    , True
                                                    )
            self._sendWAMessage(outgoing)
        elif 'to' in kwargs and 'id' in kwargs:
            outgoing = OutgoingReceiptProtocolEntity( kwargs['id']
                                                    , kwargs['to']
                                                    , True
                                                    )
            self._sendWAMessage(outgoing)

    ##############
    # WA Methods #
    ##############

    def downloadAvatar(self, waJid):
        def onSuccess(result, request):
            """
            print "Result: %s" % result
            print "Request: %s" % request

            img = result.getPictureData()
            hashsum = hashlib.sha1().update(img).hexdigest()

            dataIq = iq(itype = "set", ifrom = self.jid, id = "publish1")
            pubsub = ET.SubElement(dataIq, "pubsub")
            pubsub.set("xmlns", "http://jabber.org/protocol/pubsub")
            publish = ET.SubElement(pubsub, "publish")
            publish.set("node", "urn:xmpp:avatar:data")
            item = ET.SubElement(publish, "item")
            item.set("id", hashsum)
            data = ET.SubElement(item, "data")
            data.set("xmlns", "urn:xmpp:avatar:data")
            data.body = base64.b64encode(img)

            self.xmpp.write(ET.tostring(dataIq))

            metaIq = iq(itype = "set", ifrom = self.jid, id = "publish2")
            pubsub = ET.SubElement(metaIq, "pubsub")
            pubsub.set("xmlns", "http://jabber.org/protocol/pubsub")
            publish = ET.SubElement(pubsub, "publish")
            publish.set("node", "urn:xmpp:avatar:metadata")
            item = ET.SubElement(publish, "item")
            item.set("id", hashsum)
            metadata = ET.SubElement(item, "metadata")
            metadata.set("xmlns", "urn:xmpp:avatar:metadata")
            info = ET.SubElement(metadata, "info")
            info.set("bytes", len(img))
            info.set("id", hashsum)
            info.set("type", "image/jpeg")
            info.set("width", "640")
            info.set("height", "640")

            self.xmpp.write(ET.tostring(metaIq))
            """

            result.writeToFile("./xowpics/%s_%s.jpg" % (request.getTo(), preview if result.isPreview() else "full"))



        entity = GetPictureIqProtocolEntity(waJid, preview = True)
        self.ystack._sendIq(entity, onSuccess)

    def incomingWAReceipt(self, receipt):
        waJid = Jid(receipt.getFrom())
        waJid.server = self.config.transport_domain
        msg = message(mfrom = waJid.bare, mto = self.jid)

        if receipt.getType() == "read":
            # read
            received = ET.SubElement(msg, "displayed")
            received.set("xmlns", "urn:xmpp:chat-markers:0")
            received.set("id", receipt.getId())

            self.xmpp.write(ET.tostring(msg))
        else:
            # delivered
            received = ET.SubElement(msg, "received")
            received.set("xmlns", "urn:xmpp:chat-markers:0")
            received.set("id", receipt.getId() )

            received2 = ET.SubElement(msg, "received")
            received2.set("xmlns", "urn:xmpp:receipts")
            received2.set("id", receipt.getId() )

            self.xmpp.write(ET.tostring(msg))

    def _sendXMPPMessage(self, frm, text, id):
        xmsg = message( mto = self.jid
                      , mfrom = frm
                      , mtype = "chat"
                      , id = id
                      )

        body = ET.SubElement(xmsg, "body")
        body.text = text

        request = ET.SubElement(xmsg, "request")
        request.set("xmlns", "urn:xmpp:receipts")
        request.set("id", id)

        markable = ET.SubElement(xmsg, "markable")
        markable.set("xmlns", "urn:xmpp:chat-markers:0")

        self.xmpp.write(ET.tostring(xmsg))

    def incomingWAMessage(self, wmsg):
        waJid = Jid(wmsg.getFrom(True))
        waJid.server = self.config.transport_domain
        id = wmsg.getId()

        #self.markWAMessageAsReceived(msg = wmsg)
        self._sendXMPPMessage(waJid.bare, wmsg.getBody().decode("UTF-8"), id)

    def incomingWAMedia(self, msg):
        waJid = Jid(msg.getFrom(True))
        waJid.server = self.config.transport_domain
        id = msg.getId()
        if msg.getMediaType() == "location":
            text = "geo:%s,%s" % (msg.getLatitude(), msg.getLongitude())
            self._sendXMPPMessage(waJid.bare, text, id)
        elif msg.getMediaType() == "vcard": #??????
            #self.markWAMessageAsReceived(msg = msg)
            logger.info(msg)
        else:
            self.media_downloader.download(msg)




    def onYowConnect(self, ystack):
        self.connected = True
        self.ystack = ystack
        for msg in self.message_queue:
            self.ystack.toLower(msg)
        self.message_queue = []

        for buddy in self.roster:
            p = presence(pfrom = buddy.bare, pto = self.jid)
            self.xmpp.write(ET.tostring(p))

        #for buddy in self.roster:
        #    self.downloadAvatar(buddy.bare)

    def onYowDisconnect(self):
        self.connected = False
        for buddy in self.roster:
            p = presence( pfrom = buddy.bare
                        , pto = self.jid
                        , ptype = "unavailable"
                        )
            self.xmpp.write(ET.tostring(p))

    ###############
    # XMPP Method #
    ###############


    def incomingXMPPMessage(self, msg):
        body = msg.find("{jabber:component:accept}body")
        read = msg.find("{urn:xmpp:chat-markers:0}displayed")
        received = msg.find("{urn:xmpp:receipts}received")

        waToJid = Jid(msg.get("to"))
        waToJid.server = "s.whatsapp.net"
        waToJid = waToJid.bare

        if body is not None:
            geoUri = re.compile(r'^geo:(\d+\.d+),(\d+\.\d+)$')
            m = geoUri.match(body.text)
            if m:
                outgoing = LocationMediaMessageProtocolEntity( m.get(1)
                                                             , m.get(2)
                                                             , to = waToJid
                                                             )
            else:
                outgoing = TextMessageProtocolEntity( body.text.encode("UTF-8")
                                                    , to = waToJid
                                                    )

            if msg.get("id") is not None:
                outgoing._id = msg.get("id")

            self.ystack.toLower(outgoing)
            #self._sendWAMessage(outgoing)

        if read is not None:
            self.markWAMessageAsRead(id = read.get("id"), to = waToJid)


    def incomingXMPPPresence(self, msg):
        if msg.get("type") == "subscribe":

            xmppToJid = Jid(msg.get("to"))

            if xmppToJid.bare not in self.roster:
                entity = GetSyncIqProtocolEntity([xmppToJid.name])
                self._sendWAMessage(entity)

                waJid = Jid(xmppToJid.bare)
                waJid.server = "s.whatsapp.net"
                subscribeEntity = SubscribePresenceProtocolEntity(waJid.bare)
                self._sendWAMessage(subscribeEntity)

                self.roster.append(xmppToJid.bare)
                self.database.add_contact(self.number, xmppToJid.name)

            subscribed = presence( pto = self.jid
                                 , pfrom = xmppToJid.bare
                                 , ptype = "subscribed"
                                 )

            subscribe = presence( pto = self.jid
                                , pfrom = xmppToJid.bare
                                , ptype = "subscribe"
                                )

            self.xmpp.write(ET.tostring(subscribed))
            self.xmpp.write(ET.tostring(subscribe))

        elif msg.get("type") == "probe":
            probe = presence( pfrom = msg.get("to")
                            , pto = msg.get("from")
                            )
            self.xmpp.write(ET.tostring(probe))

        else:
            logger.debug("Unhandled Presence Stanza: %s" % ET.tostring(msg))


