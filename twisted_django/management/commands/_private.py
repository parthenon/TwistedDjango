# connex/twisted/management/commands/_private.py

from django.conf import settings

from subprocess import Popen
import os
import sys
import psutil
import time


#This is here to clean up code and shorten line lengths
try:
    DEFAULT_TWISTED_PORT = settings.DEFAULT_TWISTED_PORT
except AttributeError:
    DEFAULT_TWISTED_PORT = '8080'

SITE_ROOT = settings.SITE_ROOT

pid_lock_stub = '/tmp/server%s.pid'
script_name = os.path.join(SITE_ROOT,
                           'TwistedDjango/twisted_server.py')


def start_twisted_server(args, **kwargs):
    #Start up an instance of a twisted server on a unique port
    signature = 'runtwistedserver port_number'
    if len(args) != 1:
        if server_already_running(DEFAULT_TWISTED_PORT):
            print 'A twisted server is already running on that port.'
            return
        else:
            twisted_env = os.environ
            twisted_env["PYTHONPATH"] = settings.SITE_ROOT + ':' + twisted_env["PATH"]
            sys.path.insert(0, os.path.join(os.path.join(settings.SITE_ROOT, '../'), "freelancecoach/"))

            server = Popen(['python', script_name, DEFAULT_TWISTED_PORT], env=twisted_env)
        with open(os.path.join(pid_lock_stub % DEFAULT_TWISTED_PORT), 'w') as f:
            f.write(str(server.pid) + '\n')
        print 'twisted server opened on default port number (%s).' % DEFAULT_TWISTED_PORT
    elif len(args) == 1:
        if server_already_running(args[0]):
            print 'A twisted server is already running on that port.'
            return
        else:
            try:
                twisted_env = os.environ
                twisted_env["PYTHONPATH"] = settings.SITE_ROOT + ':' + twisted_env["PATH"]
                sys.path.insert(0, os.path.join(os.path.join(settings.SITE_ROOT, '../'), "freelancecoach/"))

                server = Popen(['python', script_name, str(args[0])], env=twisted_env)
            except TypeError as e:
                print (e, script_name, args[0])
        with open(os.path.join(pid_lock_stub % args[0]), 'w') as f:
            f.write(str(server.pid) + '\n')
        print 'twisted server opened on port number %s.' % args[0]
    else:
        print ('twisted Server: Missing operand\n%s\nTry twisteddjango --help for more information.'
               % signature)
        return


def kill_twisted_server(args, **kwargs):
    """
    Open the lock file, get the pid and terminate the coresponding process

    """
    if len(args) == 1:
        try:
            port = args[0]
        except ValueError:
            print 'Invalid port number.'
            return False
    else:
        print 'You must provide the server\'s port number.'
        return False

    try:
        with open(os.path.join(SITE_ROOT, pid_lock_stub % port), 'r') as f:
            try:
                pid = int(f.read())
            except ValueError:
                return False
            proc = None
            if pid in psutil.get_pid_list():
                proc = psutil.Process(pid)
                proc.terminate()
            else:
                return False
            time.sleep(.5)

            if proc:
                try:
                    os.remove(os.path.join(settings.SITE_ROOT, pid_lock_stub % port))
                except OSError:
                    pass

                return True
            else:
                return False

    except IOError:
        print 'I do not have a record of a twisted server registered on that port.'
        return False

    print 'The twisted server running on port %s has been terminated.' % port
    return True


def server_already_running(port):
    try:
        with open(os.path.join(SITE_ROOT, pid_lock_stub % port), 'r') as f:
            try:
                pid = int(f.read())
            except ValueError:
                return False

            if pid in psutil.get_pid_list():
                return True
            else:
                return False
    except IOError:
        return False
