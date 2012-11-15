# connex/chat/runserver.py

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from connex.twisted_django_server.management.commands._private import (start_twisted_server, 
                                                                      kill_twisted_server,)

class Command(BaseCommand):
    args = 'start|stop <port number>'
    help = 'Run the Autobahn server on the specified port number. \n\truntwistedserver port_number'

    def handle(self, *args, **kwargs):
        temp = list(args)
        if len(temp) > 1:
            command = temp.pop(0)
            if command == 'start':
                start_twisted_server(temp, **kwargs)        
            elif command == 'stop':
                kill_twisted_server(temp, **kwargs)



        
