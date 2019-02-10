from tiny_elephant.in_memory_cluster import InMemoryCluster

# Data structure is dictionary
data = {
    "user1": ['airplane', 'banana', 'cat', 'dog', 'elephant', 'fruit', 'google', 'hobby', 'internet', 'jogging'],
    "user2": ['cat', 'dog', 'elephant', 'fruit', 'google', 'jogging', 'kotlin'],
    "user3": ['java', 'rx', 'yahoo', 'zoo'],
    "user4": ['apple', 'banana'],
    "user5": ['airplane'],
    "user6": ['bobby', 'dog'],
    "user7": ['train', 'cat', 'exercise', 'healthy'],
    "user8": ['healthy', 'dog', 'exercise', 'banana', 'youtube'],
    "user9": ['java', 'javascript', 'rx', 'zoo', 'yahoo', 'google', 'github'],
    "user10": ['cook', 'bobby', 'dog', 'youtube'],
    "user11": ['dance', 'airplane', 'trip', 'elephant', 'fruit', 'google']
}

# Initialize instance
imc = InMemoryCluster(
    minhash_host='localhost:6379',
    seed=1
)

# Flush minhash & secondary index db on redis
# In example db 1 & 2
imc.flush()

# update_cluster method run next ways.
# 1. Generate minhash by data and save on redis(db 1).
# 2. Load minhash objects and generate secondary index.
# 3. put in each secondary index.(db 2)
imc.update_cluster(data)

# Load minhash objects. These are instance of datasketch's MinHash object.
users = data.keys()
for user in users:
    print(user, imc.most_common(user, count=10))

# You don't need care about duplicated!
update_data = {'user1': ['airplane', 'banana', 'cat'], 'user5': ['hobby', 'internet', 'jogging', 'banana', 'cat', 'dog']}

# You should use update_cluster method after init_cluster
imc.update_cluster(update_data)

print('======== UPDATED!! =========')

# You can check user 5 more similer than before.
for user in users:
    print(user, imc.most_common(user, count=10))
