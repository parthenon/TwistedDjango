import json

from termcolor import colored
from inspect import stack


def who_called_me():
    """
        Return the name of the parent of the function that doesn't know where it came from.
    """
    return stack()[2][3]


def who_am_i():
    """
        Return the name of the function that doesn't know who it is.
    """
    return stack()[1][3]


def generic_deferred_errback(error, *args, **kwargs):
    if "message" in kwargs and not kwargs['message'].endswith('\n'):
        kwargs['message'] += '\n'

    m = colored(kwargs['message'], 'red', attrs=['bold'])
    e = colored(error, 'red')
    print(e + m)


class CommandResponse:
    def __init__(self,
                 deferred=None,
                 response={},
                 recipients=[],
                 deferred_response=None):
        self.response = response
        self.recipients = recipients
        self.cleanup_funcs = []
        self.deferred = deferred
        self.deferred_response = deferred_response
        self.everyone_else = False

    def distribute(self, command_name, connection, everyone_else=False):
        """
            Default recipient is the calling protocol.
            If the recipients list is not empty, send to all recipients.
        """
        self.command_name = command_name
        self.connection = connection
        self.everyone_else = everyone_else
        if self.deferred:
            self.deferred.addCallback(self._send_response)
        else:
            self._send_response()

    def _send_response(self, *args, **kwargs):
        if self.deferred_response:
            def_resp = self.deferred_response[0]
            def_resp_args = self.deferred_response[1]
        if len(self.recipients) == 0:
            self.connection.sendMessage(json.dumps({self.command_name: self.response}))
            if self.deferred_response:
                self.connection.sendMessage(json.dumps(def_resp(def_resp_args)))
        else:
            if self.everyone_else is True:
                recipients = filter(lambda a: a != self.connection, self.recipients)
                self.connection.factory.send_to_subset(
                    recipients,
                    json.dumps({self.command_name: self.response})
                    )
            else:
                self.connection.factory.send_to_subset(
                    self.recipients,
                    json.dumps({self.command_name: self.response}))

            if self.deferred_response:
                self.connection.factory.send_to_subset(self.recipients,
                                                       json.dumps(def_resp(def_resp_args)))

        #remove reference to deferred just in case that would interfere with garbage collection
        self.deferred = None

    def add_cleanup_func(self, func):
        self.cleanup_func.append(func)


class KeyNotAllowedError(KeyError):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ClientError(Exception):
    pass


class MissingKeyError(KeyError):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class DataSetNotAvailableError(ClientError):
    def __init__(self, value):
        self.value = value

    def __unicode__(self):
        return repr(self.value)
