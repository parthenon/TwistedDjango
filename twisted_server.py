# connex/chat/chat_server.py

#--------------- Set up the Django environment ---------------#
from django.core.management import setup_environ
from connex import settings

setup_environ(settings)
from django.db.models.loading import get_apps
from django.contrib.sessions.backends.db import SessionStore

get_apps()
import django.db.models
from django.contrib.sessions.models import Session

#--------------- twisted server imports---------------#
from django.core.urlresolvers import reverse
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.internet.defer import Deferred
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet.error import CannotListenError

from autobahn.websocket import (WebSocketServerFactory,
                                WebSocketServerProtocol,
                                listenWS)

from connex.conference.config import conf_perms
from connex.twisted_django_server.twisted_command_utilities import (ClientError, 
                                                                    CommandResponse,
                                                                    generic_deferred_errback,
                                                                    who_called_me)
from connex.twisted_django_server import wssettings

from termcolor import colored, cprint
import sys, logging, json, copy, os, logging
from inspect import isfunction, ismethod

logging.basicConfig(filename=os.path.join(settings.SITE_ROOT, 
                                           '../logs/spectel_api.log'))
AUTHENTICATION_FAILURE = 3000


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


class DjangoWSServerProtocol(WebSocketServerProtocol):
    """
        This is the protocol for a general purpose asyncronous server Autobahn WebSocket server.
        It has been integrated with Django, and ca therefore access models, signals, etc.
        When a connection is established the user's Django sessionId is verified thus
        authenticating the user.
    """
    def onOpen(self):
        self.factory.register(self)
        self.default_command = None
        self.commands = self.factory.commands
        self.deferred_responses = []
        self.session = None
        self.session_id = ''
        self.session_inst = None
        self.user = None
        self.logger = logging.getLogger(__name__)

        if settings.DEBUG:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.ERROR)

        self.conn_state = {key:None for key, value in self.commands.items()} 
        self.conn_state.update(connection_state={})
        try:
            self.default_command = self.commands.pop('default')
        except KeyError:
            pass

    def onMessage(self, msg, binary):
        """
            Process a message from the client.
            msg: string
                This is assumed to be json.  If it's not a default function will be run.
        """
        message = None
        self.logger.debug(msg)
        
        try:
            self.logger.debug('Loading JSON')
            message = json.loads(msg)

        except ValueError as e:
            self.logger.debug('Error loading json.')
            if self.default_command:
                self.default_command(msg, binary)
        if not message:
            return
        if 'authenticate' in message:
            self.logger.debug('authenticating')
            auth = message.pop('authenticate')
            self.logger.debug(auth)
            d = deferToThread(self.confirm_session, session_id=auth)
            d.addCallback(self.session_success)
            d.addErrback(self.session_error)
            return

        self.process_message(message, binary)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

    def process_message(self, msg, binary, *args, **kwargs):
        """
            All functions will be sent the value associated with their keyword, the binary, 
            the response dict, and a reference to self.

            Note: The unimplemented keyword is reserved and is not allowed to be 
            added to the response['errors'] dict by command functions.
        """
        errors = {}
        recipients = [self]
        unimplemented = []
        self.logger.debug(msg)
        for key, val in msg.items():
            func = self.commands.get(key, None)
            if func:
                self.current_key = key
                try:
                    cprint('processing django command: {0}'.format(json.dumps(msg, 
                                                                              indent=4,
                                                                              sort_keys=True)), 
                           'blue')
                    r = func(val, self, binary=binary)
                    if r:
                        r.distribute(self.current_key, self)
                except ClientError as e:
                    self.logger.error(e)
                    errors.update({key:e.message})
                self.current_key = ''
            else:
                unimplemented.append(key)
                if 'unimplemented' in errors:
                    raise KeyNotAllowedError("Do not add the key 'unimplemented' to the response dict.  It is reserved by the command protocol.")
        if len(unimplemented) > 0:
            errors.update(unimplemented=unimplemented)
        if len(errors) > 0:
            self.sendMessage(json.dumps({'errors':errors}))

    def get_connection_state(self):
        state = self.conn_state[self.current_command]
        state.update(connection_state=self.conn_state.get(connection_state))
        return state

    def update_connection_state(self, state={}):
        """
           Add a key value pair to the protocol's global state.
           This is used to keep information accross commands.
           The argument state is required to be a dict
        """
        self.conn_state.get(current_command).update(state)

    def is_authenticated(self):
        if self.session:
            return True
        else:
            return False

    def confirm_session(self, *args, **kwargs):
        self.session_id = kwargs.pop('session_id', None)
        self.logger.debug('Entering confirm_session session_id:%s' % self.session_id)
        if not self.session or isinstance(self.session, modles.Model):
            try:
                session = None
                uid = None
                session = Session.objects.get(pk=self.session_id)
            except Session.DoesNotExist:
                self.logger.debug('Session does not exist!')

        self.logger.debug('uid, session: %s, %s' % (str(uid), str(session)))
        return session

    def session_success(self, res):
        session = res
        self.session_inst = session
        self.session = session.get_decoded()
        admin_access = False
        if self.session.get('admin_access', False) is True:
            self.update_session('permissions', conf_perms[0])
            admin_access = True
        else:
            self.update_session('permissions', conf_perms[len(conf_perms) - 1])
        if self.session.get('logged_in', False) is True or admin_access is True:
            auth_response = {'authenticate':{'authenticate':'success'}}
        else:
            auth_response = {'authenticate':{'authenticate':'failure', 
                                            'loginUrl':reverse('conference_login')}}
        self.sendMessage(json.dumps(auth_response))

    def session_error(self, err):
        h = colored('Session Confirmation Errback: '
                    'An error ocurred during session verification\n',
                    'red')
        e = colored(err, 'red', attrs=['bold'])
        print (e+h)

        auth_response = {'authenticate':{'authenticate':'failure', 
                                        'loginUrl':reverse('conference_login')}}
        self.sendMessage(json.dumps(auth_response))
        
        self.logger.debug('Session error: %s' % str(err))
        self.sendClose(code=AUTHENTICATION_FAILURE, reason=u'Invalid session id.')
        self.factory.unregister(self)

    def update_session(self, key, value):
        self.session[key] = value
        d = deferToThread(Session.objects.save,
                          self.session_id,
                          self.session,
                          self.session_inst.expire_date)
        d.addErrback(generic_deferred_errback, message='Update Session')

    def remove_from_session(key):
        del self.session[key]
        d = deferToThread(self.session_inst.objects.save,
                          self.session_id,
                          self.session,
                          self.session_inst.expire_date)
        

