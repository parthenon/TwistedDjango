import json

import logging
import os
import sys
import datetime
from options import get_options, get_empty_options

from django.utils import timezone

if 'TWISTED_TESTING' in os.environ:
    sys.path.extend(os.environ['TESTING_PATH'].split(os.pathsep))
    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
    options = None
    import settings
elif '-f' in sys.argv or '--path' in sys.argv:
    (options, args) = get_options()
    sys.path.insert(0, options.path)
    os.environ['PYTHONPATH'] = options.path
    os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
    import settings
else:
    try:
        from django.conf import settings
        if not hasattr(settings, 'TWISTED_DJANGO_PROJECT'):
            raise Exception("TWISTED_DJANGO_PROJECT setting not set")
        if not hasattr(settings, 'TWISTED_DJANGO_PATH'):
            raise Exception("TWISTED_DJANGO_PATH setting not set")
        options = get_empty_options()
        options.project = settings.TWISTED_DJANGO_PROJECT
        options.path = settings.TWISTED_DJANGO_PATH
        if hasattr(settings, 'TWISTED_DJANGO_PORT'):
            options.port = settings.TWISTED_DJANGO_PORT
        else:
            options.port = "8080"
        if hasattr(settings, 'TWISTED_DJANGO_DEBUG'):
            options.debug = True
        else:
            options.debug = False
    except Exception as e:
        raise e
#--------------- Set up the Django environment ---------------#

from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.db import models

#--------------- twisted server imports---------------#
from twisted.internet.threads import deferToThread
from twisted.internet import reactor, task
from twisted.internet.defer import Deferred
from twisted.python import log
from autobahn.websocket import (WebSocketServerFactory,
                                listenWS,
                                WebSocketServerProtocol)
from termcolor import colored, cprint
from inspect import isfunction

from twisted_command_utilities import (ClientError,
                                       who_called_me,
                                       generic_deferred_errback,)

PRINT_MESSAGES = False
DEBUG = True

logging.basicConfig()

AUTHENTICATION_FAILURE = 3000


