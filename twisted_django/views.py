import datetime
from dateutil.tz import tzutc

from django.dispatch import Signal
from django.http import HttpResponse

from twisted.internet.threads import deferToThread

from decorators import twisted_command
from twisted_command_utilities import CommandResponse, generic_deferred_errback


def ajax_get_session_id(request):
    return HttpResponse(str(request.session.session_key))
