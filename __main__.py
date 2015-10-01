import logging
import asyncore
import sys
import time
import argparse
import os
import signal

from XMPPComponent import XMPPComponent



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'WhatsApp XMPP Transport')
    parser.add_argument( '--password'
                       , dest = 'transport_password'
                       , help = 'The transport password'
                       , required = True )
    parser.add_argument( '--http-bind'
                       , dest = 'http_bind'
                       , help = 'Address on which the httpd listens. Default: 127.0.0.1'
                       , default = "127.0.0.1" )
    parser.add_argument( '--http-port'
                       , dest = 'http_port'
                       , help = 'Port on which the httpd listens. Default: 8080'
                       , default = 8080
                       , type = int )
    parser.add_argument( '--http-address'
                       , dest = 'http_address'
                       , help = 'Address which is send in messages. Default: 127.0.0.1'
                       , default = '127.0.0.1'
                       )
    parser.add_argument( '--xmpp-host'
                       , dest = 'xmpp_host'
                       , help = 'Address of the xmpp server. Default: localhost'
                       , default = '127.0.0.1' )
    parser.add_argument( '--xmpp-port'
                       , dest = 'xmpp_port'
                       , default = 5347
                       , help = 'Port of the xmpp server. Default: 5347'
                       , type = int )
    parser.add_argument( '--transport-domain'
                       , dest = 'transport_domain'
                       , help = 'Domain of this transport service.'
                       , required = True )
    parser.add_argument( '--data-dir'
                       , dest = 'data_dir'
                       , help = 'Where to store things. Default: current directory'
                       , default = '.' )
    parser.add_argument( '--debug'
                       , action = 'store_true'
                       , help = 'Run in debug mode.'
                       )

    args = parser.parse_args()

    args.database = os.path.join(args.data_dir, "transport.db")
    logging.basicConfig( format = '%(asctime)s %(message)s'
                       , filename=os.path.join(args.data_dir, 'watransport.log'))
    logger = logging.getLogger('watransport')
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    x = XMPPComponent(args)
    def signal_handler(signal, frame):
        x.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, lambda _0, _1: x.update())

    try:
        while True:
            #handle messages locked
            with x.lock:
                asyncore.loop(timeout = 3.0, count = 10)
                for acc in x.accounts.itervalues():
                    if acc.connected:
                        acc.stack.do_detached_callback()
                    elif not acc.is_connecting:
                        acc.try_to_connect()
            # leave some time for threads and such
            time.sleep(3.0)
    except:
        x.shutdown()
        sys.exit(1)