def printerror(msg):
    errormsg = '{0}: {1}'.format(who_called_me(), msg)
    cprint(errormsg, 'red')


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

        self.conn_state = {}
        for key, value in self.commands.items():
            self.conn_state[key] = value
        self.conn_state.update(connection_state={})
        self._local_state = {}
        try:
            self.default_command = self.commands.pop('default')
        except KeyError:
            pass
        if 'TWISTED_TESTING' in os.environ:
            self.begin_testing()

    def onClose(self, wasClean, code, reason):
        try:
            close_handler = self.commands.get('onClose', None)
        except AttributeError:
            close_handler = None

        if not close_handler:
            return

        if self.user:
            user_id = self.user.pk
        else:
            user_id = None
        self.factory.unregister(self)

        message = {
            'user_id': user_id,
            'type': self.get_state('type')
        }

        close_handler(message, self)

    def onMessage(self, msg, binary):
        """
            Process a message from the client.
            msg: string
                This is assumed to be json.  If it's not a default function will be run.
        """
        message = None
        cprint(msg, 'green')
        self.logger.debug(msg)
        try:
            self.logger.debug('Loading JSON')
            message = json.loads(msg)
        except ValueError:
            self.logger.debug('Error loading json.')
            if self.default_command:
                self.default_command(msg, binary)
        if not message:
            return

        return self.process_message(message, binary)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

    def process_event(self, msg, binary, *args, **kwargs):
        pass

    def process_message(self, msg, binary, *args, **kwargs):
        """
            All functions will be sent the value associated with their keyword, the binary,
            the response dict, and a reference to self.

            Note: The unimplemented keyword is reserved and is not allowed to be
            added to the response['errors'] dict by command functions.
        """
        errors = {}
        unimplemented = []
        test_output = []
        self.logger.debug(msg)
        for command, val in msg.items():
            function = self.commands.get(command, None)
            if function:
                self.current_command = command
                try:
                    if PRINT_MESSAGES is True:
                        cprint('processing django command: {0}'.format(json.dumps(msg, indent=4,
                               sort_keys=True)), 'blue')
                    r = function(val, self, binary=binary)
                    if r is not None and not isinstance(r, Deferred):
                        r.distribute(self.current_command, self)
                    else:
                        test_output.append(r)
                except ClientError as e:
                    self.logger.error(e)
                    errors.update({command: e.message})
                self.current_command = ''
            else:
                unimplemented.append(command)
                if 'unimplemented' in errors:
                    raise KeyError("Do not add the key 'unimplemented' to the response dict.  It is reserved by the command protocol.")
        if len(unimplemented) > 0:
            errors.update(unimplemented=unimplemented)
        if len(errors) > 0:
            self.sendMessage(json.dumps({'errors': errors}))
        if len(test_output) != 0:
            return test_output

    def get_connection_state(self):
        state = self.conn_state[self.current_command]
        state.update(connection_state=self.conn_state.get(self.connection_state))
        return state

    def update_connection_state(self, state={}):
        """
           Add a key value pair to the protocol's global state.
           This is used to keep information accross commands.
           The argument state is required to be a dict
        """
        self.conn_state.get(self.current_command).update(state)

    def is_authenticated(self):
        if self.session:
            return True
        else:
            return False

    def confirm_session(self, *args, **kwargs):
        self.session_id = kwargs.pop('session_id', None)
        self.logger.debug('Entering confirm_session session_id:%s' % self.session_id)
        if not self.session or isinstance(self.session, models.Model):
            cprint('Loading session', 'red')
            try:
                session = Session.objects.get(pk=self.session_id)
                uid = session.get_decoded().get('_auth_user_id')
                user = User.objects.get(pk=uid)
                self.logger.debug(user.username)
                self.session = session.get_decoded()
                cprint('session: {0}'.format(self.session), 'red')
                self.user = user
            except Session.DoesNotExist:
                self.logger.debug('Session does not exist!')
                session = None
                user = None

        #self.logger.debug('uid, session: %s, %s' % (str(uid), str(session)))
        return session, user

    def session_success(self, res):
        if res:
            session, user = res
            if user.is_authenticated():
                auth_response = {'authenticate': {'authenticate': 'success'}}
            else:
                    auth_response = {'authenticate': {'authenticate': 'failure'}}
            self.sendMessage(json.dumps(auth_response))

    def session_error(self, err):
        h = colored('Session Confirmation Errback: '
                    'An error ocurred during session verification\n',
                    'red')
        e = colored(err, 'red', attrs=['bold'])
        print (e + h)

        auth_response = {'authenticate': {'authenticate': 'failure'}}
        self.sendMessage(json.dumps(auth_response))

        self.logger.debug('Session error: %s' % str(err))
        self.sendClose(code=AUTHENTICATION_FAILURE, reason=u'Invalid session id.')
        self.factory.unregister(self)

    def update_session(self, key, value):
        self.session[key] = value
        d = deferToThread(Session.objects.save,
                          self.session_id,
                          self.session,
                          timezone.make_aware(datetime.datetime(2037, 1, 1, 0, 0),
                          timezone.get_default_timezone()))

        def cb(s):
            cprint(s, 'cyan')
            cprint(s.get_decoded(), 'cyan')
            s.save()

        d.addCallback(cb)
        d.addErrback(generic_deferred_errback, message='Update Session')

    def remove_from_session(self, key):
        del self.session[key]
        deferToThread(self.session_inst.objects.save,
                      self.session_id,
                      self.session,
                      self.session_inst.expire_date)

    def callLater(self, seconds, func, *args, **kwargs):
        task.deferLater(reactor, seconds, func, *args, **kwargs)

    def get_state(self, key, default=None):
        try:
            return self._local_state[key]
        except KeyError:
            return default

    def set_state(self, key, value):
        self._local_state[key] = value

    def begin_testing(self):
        self.sendMessage = self.test_send
        self.message_buffer = []
        self.deferreds = {}
        self.session = {
            'testing': True
        }

    def test_send(self, payload, binary=False, payload_frag_size=None, sync=False):
        self.message_buffer.append({
            'binary': binary,
            'payload_frag_size': payload_frag_size,
            'payload': payload,
            'sync': sync,
        })


