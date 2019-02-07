from io import BytesIO
import pickle
from collections import Counter

from datasketch import MinHash
from tiny_elephant.renappy import Renappy


class InMemoryCluster:
    def __init__(self, minhash_host='localhost:6379', secondary_index_host=None, minhash_db=1, secondary_index_db=2,
                 num_perm=128, seed=1, load_data_per=10000):
        if not secondary_index_host:
            secondary_index_host = minhash_host

        # minhash redis host, minhash redis port
        mr_host, mr_port = minhash_host.split(":")

        # secondary index redis host, secondary index redis port
        sr_host, sr_port = secondary_index_host.split(":")

        # minhash redis
        self.m_r = Renappy(host=mr_host, port=mr_port, db=minhash_db)
        # secondary index redis
        self.s_r = Renappy(host=sr_host, port=sr_port, db=secondary_index_db)
        self.num_perm = num_perm
        self.load_data_per = load_data_per
        self.seed = seed

    def flush_all(self):
        self.m_r.flushdb()
        self.s_r.flushdb()

    def init_cluster(self, data):
        for key, streams in data.items():
            self._generate_and_save_minhash(key, streams)
        keys = self.m_r.keys()
        self._generate_and_save_secondary_index(keys)

    def update_cluster(self, data):
        for key, streams in data.items():
            if self.m_r.exists(key):
                self._update_secondary_index(key, streams)
            else:
                self._generate_and_save_minhash(key, streams)
                self._generate_and_save_secondary_index([key])

    def most_common(self, key, count=10):
        byte_stream = BytesIO(self.m_r.get_str(key))
        minhash = self._byte_array_to_obj(byte_stream)
        ssi = self._search_secondary_index(minhash)
        # Remove self element
        return Counter(ssi).most_common(count + 1)[1:]

    def _generate_minhash(self, streams):
        minhash = MinHash(num_perm=self.num_perm, seed=self.seed)

        for stream in streams:
            minhash.update(stream.encode('utf-8'))

        return minhash

    def _generate_and_save_minhash(self, key, streams):
        minhash = self._generate_minhash(streams)
        byte_array = self._obj_to_byte_array(minhash)
        self.m_r.set_str(key, byte_array)

    def _load_minhash(self, data, batch_size):
        data_len = len(data)
        num_iter = data_len // batch_size
        for index in range(num_iter + 1):
            begin = index * batch_size
            end = begin + batch_size

            if end > data_len:
                end = -1

            batch_data = data[begin:end]
            batch_objs = self.m_r.mget_str(batch_data)
            batch_streams = [BytesIO(byte_obj) for byte_obj in batch_objs]

            batch_pairs = []
            for key, byte_stream in zip(batch_data, batch_streams):
                batch_pairs.append((key, self._byte_array_to_obj(byte_stream)))
            yield batch_pairs
        yield None

    def _generate_and_save_secondary_index(self, keys):
        batch_pairs = self._load_minhash(keys, self.load_data_per)
        while True:
            batch = next(batch_pairs)
            if not batch:
                break
            for key, hash_obj in batch:
                for i, hash_value in enumerate(hash_obj.digest()):
                    secondary_key = '{}-{}'.format(i, hash_value)
                    self.s_r.push_batch(secondary_key, key)
        self.s_r.pipe_force_execute()

    def _update_secondary_index(self, key, streams):
        byte_stream = BytesIO(self.m_r.get_str(key))
        hash_func = self._byte_array_to_obj(byte_stream)
        org_hash_values = hash_func.digest()
        for stream in streams:
            hash_func.update(stream.encode('utf-8'))
        update_hash_values = hash_func.digest()

        pipe = self.s_r.pipeline()
        for i in range(self.num_perm):
            if org_hash_values[i] != update_hash_values[i]:
                org_secondary_key = '{}-{}'.format(i, org_hash_values[i])
                pipe.lrem(org_secondary_key, 1, key)
                update_secondary_key = '{}-{}'.format(i, update_hash_values[i])
                pipe.lpush(update_secondary_key, key)
        self.m_r.set_str(key, self._obj_to_byte_array(hash_func))
        pipe.execute()

    def _search_secondary_index(self, hash_obj):
        keys = []
        for i, hash_value in enumerate(hash_obj.digest()):
            secondary_key = '{}-{}'.format(i, hash_value)
            candidate = self.s_r.lrange(secondary_key, 0, -1)
            keys.extend(candidate)

        return keys

    @staticmethod
    def _obj_to_byte_array(obj):
        byte_stream = BytesIO()
        try:
            pickler = pickle.Pickler(byte_stream)
            pickler.dump(obj)
            byte_stream.seek(0)
            byte_array = byte_stream.read()
            return byte_array

        finally:
            byte_stream.close()

    @staticmethod
    def _byte_array_to_obj(byte_stream):
        unpickler = pickle.Unpickler(byte_stream)
        return unpickler.load()
