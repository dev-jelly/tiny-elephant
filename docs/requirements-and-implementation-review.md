# Tiny Elephant 당시 기준 구현 평가

검토일: 2026-06-26

대상:

- Repository: https://github.com/dev-jelly/tiny-elephant
- Checked commit: `0ca407013923ace3be101c2a18907501fa93941f`
- Checked commit date: 2019-02-10
- Reference slide: https://www.slideshare.net/slideshow/261-52784785/52784785

## 0. 평가 관점

이 문서의 핵심 질문은 "2026년 현재 이 코드를 바로 서비스에 쓸 수 있는가"가 아니다. 더 중요한 질문은 다음이다.

> 당시 기준으로, 슬라이드의 핵심 아이디어를 코드로 잘 구현했는가?

따라서 최신 Python/Redis 호환성 문제는 부차적으로만 다룬다. 평가는 다음 기준으로 한다.

- 슬라이드의 문제의식을 제대로 이해했는가.
- MinHash와 Secondary Index라는 핵심 구조를 실제 코드로 옮겼는가.
- README 예제 수준에서 아이디어가 재현되는가.
- 실시간 업데이트와 성능 최적화까지 어느 정도 완성했는가.
- 당시 오픈소스/학습용 프로토타입으로 보았을 때 구현 선택이 합리적인가.

## 1. 종합 평가

당시 기준으로 보면 Tiny Elephant는 슬라이드의 핵심 아이디어를 꽤 잘 구현한 편이다. 단순한 toy 코드가 아니라, MinHash signature를 만들고 Redis에 저장한 뒤, `signature position + hash value`를 Secondary Index key로 사용해 유사 후보를 찾는 전체 흐름이 실제로 동작한다.

특히 초기 적재 후 추천 결과는 README에 적힌 결과와 동일하게 재현되었다. 이 점은 중요하다. 슬라이드의 핵심 개념인 "원본 click stream 전체를 매번 비교하지 않고, MinHash signature overlap만으로 유사도를 근사한다"는 아이디어가 코드 수준에서 검증되었다는 뜻이다.

다만 "슬라이드의 최종 최적화 설계까지 잘 구현했는가"라고 물으면 답은 부분적이다. Secondary Index 저장 방식은 슬라이드에서 강조한 Redis String + `mget` + snappy 압축 방식이 아니라 Redis List 기반으로 단순화되어 있다. 또한 업데이트 경로에는 실행 오류가 있어, 슬라이드가 강조한 실시간 누적 업데이트까지 안정적으로 구현되었다고 보기는 어렵다.

따라서 결론은 다음과 같다.

- 개념 구현: 잘했다.
- 초기 추천 동작: 잘 구현되어 있다.
- 슬라이드의 자료구조 핵심: 상당 부분 반영되어 있다.
- 성능 최적화 구현: 일부 단순화되어 있다.
- 실시간 업데이트 완성도: 부족하다.
- 당시 학습용/프로토타입 오픈소스로서의 가치: 충분하다.

## 2. 슬라이드 핵심 요구사항

### 2.1 문제 정의

슬라이드는 memory-based collaborative filtering을 작은 메모리와 적은 계산량으로 처리하는 방법을 제안한다. 핵심 문제는 다음이다.

- 사용자 또는 아이템 간 유사도를 구하려면 원래는 많은 pairwise comparison이 필요하다.
- 원본 click stream은 길이가 제각각이고, 인기 item/user는 매우 긴 stream을 가진다.
- 매번 원본 stream을 읽어 비교하면 I/O와 계산량이 커진다.
- 따라서 원본 stream 대신 고정 길이의 작은 signature를 유지해야 한다.

### 2.2 알고리즘 요구사항

- Jaccard similarity를 유사도 기준으로 사용한다.
- MinHash를 이용해 Jaccard similarity를 근사한다.
- click stream 전체가 아니라 MinHash signature를 저장한다.
- signature 길이는 고정되어 있어야 한다.
- 두 대상의 유사도는 signature overlap count로 근사한다.

### 2.3 Secondary Index 요구사항

슬라이드는 모든 대상과 직접 비교하지 않기 위해 Secondary Index를 만든다.

- key: `signature_position-signature_value`
- value: 그 signature 위치/값을 가진 item/user membership
- 조회:
  - 대상의 signature를 읽는다.
  - signature별 Secondary Index key를 만든다.
  - membership을 가져와 후보 등장 횟수를 센다.
  - 등장 횟수가 곧 signature overlap count다.

