#!/usr/bin/env python
import sys
import os
from options import get_options

(options, args) = get_options()

# ROOT needs to be set to the directory that contains settings.py
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from twisted.internet import reactor
from twisted.python import log

from autobahn.websocket import listenWS
from termcolor import cprint

from twisted_server import DjangoWSServerProtocol, DjangoWSServerFactory
import wssettings

AUTHENTICATION_FAILURE = 3000

PRINT_MESSAGES = False
DEBUG = False


def main():
    if options.debug:
        log.startLogging(open('/var/log/autobahn_chat.log', 'w'))
        debug = True
    else:
        debug = False
    debug = True

    factory = DjangoWSServerFactory("ws://localhost:" + options.port,
                                    debug=debug,
                                    debugCodePaths=debug)
    cprint('Created factory: {}'.format(factory), 'green')

    factory.load_commands(wssettings.TWISTED_COMMANDS)
    factory.protocol = DjangoWSServerProtocol
    factory.setProtocolOptions(allowHixie76=True)
    listenWS(factory)
    cprint('Listening...', 'green')

    reactor.run()


if __name__ == '__main__':
    import cProfile
    import time

    profileFileName = 'Profiles/pythonray_' + time.strftime('%Y%m%d_%H%M%S') + '.profile'

    profile = cProfile.Profile()
    profile.run('main()')

    profile.dump_stats(profileFileName)
    profile.print_stats()
