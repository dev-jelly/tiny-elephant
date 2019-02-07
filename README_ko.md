# Tiny Elephant(한국어)
메모리 기반의 collaborative filtering. 하용호님의 [이 슬라이드](https://www.slideshare.net/deview/261-52784785)를 참고하여 구현하였습니다.
본 구현은 파이썬으로 구현되어 있습니다.

## 준비물
- Redis
- python3
- [snappy](https://github.com/google/snappy)
### Snappy 설치 
#### OSX
```bash
brew install snappy
```
#### Ubuntu
```bash
apt install libsnappy-dev
```

# 설치
```bash
pip install tiny-elephant
```
# 사용법
프로젝트를 클론하시고 다음 코드를 실행해보세요.
```python
from collections import Counter
from in_memory_cluster import InMemoryCluster

# 데이터는 다음과 같이 딕셔너리로 구성해줍니다.
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

# 인스턴스 초기화
imc = InMemoryCluster(
    minhash_host='localhost:6379',
    secondary_index_host='localhost:6379',
    minhash_db=1,
    secondary_index_db=2,
    seed=1
)

# MinHash DB와 Secondary Index DB를 날립니다.
# 예제에서는 각각 1번 DB와 2번 DB를 사용합니다.
imc.flush_all()

# init_cluster 메소드는 다음과 같이 동작합니다.
# 1. 데이터를 넘겨 받아 Minhash 를 생성하고 저장합니다. (db 1).
# 2. MinHash를 불러와 Secondary Index를 생성합니다.
# 3. 각각의 Secondary Index에 키를 넣어줐니다.(db 2)
imc.init_cluster(data)

users = data.keys()
for user in users:
    # 비슷한 유저 10명을 뽑습니다.
    print(user, imc.most_common(user, count=10))

# 중복에 대한 걱정은 하실 필요가 없어요.
update_data = {'user1': ['airplane', 'banana', 'cat'], 'user5': ['hobby', 'internet', 'jogging', 'banana', 'cat', 'dog']}

# init_cluster 이후에는 update_cluster를 사용해 주셔야 합니다.
# init_cluster 는 update_cluster 보다 빠릅니다.
# 그러니 처음 데이터를 집어넣으실 때는 init_cluster를 사용해주세요.
imc.update_cluster(update_data)

print('======== UPDATED!! =========')

# user5는 전보다 더 비슷해 졌다는 걸 확인하실 수 있어요.
for user in users:
    print(user, imc.most_common(user, count=10))
```
그리고 결과는 다음과 같습니다.
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
- pypi에 올리기
- 성능향상
- 다른언어로 구현하기

# Special Thanks
[@GulliverNam](https://github.com/GulliverNam)
