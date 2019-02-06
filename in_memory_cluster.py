import io
import pickle

from datasketch import MinHash

from renappy import Renappy


class InMemoryCluster:
    def __init__(self, minhash_host='localhost:6379', secondary_index_host=None, minhash_db=1, secondary_index_db=2,
                 num_perm=100, load_data_per=10000):
        if not secondary_index_host:
            secondary_index_host = minhash_host

        # minhash redis host, minhash redis port
        mr_host, mr_port = minhash_host.split(":")

        # secondary index redis host, secondary index redis portdef load_minhash_objs(self, keys):
        byte_streams = [io.BytesIO(byte_obj) for byte_obj in self.m_r.mget_str(keys)]
        objs =[]

        for byte_stream in byte_streams:
            unpickler = pickle.Unpickler(byte_stream)
            objs.append(unpickler.load())

        return objs

    def search_secondary_index(self, hash_obj):
        keys = []
        for i, hash_value in enumerate(hash_obj.digest()):
            secondary_key = '{}-{}'.format(i, hash_value)

            l = self.s_r.lrange(secondary_key, 0, -1)
            keys.extend(l)

        return keys
        sr_host, sr_port = secondary_index_host.split(":")

        # minhash redis
        self.m_r = Renappy(host=mr_host, port=mr_port, db=minhash_db)
        # secondary index redis
        self.s_r = Renappy(host=sr_host, port=sr_port, db=secondary_index_db)
        self.num_perm = num_perm
        self.load_data_per = load_data_per

    def flush_all(self):
        self.m_r.flushdb()
        self.s_r.flushdb()

    def init_cluster(self, data):
        for key in data.keys():
            self._generate_minhash_and_save(key, data[key])
        keys = self.m_r.keys()
        self._generate_and_save_secondary_index(keys)

    def update_cluster(self, data):
        for key in data.keys():
            if self.m_r.exists(key):
                self._update_secondary_index(data, key)
            else:
                self._generate_minhash_and_save(key, data[key])
                self._generate_and_save_secondary_index([key])

    def load_minhash_objs(self, keys):
        byte_streams = [io.BytesIO(byte_obj) for byte_obj in self.m_r.mget_str(keys)]
        objs = []

        for byte_stream in byte_streams:
            unpickler = pickle.Unpickler(byte_stream)
            objs.append(unpickler.load())

        return objs

    def search_secondary_index(self, hash_obj):
        keys = []
        for i, hash_value in enumerate(hash_obj.digest()):
            secondary_key = '{}-{}'.format(i, hash_value)

            l = self.s_r.lrange(secondary_key, 0, -1)
            keys.extend(l)

        return keys

    def _update_secondary_index(self, data, key):
        byte_stream = io.BytesIO(self.m_r.get_str(key))
        unpickler = pickle.Unpickler(byte_stream)
        hash_func = unpickler.load()
        org_hash_values = hash_func.digest()
        for stream in data[key]:
            hash_func.update(stream.encode('utf-8'))
        update_hash_values = hash_func.digest()
        need_remove_secondary_index = []
        for i in range(len(org_hash_values)):
            if org_hash_values[i] != update_hash_values[i]:
                need_remove_secondary_index.append(i)
        pipe = self.s_r.pipeline()
        for i in need_remove_secondary_index:
            org_secondary_key = '{}-{}'.format(i, org_hash_values[i])
            pipe.lrem(org_secondary_key, 1, key)
            update_secondary_key = '{}-{}'.format(i, update_hash_values[i])
            pipe.lpush(update_secondary_key, key)
        self.m_r.set_str(key, self._obj_to_byte_array(hash_func))
        pipe.execute()

    def _generate_minhash_and_save(self, key, stream):
        hash_func = self._generate_minhash_func(key, stream)
        byte_array = self._obj_to_byte_array(hash_func)
        self.m_r.set_str(key, byte_array)

    def _load_minhash(self, data, per):
        data_len = len(data)
        num_iter = data_len // per
        for index in range(num_iter + 1):
            begin = index * per
            end = begin + per
            if end > data_len:
                batch_data = data[begin:]
            else:
                batch_data = data[begin:end]

            byte_objs = self.m_r.mget_str(batch_data)
            byte_streams = [io.BytesIO(byte_obj) for byte_obj in byte_objs]
            minhash_objs = []
            for key, byte_stream in zip(batch_data, byte_streams):
                unpickler = pickle.Unpickler(byte_stream)
                minhash_objs.append((key, unpickler.load()))
            yield minhash_objs
        yield None

    def _create_and_push_secondary_index(self, key, hash_obj):
        for i, hash_value in enumerate(hash_obj.digest()):
            secondary_key = '{}-{}'.format(i, hash_value)
            self.s_r.push_batch(secondary_key, key)

    def _generate_and_save_secondary_index(self, keys):
        batch_objs = self._load_minhash(keys, self.load_data_per)
        while True:
            batch = next(batch_objs)
            if not batch:
                break
            for key, hash_obj in batch:
                self._create_and_push_secondary_index(key, hash_obj)
        self.s_r.pipe_force_execute()

    def _generate_minhash_func(self, key, streams):
        exist_stream = None
        if self.m_r.exists(key):
            exist_stream = self.m_r.get_str(key)

        if exist_stream:
            hash_func = pickle.load(exist_stream)
        else:
            hash_func = MinHash(num_perm=self.num_perm)

        for stream in streams:
            hash_func.update(stream.encode('utf-8'))

        return hash_func

    @staticmethod
    def _obj_to_byte_array(obj):
        byte_stream = io.BytesIO()
        pickler = pickle.Pickler(byte_stream)

        pickler.dump(obj)
        byte_stream.seek(0)
        byte_array = byte_stream.read()
        return byte_array


