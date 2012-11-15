#--------------- Set up the Django environment ---------------#
from django.core.management import setup_environ
from connex import settings

setup_environ(settings)
from django.db.models.loading import get_apps
from django.contrib.sessions.backends.db import SessionStore

get_apps()
import django.db.models
from django.contrib.sessions.models import Session

#--------------- Start of WebSocketServer settings ---------------#
import example_module
from example_module import example_function

COMMAND_MODULES = (example_module,)


TWISTED_COMMANDS = {'command_key':example_function, } 