### 2.4 실시간 업데이트 요구사항

슬라이드는 MinHash의 `min` 성질을 이용해 새 click을 누적 반영할 수 있다고 설명한다.

- 기존 signature를 읽는다.
- 새 click stream 조각만 MinHash에 반영한다.
- 바뀐 signature 위치만 Secondary Index에서 갱신한다.
- 전체 batch rebuild 없이 작은 업데이트를 계속 누적한다.

## 3. 구현이 잘 된 부분

### 3.1 MinHash 선택과 사용

`tiny_elephant/in_memory_cluster.py`는 `datasketch.MinHash`를 사용한다. 당시 기준으로 직접 MinHash를 구현하지 않고 검증된 라이브러리를 사용한 선택은 합리적이다.

구현은 각 stream token을 UTF-8 bytes로 변환해 MinHash에 update한다. 이 방식은 슬라이드의 "click stream을 MinHash signature로 축약한다"는 요구사항에 잘 맞는다.

평가:

- 좋음.
- 핵심 알고리즘을 직접 재발명하지 않고 라이브러리로 처리한 점도 적절하다.

### 3.2 고정 길이 signature 저장

MinHash object를 pickle로 직렬화하고 snappy로 압축해 Redis에 저장한다. 슬라이드가 말한 "원본 click stream 대신 짧은 대체본을 저장한다"는 아이디어가 구현되어 있다.

평가:

- 좋음.
- 당시 Python 프로토타입으로는 pickle + snappy + Redis 조합이 실용적인 선택이다.
- 다만 pickle은 장기 호환성과 보안 측면에서 서비스 경계가 넓어지면 조심해야 한다.

### 3.3 Secondary Index 구조

구현은 Secondary Index key를 다음 형태로 만든다.

```text
sip_____{position}-{hash_value}
```

그리고 해당 signature 위치/값을 가진 user key를 value에 넣는다. 이는 슬라이드의 `Sig위치-값 -> membership` 구조와 거의 같은 발상이다.

평가:

- 개념적으로 잘 옮겼다.
- 슬라이드를 이해하고 핵심 자료구조를 코드로 만들었다고 볼 수 있다.
- 이 레포에서 가장 중요한 구현 포인트다.

### 3.4 추천 조회 흐름

`most_common()`은 대상 user의 MinHash를 읽고, 해당 signature 값들로 Secondary Index를 조회한 뒤 `Counter`로 후보 등장 횟수를 센다.

이 구조는 슬라이드의 "Secondary Index lookup만으로 Jaccard를 계산할 수 있다"는 아이디어와 일치한다. 실제로 README 샘플 데이터에서 초기 추천 결과가 그대로 재현되었다.

평가:

- 좋음.
- 학습용 구현으로는 매우 명확하다.
- 반환값이 정규화된 Jaccard가 아니라 raw overlap count라는 점은 문서로 보완하면 된다.

### 3.5 초기 예제 재현성

Python 3.11 + `redis==2.10.6` 환경에서 다음 흐름은 성공했다.

- Redis flush
- 샘플 data 적재
- 각 user별 `most_common()` 조회

결과는 README의 초기 출력과 동일했다.

평가:

- 매우 중요하게 긍정 평가할 부분이다.
- 단순히 구조만 흉내 낸 것이 아니라, 실제 데이터에서 의도한 결과를 냈다.

## 4. 당시 기준 아쉬운 부분

### 4.1 Secondary Index 저장 방식은 슬라이드보다 단순하다

슬라이드는 Redis String + `mget` + snappy 압축을 중요한 최적화로 설명한다. 현재 구현은 Secondary Index membership을 Redis List로 저장한다.

- 생성: `LPUSH`
- 조회: signature 수만큼 `LRANGE`
- 삭제: `LREM`

이 선택은 이해하기 쉽고 구현도 단순하다. 하지만 슬라이드가 강조한 round-trip 감소와 압축 최적화까지 구현한 것은 아니다.

평가:

- 프로토타입으로는 합리적이다.
- 슬라이드의 최종 성능 설계 재현으로는 부족하다.
- "잘못 구현"이라기보다 "핵심 구조는 구현했고, 성능 최적화는 단순화했다"가 정확하다.

### 4.2 초기 bulk build API가 문서와 다르다

README에는 `init_cluster()`가 있고 `update_cluster()`보다 빠른 초기 적재용 API라고 설명되어 있다. 하지만 현재 코드에는 `init_cluster()`가 없다. 초기 적재도 `update_cluster()`를 사용해야 한다.

