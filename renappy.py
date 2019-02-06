import snappy
import simplejson as json

from redis import Redis
from redis.client import Pipeline


class Renappy(Redis):
    def __init__(self, host='localhost', port=6379,
                 db=0, password=None, socket_timeout=None,
                 socket_connect_timeout=None,
                 socket_keepalive=None, socket_keepalive_options=None,
                 connection_pool=None, unix_socket_path=None,
                 encoding='utf-8', encoding_errors='strict',
                 charset=None, errors=None,
                 decode_responses=False, retry_on_timeout=False,
                 ssl=False, ssl_keyfile=None, ssl_certfile=None,
                 ssl_cert_reqs='required', ssl_ca_certs=None,
                 max_connections=None):
        super().__init__(host=host, port=port, db=db, password=password, socket_timeout=socket_timeout,
                         socket_connect_timeout=socket_connect_timeout, socket_keepalive=socket_keepalive,
                         socket_keepalive_options=socket_keepalive_options,
                         connection_pool=connection_pool, unix_socket_path=unix_socket_path, encoding=encoding,
                         encoding_errors=encoding_errors,
                         charset=charset, errors=errors, decode_responses=decode_responses,
                         retry_on_timeout=retry_on_timeout, ssl=ssl,
                         ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile, ssl_cert_reqs=ssl_cert_reqs,
                         ssl_ca_certs=ssl_ca_certs,
                         max_connections=max_connections)
        self.works = 0
        self.p = self.pipeline()

    def pipeline(self, transaction=True, shard_hint=None):
        return RenappyPipeline(
            self.connection_pool,
            self.response_callbacks,
            transaction,
            shard_hint)

    def set_dict(self, key, o):
        self.set_str(key, json.dumps(o))

    def set_str(self, key, s):
        self.set(key, snappy.compress(s))

    def get_dict(self, key):
        return json.loads(self.get_str(key))

    def get_str(self, key):
        return snappy.decompress(self.get(key))

    def mget_str(self, keys):
        data = self.mget(keys)
        return [snappy.decompress(datum) for datum in data]

    def mget_dict(self, keys):
        data = self.mget(keys)
        return [json.loads(snappy.decompress(datum)) for datum in data]

    def set_empty_list_batch(self, key_sets):
        pipeline = self.pipeline()
        compressed_empty_list = snappy.compress(json.dumps([]))
        for i, key in enumerate(key_sets):
            if i % 100000 == 0:
                pipeline.execute()
            pipeline.set(key, compressed_empty_list)
        pipeline.execute()

    def push_batch(self, key, value):
        self.p.lpush(key, value)
        self.check_works_and_execute()

    def check_works_and_execute(self):
        self.works += 1
        if (self.works % 100000) == 0:
            self.p.execute()
            self.works = 0

    def pipe_force_execute(self):
        self.p.execute()


class RenappyPipeline(Pipeline, Renappy):
    pass