class DjangoWSServerFactory(WebSocketServerFactory):
    """
    """
    def __init__(self, url, debug = False, debugCodePaths = False):
        WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debugCodePaths)
        #Protocol instances are the keys, django users are the values.
        self.clients = {}
        self.client_count = 0
        #This is the global state for all connections.
        self.conn_state = {}
        for module in wssettings.COMMAND_MODULES:
            module.initialize(self)
        
    def register(self, client):
        self.client_count += 1
        self.clients.update({client:self.client_count})
        self.conn_state.update({client:{}})
        print 'Client number:{0}:{1} '.format(self.client_count, who_called_me())
        client.user_number = self.client_count

    def unregister(self, client):
        if client in self.clients:
            del self.clients[client]
        if client in self.conn_state:
            del self.conn_state[client]

        for conf_id, conn_list in self.conn_state['conferences'].items():
            for conn in conn_list:
                if conn is client:
                    self.conn_state['conferences'][conf_id].remove(conn)
        
    def broadcast(self, msg):
        for c in self.clients:
            c.sendMessage(msg)
    
    def send_to_subset(self, clients, msg):
        msg = json.dumps(json.loads(msg), indent=4, sort_keys=True)
        cprint('Sending to browser: {0}'.format(msg), 'yellow')
        for client in clients:
            if client in self.clients:
                client.sendMessage(msg)

    def load_commands(self, comm):
        """
            Import commands from a dict.
            {<type 'str'>:<type 'function'>, ...}
            Will raise a VauleError if the types are incorrect.
        """
        for key, value in comm.items():
            if not isinstance(key, str) or not isfunction(value):
                raise ValueError(u'All server commands must be string:function pairs.')
            self.commands = comm

    def get_global_state(self):
        return self.conn_state

    def update_global_state(self, state):
        self.conn_state.update(state)

    def get_user_by_number(self, user_number):
        for client, number in self.clients.items():
            if number == user_number:
                return client

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        log.startLogging(open('/var/log/autobahn_chat.log', 'w'))
        debug = True
    else:
        debug = False
    
    if len(sys.argv) > 1:
        factory = DjangoWSServerFactory("ws://localhost:" + '31415', 
                                         debug=debug, 
                                         debugCodePaths=debug)

        factory.load_commands(wssettings.TWISTED_COMMANDS)
        factory.protocol = DjangoWSServerProtocol
        factory.setProtocolOptions(allowHixie76 = True)
        listenWS(factory)

        webdir = File(".")
        web = Site(webdir)
        try:
            reactor.listenTCP(int(sys.argv[1]), web)
        except CannotListenError as error:
            print 'There was a problem opening the specified port number.'
            print error
            sys.exit()
            
        reactor.run()

if __name__ == '__main__':
    with AtExit():    
        main()

