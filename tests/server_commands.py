# chat/tests/server_commands.py
"""
    Okay, this might get a little messy.  Django's testing framework and twisted aren't
    meant to play nicely together.
"""
from django import test

from connex.chat.tests.chat_test_base_classes import DjangoChatBaseTestCase

import json, time, unittest

class TestChatCommands(DjangoChatBaseTestCase):
    def test_connect(self):
        """
            Test if the connect command works properly.
        """
        #Bad user name
        self.clients[0].sendTestMessage('%%connect {0}'.format('BadUsername'))
        response = None

        while response is None:
            response = self.clients[0].pop_msg()
        self.assertEqual(response, '{"error": "No such user"}')


        #Connect all of the users except for the first one.  We'll leave that one disconnected
        #to test what happens when a disconnected person some how manages to send
        #messages/commands
        for i, c in enumerate(self.usernames[1:]):
            self.clients[c].sendTestMessage('{"command": {"connect": "{0}"}}' % self.username)
        
        for i, c in enumerate(self.usernames[1:]):
            response = None
            while response is None:
                response = self.clients[0].pop_msg()
                self.assertEqual(response, '{"response": {"connected": "{0}"}}')

    def test_disconnect(self):
        """
            Test if the disconnect command works properly.
        """
        #The first user was never connected, see what happens when we try to disconnect them.
        self.clients[0].sendTestMessage(
            '{"command": {"disconnect": "{0}"}}'.format(self.usernames[0]))
        response = None

        time.sleep(1)
        response = self.clients[0].pop_msg()
        self.assertEqual(response, '{"error": "No such user"}')

        #Try to disconnect the rest of the users.
        for i, c in enumerate(self.usernames[1:]):
            self.clients[i].sendTestMessage(
                '{"command": {"disconnect": "{0}"}}'.format(self.usernames[i]))
        time.sleep(2)
        for i, c in enumerate(self.usernames[1:]):
            response = None
            response = self.clients[0].pop_msg()
            self.assertEqual(response, 
                             '{"response": {"goodbye": "{0}"}}'.format(self.usernames[i]))

    def test_ignore(self):
        """
            Ignore will block the messages from the specified user from appearing in 
            the current user's feed.
            Test if the the ignore command is handled properly.
        """
        pass

    def test_global_mute(self):
        """
           Coordinators can mute users that are being excessively annoying.
           Test if the the ignore command is handled properly.
        """
        pass

        
