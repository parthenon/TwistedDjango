import json
import logging
import os
import Queue
import re
import sys

#--------------- Set up the Django environment ---------------#
from django.conf import settings

from django.db.models.loading import get_apps

get_apps()
from django.contrib.sessions.models import Session

#--------------- twisted server imports---------------#
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.internet.task import LoopingCall
from twisted.python import log

from autobahn.websocket import (WebSocketServerFactory,
                                WebSocketServerProtocol,
                                listenWS)
from termcolor import colored, cprint
from inspect import isfunction

from twisted_command_utilities import (ClientError,
                                       DataSetNotAvailableError,
                                       who_called_me,
                                       generic_deferred_errback,)
import wssettings

PRINT_MESSAGES = False
DEBUG = True

logging.basicConfig()

AUTHENTICATION_FAILURE = 30000


def printerror(msg):
    errormsg = '{}: {}'.format(who_called_me(), msg)
    cprint(errormsg, 'red')


class AtExit(object):
    def __init__(self):
        self.pid = os.getpid()
        self.pid_lock_stub = '/tmp/server%s.pid'

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if len(sys.argv) > 1:
            try:
                os.remove(os.path.join(self.pid_lock_stub % int(sys.argv[1])))
            except OSError:
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
        cprint('Initializing Protocol...', 'green')
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

        self.conn_state = {key: None for key, value in self.commands.items()}
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
        #if 'authenticate' in message:
        #    self.logger.debug('authenticating')
        #    auth = message.pop('authenticate')
        #    self.logger.debug(auth)
        #    d = deferToThread(self.confirm_session, session_id=auth)
        #    d.addCallback(self.session_success)
        #    d.addErrback(self.session_error)
        #    return

        self.process_message(message, binary)

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
        self.logger.debug(msg)
        for command, val in msg.items():
            function_list = self.commands.get(command, None)
            if function_list:
                self.current_command = command
                for func in function_list:
                    try:
                        if PRINT_MESSAGES is True:
                            cprint('processing django command: {0}'.format(json.dumps(msg, indent=4, sort_keys=True)), 'blue')
                        r = func(val, self, binary=binary)
                        if r:
                            r.distribute(self.current_command, self)
                    except ClientError as e:
                        self.logger.error(e)
                        errors.update({command: e.message})
                    self.current_command = ''
                    if function_list[func] is True:
                        function_list.remove(func)
            else:
                unimplemented.append(command)
                if 'unimplemented' in errors:
                    raise KeyError("Do not add the key 'unimplemented' to the response dict.  It is reserved by the command protocol.")
        if len(unimplemented) > 0:
            errors.update(unimplemented=unimplemented)
        if len(errors) > 0:
            self.sendMessage(json.dumps({'errors': errors}))

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
            try:
                session = Session.objects.get(pk=self.session_id)
                uid = session.get_decoded().get('_auth_user_id')
                user = User.objects.get(pk=uid)
                self.session = session
            except Session.DoesNotExist:
                self.logger.debug('Session does not exist!')

        self.logger.debug('uid, session: %s, %s' % (str(uid), str(session)))
        return session, user

    def session_success(self, res):
        session = res
        self.session_inst = session
        self.session = session.get_decoded()
        admin_access = False
        if self.session.get('admin_access', False) is True:
            self.update_session('permissions', self.conf_perms[0])
            admin_access = True
        else:
            self.update_session('permissions', self.conf_perms[len(self.conf_perms) - 1])
        #if self.session.get('logged_in', False) is True or admin_access is True:
        #    auth_response = {'authenticate': {'authenticate': 'success'}}
        #else:
        #    auth_response = {'authenticate': {'authenticate': 'failure',
        #                                      'loginUrl': reverse('conference_login')}}
        #self.sendMessage(json.dumps(auth_response))

    def session_error(self, err):
        h = colored('Session Confirmation Errback: '
                    'An error ocurred during session verification\n',
                    'red')
        e = colored(err, 'red', attrs=['bold'])
        print (e + h)

        #auth_response = {'authenticate': {'authenticate': 'failure',
        #                                  'loginUrl': reverse('conference_login')}}
        #self.sendMessage(json.dumps(auth_response))

        #self.logger.debug('Session error: %s' % str(err))
        #self.sendClose(code=AUTHENTICATION_FAILURE, reason=u'Invalid session id.')
        self.factory.unregister(self)

    def update_session(self, key, value):
        return True
        self.session[key] = value
        d = deferToThread(Session.objects.save,
                          self.session_id,
                          self.session,
                          self.session_inst.expire_date)
        d.addErrback(generic_deferred_errback, message='Update Session')

    def remove_from_session(self, key):
        del self.session[key]
        deferToThread(self.session_inst.objects.save,
                      self.session_id,
                      self.session,
                      self.session_inst.expire_date)