평가:

- 당시 구현 완성도 관점에서 아쉬운 부분이다.
- 대량 초기 적재를 고려하면 별도 bulk build 경로가 있는 편이 더 좋다.
- README와 코드가 어긋나 있어 사용자가 혼란을 겪을 수 있다.

### 4.3 실시간 업데이트 구현은 미완성에 가깝다

코드에는 기존 MinHash를 읽고 새 stream을 누적 적용한 뒤, 바뀐 signature 위치만 Secondary Index에서 제거/추가하려는 구조가 있다. 방향 자체는 슬라이드와 맞다.

하지만 검증 중 `update_cluster(update_data)`에서 Redis `LREM` 인자 순서 문제로 오류가 발생했다.

```text
redis.exceptions.ResponseError: Command # 1 (LREM sip_____1-1822378879 user5 1) of pipeline caused error: value is not an integer or out of range
```

평가:

- 설계 의도는 좋다.
- 하지만 슬라이드의 중요한 주장인 "실시간으로 조금씩 업데이트한다"를 완성했다고 보기는 어렵다.
- 당시 기준으로도 이 부분은 테스트가 필요했을 가능성이 높다.

### 4.4 Redis round-trip 최적화가 약하다

조회 시 signature 개수만큼 `LRANGE`를 순차 호출한다. 기본 `num_perm=128`이면 조회마다 최대 128번의 Redis list read가 발생한다.

슬라이드의 최종안은 Redis String membership을 `mget`으로 한 번에 가져오는 쪽에 가깝다.

평가:

- 작은 샘플에서는 문제 없다.
- 슬라이드의 "머신 한 대에서 대량 추천" 목표까지 생각하면 아쉽다.
- 구조 설명용 구현이라면 괜찮지만, 성능 데모용 구현으로는 부족하다.

## 5. 작성자가 당시 덜 이해했거나 놓친 것으로 보이는 부분

아래 내용은 작성자의 실제 의도를 단정하는 것이 아니라, 코드와 README, 커밋 이력, 실행 결과에서 드러나는 근거를 바탕으로 한 추정이다. 중요한 전제는 작성자가 MinHash와 Secondary Index의 핵심 아이디어는 이해했다는 점이다. 부족해 보이는 부분은 알고리즘의 큰 그림보다는 구현 완성도, Redis 사용 방식, API/문서 관리 쪽에 가깝다.

### 5.1 Redis 자료구조 선택의 성능 의미를 끝까지 반영하지 못했다

작성자는 Secondary Index가 필요하다는 점은 이해했다. `position-value -> members` 구조를 구현했기 때문이다.

하지만 슬라이드에서 Redis String을 선택한 이유는 단순 저장 편의가 아니라 다음 최적화 때문이다.

- 여러 Secondary Index key를 `mget`으로 한 번에 읽는다.
- membership payload를 snappy로 압축한다.
- Redis round-trip 수를 줄인다.
- Set/List의 per-key operation 비용을 피한다.

현재 구현은 Redis List + `LRANGE` 반복 호출이다. 이는 자료구조의 모양은 맞지만, 슬라이드가 왜 Redis String을 강조했는지까지는 충분히 반영하지 못한 선택으로 보인다.

평가:

- 알고리즘 구조는 이해했다.
- Redis 자료구조 선택이 성능에 미치는 영향은 덜 이해했거나, 프로토타입 단순성을 우선한 것으로 보인다.

### 5.2 조회 성능의 병목이 network round-trip이라는 점을 충분히 반영하지 못했다

`most_common()`은 대상 signature의 각 위치마다 Secondary Index를 조회한다. 기본 `num_perm=128`이면 한 번의 추천 조회에 최대 128번의 `LRANGE`가 발생한다.

슬라이드의 핵심 최적화 중 하나는 이 조회들을 `mget`으로 묶어 round-trip을 줄이는 것이다. 현재 구현은 이 부분을 코드로 옮기지 못했다.

평가:

- "signature가 겹치는 후보를 세면 된다"는 계산 원리는 이해했다.
- "Redis 호출 횟수 자체가 latency 병목이 된다"는 시스템 관점은 부족했던 것으로 보인다.

### 5.3 실시간 업데이트 경로를 충분히 검증하지 못했다

코드에는 기존 MinHash를 읽고 새 stream을 누적 적용한 뒤 바뀐 signature 위치만 Secondary Index에서 갱신하려는 구조가 있다. 이는 슬라이드의 실시간 업데이트 아이디어와 맞다.

