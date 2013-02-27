import datetime
from dateutil.tz import tzutc

from django.dispatch import Signal
from django.http import HttpResponse

from twisted.internet.threads import deferToThread

from decorators import twisted_command
from twisted_command_utilities import CommandResponse, generic_deferred_errback


echo_test_signal = Signal(providing_args=['message', ])


@twisted_command('test', {})
def echo_test(request, connection, binary=None):
    d = deferToThread(echo_test_signal.send,
                      'echo_test',
                      message=request.get('message', ''))
    d.addErrback(generic_deferred_errback)

    response = {'time': round(float(datetime.datetime.now(tzutc()).strftime('%s.%f')), 0),
                'message': request.get('message', '')}
    return CommandResponse(response=response)


@twisted_command('authenticate', {})
def authenticate(msg, connection, *args, **kwargs):
    global_state = connection.factory.get_global_state()
    confs = global_state.get('conferences')
    conf_id = msg.get('conf_id')

    if confs.get(conf_id):
        confs.get(conf_id).append(connection)
    else:
        confs[conf_id] = [connection]


def ajax_get_session_id(request):
    return HttpResponse(str(request.session.session_key))
