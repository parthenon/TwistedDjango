#viualization/TwistedDjango/twisted_server.py

#--------------- Set up the Django environment ---------------#
from django.core.management import setup_environ
from visualization import settings

setup_environ(settings)
from django.db.models.loading import get_apps
from django.contrib.sessions.backends.db import SessionStore

get_apps()
import django.db.models
from django.contrib.sessions.models import Session

from termcolor import colored, cprint
import sys, logging, json, copy, os, logging, redis, Queue, re, time
from inspect import isfunction, ismethod
from visualization.TwistedDjango.twisted_server import (DjangoWSServerProtocol, 
                                                        DjangoWSServerFactory,)
from autobahn.websocket import listenWS
from twisted.web.static import File
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.internet.error import CannotListenError

import wssettings

AUTHENTICATION_FAILURE = 3000

PRINT_MESSAGES = False
DEBUG = False

class AtExit(object):

    def __init__(self):
        self.pdi = os.getpid()
        self.pid_lock_stub = 'django_twisted_server/management/server%s.pid' 

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if len(sys.argv) > 1:
            try:
                os.remove(os.path.join(settings.SITE_ROOT, self.pid_lock_stub % int(sys.argv[1])))
            except OSError as e:
                pass
        else:
            print 'You must provide a valid port number.'

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        log.startLogging(open('/var/log/autobahn_chat.log', 'w'))
        debug = True
    else:
        debug = False
    debug = True
    
    if len(sys.argv) > 1:
        factory = DjangoWSServerFactory("ws://localhost:" + '31415', 
                                         debug=debug, 
                                         debugCodePaths=debug)
        cprint('Created factory: {}'.format(factory), 'green')

        #factory.load_commands(wssettings.TWISTED_COMMANDS)
        factory.protocol = DjangoWSServerProtocol
        factory.setProtocolOptions(allowHixie76 = True)
        listenWS(factory)
        cprint('Listening...', 'green')

        webdir = File(".")
        web = Site(webdir)
        try:
            reactor.listenTCP(int(sys.argv[1]), web)
            cprint('Reactor listening on {}'.format(sys.argv[1]), 'green')
        except CannotListenError as error:
            print 'There was a problem opening the specified port number.'
            print error
            sys.exit()

        cprint('Starting Reactor', 'green')
        reactor.run()
        

if __name__ == '__main__':
    #with AtExit():    
    main()


