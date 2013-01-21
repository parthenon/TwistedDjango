#{'pattern': None, 'type': 'subscribe', 'channel': 'foo', 'data': 1L}

from termcolor import cprint, colored
import threading, time, redis, json, sys, config

DEBUG = False

class RedisListener(threading.Thread):

    def __init__(self, factory):
        super(RedisListener, self).__init__()
        self.daemon = True
        self.factory = factory
        self.redis_server = redis.StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0)
        self.redis_pubsub = self.redis_server.pubsub()
        self.all_keys = self.redis_server.keys('*')
        self.active_keys = self.redis_server.lrange('data_keys',0,-1)
         
        for key in self.active_keys:
            if DEBUG is True:
                cprint(key, 'blue')
            self.redis_pubsub.subscribe(key)

    def get_all_keys(self, regex=None):
        return self.all_keys[:]
        
    def get_active_keys(self, regex=None):
        return self.active_keys[:]

    def update_active_keys(self): 
        new_key_set = self.redis_server.lrange('data_keys',0,-1)
        new_keys = []
        stale_keys = []

        #Get keys that are new
        for new_key in new_key_set:
            if new_key not in self.active_keys:
                new_keys.append(new_key)
                self.redis_pubsub.subscribe(new_key)

        #Get keys that are stale
        for old_key in self.active_keys:
            if old_key not in new_key_set:
                stale_keys.append(old_key)
                self.redis_pubsub.unsubscribe(old_key)

        #Update the list of active keys
        for key in stale_keys:
            self.active_keys.remove(key)
        self.active_keys.extend(new_keys)

    def run(self):
        for message in self.redis_pubsub.listen():
            try:
                message['data'] = json.loads(message.get('data'))
            except TypeError:
                msg = message.get('data')
            self.factory.update_queue.put(message)
            self.update_active_keys()

    def stop(self):
        del self.redis_pubsub
