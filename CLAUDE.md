# Wireline Census — Claude Code 작업 지침

ISSCC·VLSI·JSSC·CICC·ESSCIRC/ESSERC·A-SSCC·SSC-L·TCAS-I/II·TVLSI의 유선 송수신기 논문(DSP/ADC 기반 포함)을 모아 GitHub Pages(https://mixedcas-lab.github.io/wireline-census/)에 공개하는 저장소다. 자매 저장소 mixedcas-lab/adc-census의 수집기가 랩 서버에 받아 둔 IEEE 레코드 캐시(`~/adc-census/cache/raw`)를 읽기만 하며, **IEEE API를 직접 호출하지 않는다.** 랩 서버 cron이 `scripts/update.sh`로 매일 재분류하고 바뀐 것이 있을 때만 push한다.

## 반드시 지킬 것

- **초록 공개 금지**: 캐시의 초록은 분류·수치 추출에만 쓰고 `data/*.json`에 넣지 않는다. 캐시는 이 저장소에 복사하거나 커밋하지 않는다.
- **API 키 불필요**: 이 저장소는 키를 읽지 않는다. 수집 범위·주기·키는 adc-census가 관리한다.
- **공용 서버**: sudo, 시스템 패키지 설치, 다른 사용자의 crontab이나 파일 수정은 하지 않는다. 표준 라이브러리만 쓴다.
- **코드 수정**: `collector/`를 고치면 `collector/test_build.py`에 사례를 추가하고 `python3 -m unittest discover -s collector`가 통과해야 커밋한다. `data/papers.json`, `data/meta.json`은 직접 편집하지 않는다(빌더가 생성). `data/annotations.csv`는 사람이 검수한 값이며 덮어쓰지 않는다.
- **커밋**: main에 직접 커밋한다. 메시지는 `collector: ...`, `site: ...`, `data: ...`처럼 영역을 앞에 붙인다.

## 자주 쓰는 명령

```bash
python3 -m unittest discover -s collector   # 오프라인 테스트
python3 collector/build.py                  # 캐시에서 data/papers.json 재생성
python3 collector/build.py --report         # venue·연도별 건수, 수치 추출률, 무작위 표본, 놓친 후보
scripts/update.sh                           # 재생성 → 커밋 → push (cron이 매일 실행)
tail -50 logs/update.log                    # cron 실행 기록
```

## 갱신이 실패했을 때

1. `tail -80 logs/update.log`로 오류를 확인한다.
2. "cache directory not found" 또는 "no wireline papers found"면 adc-census 캐시 위치(`collector/venues.json`의 `cache`, `$WIRELINE_CENSUS_CACHE`)를 확인한다.
3. push 오류면 `git status`, `git pull --rebase`로 충돌을 푼다.