class DjangoWSServerFactory(WebSocketServerFactory):
    """
    """
    command_modules_init = []
    commands = {}

    def __init__(self, url, debug=False, debugCodePaths=False):
        cprint('Modules: {}'.format(self.command_modules_init), 'yellow')
        cprint('Commands: {}'.format(self.commands), 'yellow')
        cprint('Initializing Protocol...', 'green')

        WebSocketServerFactory.__init__(self, url, debug=debug, debugCodePaths=debugCodePaths)

        #Protocol instances are the keys, django users are the values.
        self.clients = {}
        self.client_count = 0

        #This is the global state for all connections.
        self.conn_state = {}

        self.update_queue = Queue.Queue()

        lc = LoopingCall(self.process_data)
        lc.start(0)

        for module in self.command_modules_init:
            module(self)

    def register(self, client):
        self.client_count += 1
        self.clients.update({client: self.client_count})
        self.conn_state.update({client: {}})
        client.user_number = self.client_count

    def unregister(self, client):
        return
        if client in self.clients:
            del self.clients[client]
        if client in self.conn_state:
            del self.conn_state[client]

        for conf_id, conn_list in self.conn_state['conferences'].items():
            for conn in conn_list:
                if conn is client:
                    self.conn_state['conferences'][conf_id].remove(conn)

    def broadcast(self, msg):
        if type(msg) == dict:
            msg = json.dumps(msg)
        for c in self.clients:
            c.sendMessage(msg)

    def send_to_subset(self, clients, msg):
        msg = json.dumps(json.loads(msg), indent=4, sort_keys=True)
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
                module = ".".join(value.split(".")[:-1])
                func = value.split(".")[-1]
                _temp = __import__(module, globals(), locals(), [func, ], -1)
                value = getattr(_temp, func)
            if not isinstance(key, str) or not isfunction(value):
                raise ValueError(u'All server commands must be string:function pairs.')
            self.commands = comm

    def get_global_state(self):
        return self.conn_state

    def update_global_state(self, state):
        self.conn_state.update(state)

    def process_data(self, *args, **kwargs):
        if self.update_queue.empty():
            return
        while not self.update_queue.empty():
            message = self.update_queue.get(False)
            try:
                if message['type'] != 'message':
                    continue
            except (TypeError, KeyError):
                continue
            for conn in self.conn_subscriptions[message['channel']]:
                msg = json.dumps({
                    'new_data_point': {
                        'key': message['channel'],
                        'data': message['data']['data'],
                        'time': message['data']['time'],
                    },
                })
                #cprint('sending {} to {} '.format(msg, str(conn)))
                conn.sendMessage(msg)

    def subscribe(self, connection, regex):
        """
            Key is a string
        """
        print 'RegEx: ' + regex
        if type(regex) == str or type(regex) == unicode:
            regex = re.compile(regex)
        for key, conn_list in self.conn_subscriptions.items():
            if regex.match(key) is not None:
                print 'Match: ' + str(regex.match(key))
                conn_list.append(connection)
                print 'RegEx: ' + str(self.conn_subscriptions)
                return True
        if DEBUG:
            printerror('No key matching your regex was found.')
            printerror(self.conn_subscriptions)

        raise DataSetNotAvailableError('The key {} is not active.'.format(regex))

    def unsubscribe(self, connection, regex):
        """
            Key is a string
        """
        if type(regex) == str:
            regex = re.compile(str)
        for key, conn_list in self.conn_subscriptions.items():
            if regex.match(key):
                try:
                    conn_list.remove(connection)
                except ValueError:
                    raise KeyError('This connection is not subscribed to this data feed.')
                    if DEBUG:
                        printerror('You are not subscribed to that feed.')

    @classmethod
    def register_command(cls, key, func, run_once=False):
        if key in cls.commands:
            cls.commands[key].update({func: run_once})
            if not isinstance(key, str) or not isfunction(func):
                raise ValueError(u'All server commands must be string:function pairs.')
        else:
            cls.commands[key] = {func: run_once}

    @classmethod
    def remove_command(cls, key, func, run_once=False):
        del cls.commands[key][func]

    @classmethod
    def register_command_module(cls, init_func):
        cls.command_modules_init.append(init_func)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        log.startLogging(open('/var/log/autobahn_chat.log', 'w'))
        debug = True
    else:
        debug = False

    if len(sys.argv) > 1:
        factory = DjangoWSServerFactory("ws://localhost:{port}".format(port=sys.argv[1]),
                                        debug=debug,
                                        debugCodePaths=debug)
        factory.load_commands(wssettings.TWISTED_COMMANDS)
        factory.protocol = DjangoWSServerProtocol
        factory.setProtocolOptions(allowHixie76=True)
        listenWS(factory)

        reactor.run()


if __name__ == '__main__':
    with AtExit():
        main()