class DjangoWSServerFactory(WebSocketServerFactory):
    """
    """
    command_modules_init = []
    commands = {}

    def __init__(self, url, commands={}, debug=False, debugCodePaths=False):
        self.load_commands(commands)
        cprint('Modules: {0}'.format(self.command_modules_init), 'yellow')
        cprint('Commands: {0}'.format(self.commands), 'yellow')
        cprint('Initializing Protocol...', 'green')
        cprint('{0}'.format(settings.TWISTED_STUFF), 'red')

        WebSocketServerFactory.__init__(self, url, debug=debug, debugCodePaths=debugCodePaths)

        #Protocol instances are the keys, django users are the values.
        self.clients = {}
        self.client_count = 0

        #This is the global state for all connections.
        self.conn_state = {}

        for module in self.command_modules_init:
            module(self)

        keys = sorted(self.commands.keys())
        for com in keys:
            cprint("\t{0}: {0}".format(com, self.commands.get(com)), 'yellow')

    def register(self, client):
        self.client_count += 1
        self.clients.update({client: self.client_count})
        self.conn_state.update({client: {}})
        client.user_number = self.client_count

    def unregister(self, client):
        other_users = []
        for conf_id, conn_list in self.conn_state['conferences'].items():
            if client in conn_list:
                self.conn_state['conferences'][conf_id].remove(client)
                other_users = self.conn_state['conferences'][conf_id]

        if client.session is not None:
            connection_closed = {
                'connection_closed': {
                    'name': client.session.get('name', ''),
                    'user_number': client.user_number,
                }
            }
        self.send_to_subset(other_users, json.dumps(connection_closed))

        if client in self.clients:
            del self.clients[client]
        if client in self.conn_state:
            del self.conn_state[client]

    def broadcast(self, msg):
        if type(msg) == dict:
            msg = json.dumps(msg)
        for c in self.clients:
            c.sendMessage(msg)

    def send_to_subset(self, clients, msg):
        msg = json.dumps(json.loads(msg))
        if DEBUG:
            cprint('Sending to browser: {0}'.format(msg), 'yellow')
        for client in clients:
            if client in self.clients:
                client.sendMessage(msg)

    def load_commands(self, comm):
        """
        Import commands form a dict.
        {<type 'str'>:<type 'function'>, ...}
        Will raise a ValueError if the types are incorrect.
        """
        for key, value in comm.items():
            if not isfunction(value):
                try:
                    module = ".".join(value.split(".")[:-1])
                    func = value.split(".")[-1]
                    _temp = __import__(module, globals(), locals(), [func, ], -1)
                    value = getattr(_temp, func)
                    comm[key] = value
                except ImportError:
                    pass
            if not isinstance(key, str) or not isfunction(value):
                raise ValueError(u'All server commands must be string:function pairs.')
            self.commands = comm

    def get_global_state(self):
        return self.conn_state

    def update_global_state(self, state):
        self.conn_state.update(state)

    def get_client_by_number(self, client_number):
        for client, number in self.clients.items():
            if number == client_number:
                return client

    @classmethod
    def register_command(cls, key, func, run_once=False):
        if key in cls.commands:
            cls.commands[key] = func
            if not isinstance(key, str) or not isfunction(func):
                raise ValueError(u'All server commands must be string:function pairs.')
        else:
            cls.commands[key] = func

    @classmethod
    def remove_command(cls, key, func, run_once=False):
        del cls.commands[key][func]

    @classmethod
    def register_command_module(cls, init_func):
        cls.command_modules_init.append(init_func)


def run_server(commands, sslcontext = None):
    port = '31415'
    if options is not None and options.debug:
        port = options.port
        log.startLogging(open('/var/log/autobahn_chat.log', 'w'))
        debug = True
    else:
        debug = False
    debug = True

    if sslcontext is not None:
        factory = DjangoWSServerFactory("wss://localhost:" + port,
                                        commands=commands,
                                        debug=debug,
                                        debugCodePaths=debug)
    else:
        factory = DjangoWSServerFactory("ws://localhost:" + port,
                                        commands=commands,
                                        debug=debug,
                                        debugCodePaths=debug)

    cprint('Created factory: {0}'.format(factory), 'green')

    factory.protocol = DjangoWSServerProtocol
    factory.setProtocolOptions(allowHixie76=True)
    if 'TWISTED_TESTING' not in os.environ:
        cprint('Listening...', 'green')
        if sslcontext is not None:
            listenWS(factory, sslcontext)
            reactor.run()
        else:
            listenWS(factory)
            reactor.run()
