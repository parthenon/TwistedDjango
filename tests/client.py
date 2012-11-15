# chat/tests/client.py

from twisted.internet import reactor
from autobahn.websocket import (WebSocketClientFactory, 
                                WebSocketClientProtocol,
                                connectWS)
import threading
                                                               
                                                                
class BaseChatClientProtocol(WebSocketClientProtocol, object):
    """
        This is the communication gateway between the test suite for the Django chat app
        and the test server.
    """
    def __init__(self, *args, **kwargs):
        """
            If the username key word arg is present the client will send the user name with all
            messages.
        """
        self.username = None
        try:
            self.username = self.pop('username')
        except KeyError:
            username = 'TestUser'
        finally:
            super(SimpleChatClientProtocol, self).__init__(*args, **kwargs)

        self.messages = []

    def clientConnectionLost(self, connector, reason):
        """
            If the connection is lost the test object should be notified.
        """
        self.test_obj.log_connection_lost(reason)  

    def onMessage(self, msg, binary):
        """
            Pass any message received from the server to the test_obj
        """
        self.messages.append(msg)

    def pop_msg(self):
        try:
            return self.message.pop()
        except IndexError:
            return None
        
    def sendTestMessage(self, message):
        """
            Used by the test object to send messages to the server.
        """
        self.sendMessage(message)

    def onOpen(self):
        self.factory.register(self)

    def setTestObject(self, obj):
        self.factory.test_obj = obj


class ChatClientFactory(WebSocketClientFactory, object):
    """
        When this factory starts it will create a single client by default.
        If given a list of Django Users via the named argument users it 
        will create a protocol instance for each user.
    """
    def __init__(self, *args, **kwargs):
        self.clients = []
        try:
            self.test_obj = kwargs.pop('test_obj')
            users = self.pop('users')
        except KeyError:
            pass
        finally:
            super(ChatClientFactory, self).__init__(*args, **kwargs)
        #TODO: Iterator over the users list and use the inherited buildProtocol function 
        #to create a client for each user

    def register(self, client):
        """
            register the client with this factory and the test object.
        """
        if not client in self.clients:
            self.clients.append(client)
            self.test_obj.register_client(client)

    def unregister(self, client):
        if client in self.clients:
            self.clients.remove(client)
            self.test_obj.unregister(client)


class ChatClientReactor(threading.Thread):
    """
        This class wraps the Autobahn/Twisted reactor so that it can run in a separate
        daemonized thread.  This allows testing to be done with out giving the Twisted
        event loop full bloking control.
    """
    def __init__(self, *args, **kwargs): 
        """
            Make this a thread a daemon, get the port number and set up the factory.
        """
        daemon = True
        
        port = kwargs.pop('port', 31415)
        self.test_obj = kwargs.pop('test_obj', None)
        self.factory_class = kwargs.pop('factory_class', BaseChatClientProtocol)
        print 'factory_class: ' + str(self.factory_class)
        
        super(ChatClientReactor,self).__init__(*args, **kwargs)

        self.factory = self.factory_class("ws://localhost:%s" % str(port), debug = True)
        self.factory.protocol = BaseChatClientProtocol
        connectWS(self.factory)

    def run(self):
        """
            Start the reactor.
        """
        reactor.run()


