
from yowsup.layers.interface                            import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities   import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities   import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities       import OutgoingAckProtocolEntity
from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer

from xml.etree                                          import ElementTree as ET
from xml.etree.ElementTree                              import XMLParser

import io
import threading
import asyncore
import logging

logger = logging.getLogger('watransport.layer')

from Jid import Jid

message_tag = "{jabber:component:accept}message"
iq_tag = "{jabber:component:accept}iq"
presence_tag = "{jabber:component:accept}presence"


class XMPPLayer(YowInterfaceLayer):

    account = None

    def __init__(self):
        YowInterfaceLayer.__init__(self)
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        logger.info("Layer initialized")

    def onEvent(self, event):
        if event.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECT or event.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            self.account.onYowDisconnect()
        logger.info("Got event %s" % event.getName())

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        self.account = self.getProp("xmpp.transport.account")
        self.account.onYowConnect(self)
        logger.info( "Successfully logged in with %s" % self.account)


    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        logger.info( "Login failed, reason: %s" % entity.getReason())

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        logger.debug( "Got receipt: %s" % entity)
        ack = OutgoingAckProtocolEntity( entity.getId()
                                       , "receipt"
                                       , entity.getType()
                                       , entity.getFrom()
                                       )
        self.toLower(ack)

        self.account.incomingWAReceipt(entity)


    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom())
        self.toLower(receipt)
        if not messageProtocolEntity.isGroupMessage():
            if messageProtocolEntity.getType() == "text":
                self.account.incomingWAMessage(messageProtocolEntity)
            elif messageProtocolEntity.getType() == "media":
                self.account.incomingWAMedia(messageProtocolEntity)
        else:
            # not yet implemented
            logger.info( "Received group message: %s" % messageProtocolEntity)

    @ProtocolEntityCallback("notification")
    def onNotification(self, message):
        logger.debug( "Got notification: %s" % message)

    @ProtocolEntityCallback("ib")
    def onIb(self, message):
        logger.debug( "Got IB: %s" % message)

    @ProtocolEntityCallback("iq")
    def onIq(self, message):
        logger.debug( "Got Iq: %s" % message)

    @ProtocolEntityCallback("chatstate")
    def onChatstate(self, message):
        logger.debug( "Got chatstate: %s" % message)

    @ProtocolEntityCallback("presence")
    def onPresence(self, message):
        logger.debug( "Got presence: %s" % presence)

    #@ProtocolEntityCallback("ack")
    #def onAck(self, message):
    #    # message reached server
    #    if ack.getClass() == "message":
    #       msgId = ack.getId()
    #        # do custom non-standarized stuff

