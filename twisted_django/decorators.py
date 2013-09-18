from inspect import getargspec
#from termcolor import cprint
from twisted_server import DjangoWSServerFactory
from twisted_command_utilities import (MissingKeyError,)


def init_twisted_module(func):
    DjangoWSServerFactory.register_command_module(func)

    def wrapper(factory, *args, **kwargs):
        return func(factory, *args, **kwargs)
    return wrapper


def protocol_teardown_function(func):
    DjangoWSServerFactory.register_teardown_function(func)

    def wrapper(protocol, *args, **kwargs):
        return func(protocol, *args, **kwargs)
    return wrapper


def twisted_command(run_once=False):

    def dec(func):
        (required_args, func_varargs, func_keywords, func_defaults) = getargspec(func)
        try:
            required_args.remove('connection')
            if func_defaults is not None:
                required_args = required_args[0:-len(func_defaults)]
        except ValueError:
            print('ArgumentError: The connection argument is required for all command functions.')
            print('Error in the definition of {}'.format(func))

        def wrapper(msg, connection, *args, **kwargs):
            """
                Make sure to register the function with TwistedDjango!
            """
            missing = []
            for arg in required_args:
                if arg not in msg:
                    missing.append(arg)
            if len(missing) > 0:
                raise MissingKeyError("The command {cmd} is missing the following arguments: {missing}"
                                      .format(cmd=func.__name__, missing=missing))
            return func(connection, **msg)
        command_name = func.__name__
        DjangoWSServerFactory.register_command(command_name, wrapper, run_once)
        return wrapper
    return dec


def on_close(func):
    DjangoWSServerFactory.register_event('close', func)
    return func



