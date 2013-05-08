from inspect import getargspec
from twisted_server import DjangoWSServerFactory
from twisted_command_utilities import (MissingKeyError,)


def init_twisted_module(func):
    DjangoWSServerFactory.register_command_module(func)

    def wrapper(factory, *args, **kwargs):
        return func(factory, *args, **kwargs)
    return wrapper


def twisted_command(run_once=False):
    def dec(func):
        (required_args, func_varargs, func_keywords, func_defaults) = getargspec(func)
        try:
            required_args.remove('connection')
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
                raise MissingKeyError(missing)
            return func(connection, **msg)
        command_name = func.__name__
        DjangoWSServerFactory.register_command(command_name, wrapper, run_once)
        return wrapper
    return dec
