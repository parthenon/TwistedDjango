#--------------- Set up the Django environment ---------------#
from django.core.management import setup_environ
from visualization import settings

setup_environ(settings)
from django.db.models.loading import get_apps
from django.contrib.sessions.backends.db import SessionStore

get_apps()
import django.db.models
from django.contrib.sessions.models import Session

#--------------- Start of WebSocketServer settings ---------------#
#---------------    Import all command functions   ---------------#

from visualization.visualization.twisted_collection import * 

