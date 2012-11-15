# connex/chat/runserver.py

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from connex.chat.management.commands._private import kill_chat_server

class Command(BaseCommand):
    args = '<port number>'
    help = 'Stop the Autobahn chat server on the specified port number. \n\tstopchatserver port_number'

    def handle(self, *args, **kwargs):
        kill_chat_server(*args, **kwargs)



        
