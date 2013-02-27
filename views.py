import datetime
from dateutil.tz import tzutc

from django.dispatch import Signal

from twisted.internet.threads import deferToThread

from decorators import twisted_command
from twisted_command_utilities import CommandResponse, generic_deferred_errback


echo_test_signal = Signal(providing_args=['name',
                                          'message',
                                          'private',
                                          'recipient'])


@twisted_command('test', {})
def echo_test(request, connection):
    private_message = True if 'private_message' in request else False
    if private_message:
        recip = None
    else:
        recip = request.get(u'recipient')

    d = deferToThread(echo_test_signal.send,
                      'echo_test',
                      name=connection.sessoin['name'],
                      message=request.get('message', ''),
                      private=private_message,
                      recipient=recip)
    d.addErrback(generic_deferred_errback)

    response = {'time': round(float(datetime.datetime.now(tzutc()).strftime('%s.%f')), 0),
                'name': connection.session.get('name', ''),
                'message': request.get('message', ''),
                'private_message': private_message,
                'recipient': recip}
    return CommandResponse(response=response, recipeints=None)