하지만 실제 실행에서는 `LREM` 호출에서 오류가 발생한다.

```text
LREM sip_____1-1822378879 user5 1
```

Redis 명령은 `LREM key count element` 형태인데, 사용된 redis-py 버전에서는 `lrem(name, value, num=0)` 형태로 호출해야 했다. 즉 코드가 Redis 명령의 인자 순서와 Python client API의 인자 순서를 혼동했다.

평가:

- 업데이트 알고리즘의 방향은 이해했다.
- Redis client API 세부 계약은 정확히 확인하지 못했다.
- 특히 업데이트 경로에 자동화된 테스트가 없어서 오류가 남은 것으로 보인다.

### 5.4 초기 적재와 온라인 업데이트의 성능 차이를 충분히 분리하지 못했다

초기 README에는 `init_cluster()`와 `update_cluster()`가 구분되어 있었다. `init_cluster()`는 초기 bulk build, `update_cluster()`는 이후 incremental update라는 역할이었다.

하지만 `709af75` 커밋에서 `init_cluster()`가 제거되었고, 현재는 신규 key 적재도 `update_cluster()`가 처리한다. 이 변경 자체는 단순화를 위한 선택일 수 있다. 문제는 README가 이 변경을 따라가지 않았고, bulk build와 online update의 성능 차이도 코드에서 약해졌다는 점이다.

평가:

- API를 단순화하려는 의도는 보인다.
- 하지만 추천 시스템에서 초기 대량 적재와 실시간 증분 업데이트가 다른 최적화 문제라는 점은 충분히 보존하지 못했다.

### 5.5 공개 API와 문서 동기화의 중요성을 놓쳤다

현재 README는 다음 API를 안내한다.

- `secondary_index_host`
- `minhash_db`
- `secondary_index_db`
- `flush_all()`
- `init_cluster()`

하지만 현재 코드에는 없다. 이는 `Remove a redis client & init_cluster` 커밋 이후 README가 갱신되지 않았기 때문으로 보인다.

평가:

- 내부 구현을 바꾸는 데 집중했고, 사용자-facing API 문서까지 함께 바꾸는 관리가 부족했다.
- 당시 오픈소스 패키지로 배포했다는 점을 감안하면 아쉬운 부분이다.

### 5.6 반환 score의 의미를 API로 명확히 정의하지 못했다

`most_common()`은 `(user, count)` 형태를 반환한다. 이 count는 Jaccard similarity 자체가 아니라 signature overlap count다. 기본 `num_perm=128`이면 `count / 128`이 근사 similarity로 해석된다.

README 출력만 보면 `60`, `45`, `16` 같은 숫자가 무엇을 뜻하는지 명확하지 않다.

평가:

- ranking에는 문제가 없다.
- 하지만 API 사용자에게 "이 값은 raw overlap count이고, 정규화하려면 signature 길이로 나눠야 한다"는 설명이 필요했다.
- 유사도 개념과 반환값 semantics를 분리해서 문서화하는 이해가 부족했던 것으로 보인다.

### 5.7 테스트를 실행 스크립트 수준에 머물게 했다

`tiny_elephant/in_memory_cluster_test.py`는 pytest/unittest 테스트라기보다 예제 실행 스크립트다. assertion이 없고, 업데이트 결과가 기대값과 맞는지 자동 검증하지 않는다.

그 결과 초기 추천 출력은 사람이 보면 확인할 수 있지만, 업데이트 경로의 오류는 자동으로 잡히지 않는다.

평가:

- 예제를 통해 동작을 보여주려는 의도는 좋다.
- 하지만 추천 엔진의 핵심 경로인 초기 적재, 조회, 업데이트에 대해 회귀 테스트를 작성하는 습관은 부족했던 것으로 보인다.

### 5.8 패키징과 의존성 고정에 대한 이해가 약했다

`requirements.txt`는 버전을 고정하지 않는다. `setup.py`에는 `python_require`라는 오타가 있고, repository URL도 현재 레포와 다르다.

이 문제는 2026년 기준으로 더 크게 보이는 면이 있다. 하지만 PyPI 배포까지 한 패키지라면 당시 기준으로도 최소한 호환 가능한 dependency range와 package metadata는 더 정확히 관리하는 편이 좋았다.

평가:

- 알고리즘 프로토타입 작성 능력은 충분했다.
- 배포 가능한 Python 패키지로 유지하는 데 필요한 packaging discipline은 부족했던 것으로 보인다.

