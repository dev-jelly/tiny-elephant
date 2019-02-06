from collections import Counter
from in_memory_cluster import InMemoryCluster


i = InMemoryCluster()
i.flush_all()
d = {
    "key1": ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'],
    "key2": ['c', 'd', 'e', 'f', 'g', 'j', 'k'],
    "key3": ['j', 'x', 'y', 'z'],
    "key4": ['a', 'b'],
    "key5": ['a']
}

i.init_cluster(d)
objs = i.load_minhash_objs(['key1', 'key2', 'key3', 'key4', 'key5'])
for obj in objs:
    ssi = i.search_secondary_index(obj)
    print(Counter(ssi).most_common(10))
    print(ssi)

update_data = {'key1': ['h', 'i', 'j'], 'key5': ['h', 'i', 'j', 'b', 'c']}

i.update_cluster(update_data)

print('==========================')

objs = i.load_minhash_objs(['key1', 'key2', 'key3', 'key4', 'key5'])
for obj in objs:
    ssi = i.search_secondary_index(obj)
    print(Counter(ssi).most_common(10))
    print(ssi)

