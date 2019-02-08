
# Tiny Elephant(English)
In memory based collaborative filtering. Implementation of [this slide](https://www.slideshare.net/deview/261-52784785).
This is written by python.

## Requirements
- Redis
- python3
- [snappy](https://github.com/google/snappy)

### Install snappy 
#### OSX
```bash
brew install snappy
```
#### Ubuntu
```bash
apt install libsnappy-dev
```

# Install
```bash
pip install tiny-elephant
```

# Usage
Clone this project and run next way 
```python
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
    secondary_index_host='localhost:6379',
    minhash_db=1,
    secondary_index_db=2,
    seed=1
)

# Flush minhash & secondary index db on redis
# In example db 1 & 2
imc.flush_all()

# init_cluster method run next ways.
# 1. Generate minhash by data and save on redis(db 1).
# 2. Load minhash objects and generate secondary index.
# 3. put in each secondary index.(db 2)
imc.init_cluster(data)

users = data.keys()
for user in users:
    # Print similar top 10 of each user
    print(user, imc.most_common(user, count=10))

# You don't need care about duplicated!
update_data = {'user1': ['airplane', 'banana', 'cat'], 'user5': ['hobby', 'internet', 'jogging', 'banana', 'cat', 'dog']}

# You should use update_cluster method after init_cluster
# init_cluster is faster more than update_cluster
# So use init_cluster when put your first data.
imc.update_cluster(update_data)

print('======== UPDATED!! =========')

# You can check user 5 more similar than before.
for user in users:
    print(user, imc.most_common(user, count=10))

```
And this is result.
```
user1 [(b'user2', 60), (b'user11', 45), (b'user5', 16), (b'user8', 13), (b'user7', 12), (b'user4', 11), (b'user6', 8), (b'user10', 5), (b'user9', 5)]
user2 [(b'user1', 60), (b'user11', 36), (b'user6', 14), (b'user10', 12), (b'user7', 12), (b'user9', 9), (b'user8', 9)]
user3 [(b'user9', 75)]
user4 [(b'user8', 23), (b'user1', 11)]
user5 [(b'user11', 25), (b'user1', 16)]
user6 [(b'user10', 67), (b'user8', 17), (b'user2', 14), (b'user1', 8)]
user7 [(b'user8', 42), (b'user1', 12), (b'user2', 12)]
user8 [(b'user7', 42), (b'user10', 37), (b'user4', 23), (b'user6', 17), (b'user1', 13), (b'user2', 9)]
user9 [(b'user3', 75), (b'user2', 9), (b'user11', 7), (b'user1', 5)]
user10 [(b'user6', 67), (b'user8', 37), (b'user2', 12), (b'user1', 5)]
user11 [(b'user1', 45), (b'user2', 36), (b'user5', 25), (b'user9', 7)]
======== UPDATED!! =========
user1 [(b'user5', 93), (b'user2', 60), (b'user11', 45), (b'user8', 13), (b'user7', 12), (b'user4', 11), (b'user6', 8), (b'user10', 5), (b'user9', 5)]
user2 [(b'user1', 60), (b'user11', 36), (b'user5', 28), (b'user6', 14), (b'user10', 12), (b'user7', 12), (b'user9', 9), (b'user8', 9)]
user3 [(b'user9', 75)]
user4 [(b'user8', 23), (b'user5', 15), (b'user1', 11)]
user5 [(b'user1', 93), (b'user2', 28), (b'user8', 20), (b'user6', 15), (b'user7', 15), (b'user4', 15), (b'user11', 13), (b'user10', 10)]
user6 [(b'user10', 67), (b'user8', 17), (b'user5', 15), (b'user2', 14), (b'user1', 8)]
user7 [(b'user8', 42), (b'user5', 15), (b'user1', 12), (b'user2', 12)]
user8 [(b'user7', 42), (b'user10', 37), (b'user4', 23), (b'user5', 20), (b'user6', 17), (b'user1', 13), (b'user2', 9)]
user9 [(b'user3', 75), (b'user2', 9), (b'user11', 7), (b'user1', 5)]
user10 [(b'user6', 67), (b'user8', 37), (b'user2', 12), (b'user5', 10), (b'user1', 5)]
user11 [(b'user1', 45), (b'user2', 36), (b'user5', 13), (b'user9', 7)]
```

# TODO
- Improve performance
- Implement another language.

# Special Thanks
[@GulliverNam](https://github.com/GulliverNam)