### 5.9 요약: 부족했던 것은 알고리즘보다 시스템 구현 디테일이다

작성자가 몰랐거나 덜 이해했던 것으로 보이는 핵심은 MinHash 자체가 아니다. 오히려 MinHash와 Secondary Index라는 큰 구조는 잘 이해했다.

부족했던 지점은 다음에 가깝다.

- Redis 자료구조 선택이 실제 latency와 memory에 미치는 영향
- Redis 명령과 redis-py API의 차이
- bulk build와 online update의 성능 특성 차이
- API 변경 시 README와 사용자 예제를 함께 바꾸는 관리
- 반환값의 의미를 명확히 정의하는 API 설계
- 자동화된 테스트와 dependency pinning

즉, 이 코드는 "알고리즘 아이디어를 이해하지 못한 코드"가 아니라 "알고리즘 아이디어는 이해했지만, 시스템/운영/패키징 디테일이 미완성인 코드"에 가깝다.

## 6. 당시 기준 판정표

| 항목 | 평가 | 이유 |
| --- | --- | --- |
| 슬라이드 문제의식 이해 | 좋음 | 원본 click stream 비교 비용을 MinHash signature 비교로 줄이는 방향을 잡았다. |
| MinHash 구현 | 좋음 | `datasketch.MinHash`를 사용해 안정적으로 구현했다. |
| signature 저장 | 좋음 | Redis + snappy 압축으로 작은 대체본을 저장한다. |
| Secondary Index 개념 구현 | 좋음 | `position-value -> members` 구조를 실제 코드로 만들었다. |
| 추천 조회 결과 | 좋음 | README 초기 예제 결과가 재현된다. |
| 실시간 업데이트 | 부족 | 구조는 있으나 업데이트 실행 오류가 있다. |
| 성능 최적화 충실도 | 보통 | List 기반이라 슬라이드의 String + `mget` 최적화와 다르다. |
| 문서/API 일치성 | 부족 | README의 `init_cluster()`, `flush_all()` 등이 현재 코드와 맞지 않는다. |
| 당시 프로토타입 가치 | 높음 | 핵심 아이디어를 이해하고 실험하기에는 충분히 의미 있다. |
| 시스템 구현 디테일 | 부족 | Redis 호출 최적화, client API, 테스트, 문서 동기화에서 빈틈이 있다. |

## 7. 최종 평가

Tiny Elephant는 당시 기준으로 "잘 구현된 편"이라고 평가할 수 있다. 이유는 명확하다.

1. 슬라이드의 핵심인 MinHash 기반 Jaccard 근사를 실제 코드로 구현했다.
2. Secondary Index를 만들어 signature overlap count로 유사 후보를 찾는 구조를 구현했다.
3. README 샘플의 초기 추천 결과가 실제로 재현된다.
4. 코드가 짧고 구조가 직접적이라 아이디어 학습용으로 좋다.

다만 "슬라이드의 최종 성능 최적화와 실시간 업데이트까지 완성도 있게 구현했는가"라고 평가하면 그렇지는 않다.

1. Secondary Index가 Redis String + `mget` 방식이 아니라 Redis List 방식으로 단순화되어 있다.
2. 업데이트 경로가 실제 실행에서 실패한다.
3. README와 현재 API가 맞지 않는다.
4. 대량 데이터 성능을 검증할 테스트나 벤치마크가 없다.

따라서 가장 공정한 평가는 다음과 같다.

> Tiny Elephant는 슬라이드의 핵심 알고리즘 아이디어를 이해하고 재현한 좋은 프로토타입이다. 초기 추천 기능은 잘 구현되어 있다. 다만 실시간 업데이트와 Redis 최적화까지 포함한 완성형 추천 엔진 구현으로 보기는 어렵다.

## 8. 현재 관점에서의 참고 개선점

아래 내용은 당시 구현 평가와 별개로, 지금 다시 살리거나 유지보수할 때 필요한 작업이다.

- README와 실제 API를 맞춘다.
- `init_cluster()`를 복원하거나 README에서 제거한다.
- `update_cluster()`의 `LREM` 오류를 수정하고 테스트를 추가한다.
- Secondary Index를 슬라이드에 맞춰 Redis String + compressed membership + `mget` 방식으로 바꿀지 결정한다.
- 최신 redis-py와 Python 버전에 맞게 `Renappy`를 수정한다.
- integration test와 간단한 benchmark를 추가한다.
