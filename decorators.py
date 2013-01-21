from visualization.TwistedDjango.twisted_server import (DjangoWSServerProtocol, 
                                                        DjangoWSServerFactory,)
from visualization.TwistedDjango.twisted_command_utilities import (MissingKeyError,) 

#---------- Decorators ----------#

from termcolor import colored, cprint
import json

def init_twisted_module(func):
    DjangoWSServerFactory.register_command_module(func)
    def wrapper(factory, *args, **kwargs):
        return func(factory, *args, **kwargs)
    return wrapper

def twisted_command(key, required_args, run_once=False):
    def dec(func):
        def wrapper(msg, connection, *args, **kwargs):
            """
                Make sure to register the function with TwistedDjango!
            """
            missing = []
            for key in required_args:
                if key not in msg:
                    missing.append(key)
            if len(missing) > 0:
                raise MissingKeyError(missing)
            return func(msg, connection, *args, **kwargs)
        DjangoWSServerFactory.register_command(key, wrapper, run_once)
        return wrapper
    return dec
