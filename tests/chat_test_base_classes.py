# chat/tests/server_commands.py
"""
    Okay, this might get a little messy.  Django's testing framework and twisted aren't
    meant to play nicely together.
"""
from django import test
from connex.utilities.base_test import BaseTestCase
from connex.chat.management.commands.runchatserver import (start_chat_server, 
                                                           kill_chat_server)
from connex.chat.tests.client import (BaseChatClientProtocol, 
                                      ChatClientFactory, 
                                      ChatClientReactor,)
from twisted.internet import reactor
import subprocess

class DjangoChatBaseTestCase(test.TestCase):
    """
        This test case will test the server commands that are available to all of the clients.
        Users can:
            log out
            ignore people
        Coordinators can 
            kick people
            mute people (locally and globally)
        Class variables
            None
        Instance variables
            reactor: twisted reactor
                Client reactor 
            clients: [Web socket client protocol, ...]  
                list of the currently running clients
            conn_lost_events: What ever type the argument reason in clientConnectionLost is
                This is a list of clients that have lost their connection

    """
    def __new__(cls, *args, **kwargs):
        cls.test_factory = kwargs.get('test_factory', ChatClientFactory)
        return super(DjangoChatBaseTestCase, cls).__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        super(DjangoChatBaseTestCase, self).__init__(*args, **kwargs)
        self.clients = []

    @classmethod
    def setUpClass(cls):
        """
            Start the chat server
            Start the client reactor
            Call set up on the parent class
        """
        #TODO:  Log some users in
        #           User
        #           Mod
        #           Coordinator
        #       Test that they can issue role appropriate commands

        start_chat_server(31415)
        cls.reactor = ChatClientReactor(port=31415, 
                                         test_obj=cls, 
                                         factory_class=cls.test_factory)
        cls.reactor.start()

        #Parent class adds users and generates lists with first/last names, usernames, 
        #passwords, and emails
        super(DjangoChatBaseTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.reactor.crash()
        kill_chat_server(31415)
        
    def register_client(self, client):
        """
            The twisted client reactor is running in a differenct thread, when a protocol
            instance is created it will register that instance via this function.
        """
        if not client in self.clients:
            self.clients.append(client)

    def unregister_client(self, client):
        """
            The twisted client reactor is running in a differenct thread, when a protocol
            instance is removed it will unregister that instance via this function.
        """
        if client in self.clients:
            self.clients.remove(client)

    def log_connection_lost(self, reason):
        self.conn_lost_events.append(reason)

