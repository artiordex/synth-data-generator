# 노트북 기능 반영

기준: `experiments/notebooks/합성데이터_수행_코드.ipynb`의 전체 10개 셀.
Colab의 설치 명령·고정 파일 경로·중복 실험 코드는 서비스 코드로 옮기지 않고,
동작을 다음 모듈에 통합했다. 화면·API·일괄 처리 기본 모델은 CTGAN이다.
업로드 프로필에 `notebook_preset`을 포함한다. 알려진 6개 컬럼 구성과 일치하면
학습 유형, 결측 보존, 평가 제외, epochs/batch_size/PAC를 자동 적용한다.
모르는 파일의 결측 의미는 추정하지 않는다. 추가 컬럼은 유지하고 사용자 명시 설정이 우선한다.
API에서 epochs/batch_size/PAC 생략 또는 null은 자동 설정, 컬럼 옵션의 빈 배열은 자동 선택 해제를 뜻한다.

| 노트북 기능 | 서비스 구현 |
| --- | --- |
| 엑셀 로드, 컬럼 지정, 범주/수치형 변환, 중앙값 보정 | profiling/analyzer.py, preprocessing/transformer.py |
| CTGAN 메타데이터, epochs, batch_size, PAC | generators/ml/ctgan.py |
| ‘비적용’ 의미의 NA·적용 플래그 | preserve_null_columns 또는 null_indicator 제약조건 |
| 적용인데 NA인 행 제거, 비적용인 값은 NA 강제 | preprocessing/transformer.py |
| 오버샘플·수리·보충 생성 | generators/sampling.py |
| 수치형 구간화·NA 버킷을 포함한 행 일치율 | quality/jsd.py, quality/assessment.py |
| 범주형 JSD, 수치형 히스토그램 + NA 버킷 JSD | quality/jsd.py; 화면 분포에도 NA 비율 표시 |
| sin/cos를 학습에 사용하고 평가에서 제외 | evaluation_excluded_columns |
| NumPy·PyTorch 시드, CPU 실행 | common/randomness.py; seed, enable_gpu 설정 |
| CSV·XLSX·평가 JSON 및 실험 설정 저장 | pipeline.py; 기존 HWPX 문서·ZIP도 유지 |

화면의 **학습·평가 상세 설정**에서 학습 유형, 결측 의미 보존, 평가 제외,
epochs·batch_size·PAC·seed·최소 생성 묶음·최대 시도 횟수·GPU 사용을 설정한다.
기본은 CPU이며 CTGAN 배치 크기는 짝수이면서 PAC의 배수가 되도록 조정하고
실제로 사용한 크기를 기록한다.

API 예시 (`POST /api/v1/synthesis/start`):

```json
{
  "file_name": "입력.csv",
  "model_type": "ctgan",
  "target_rows": 1000,
  "epochs": 50,
  "batch_size": 64,
  "pac": 1,
  "seed": 42,
  "enable_gpu": false,
  "sampling_batch_size": 800,
  "max_sampling_attempts": 10,
  "preserve_null_columns": ["소득분위"],
  "evaluation_excluded_columns": ["가입월_sin", "가입월_cos"]
}
```

열 이름은 입력 파일에 실제로 존재해야 한다. sin/cos 값은 노트북과 동일하게
입력 파일의 값을 사용한다. 자동으로 파생변수를 만들지는 않는다.
평가 제외는 평가에만 적용하며 학습·출력·전체 컬럼 명세는 유지한다.
결측 의미 보존을 선택하지 않은 수치형의 결측은 노트북 기본 흐름처럼 중앙값으로 보정한다.

각 생성 시도는 `max(최소 생성 묶음 크기, 아직 필요한 행 수)`행을 요청한다.
타입 정리 → 규칙 및 선택적 노이즈 → 제약조건 수리 → 조건 확인 → 원본 일치 정책
적용을 거쳐 목표 행 수까지 보충한다. 마지막 초과분만 잘라낸다.
최대 시도 후에도 부족하면 목표·확보 행 수가 포함된 오류로 종료한다.
`duplicate_policy=balanced`가 기본이다. 학습 컬럼 값의 조합이 학습 원본에 5회 이상
나타난 경우에는 생성된 같은 조합을 유지하고, 1~4회 나타난 희귀 조합 일치는 제거한다.
생성기가 낸 행만 사용하며 원본 행을 복사해 보충하지 않는다. 일치 행이 남으면 최종 판정은
검토 필요이며 JSON guardrails와 HWPX에 정책·일치 건수를 기록한다.
`strict`는 모든 원본 일치 행을 제거한다. 어떤 정책이든 희귀 조합만 가능한 데이터에서는
생성에 실패할 수 있다. 원본 일치 제거가 분포를 바꿀 수 있어 JSD·상관관계를 함께 확인한다.

50행 이상 입력은 시드 기반 무작위 20%를 학습 전에 독립 대조 데이터로 분리한다.
모델은 나머지 80%에만 학습하고, 대조 데이터의 중앙값 보정도 학습 데이터 기준으로 수행한다.
따라서 전체 원본으로 학습하던 노트북과 학습 행 수가 다르다. 분포 평가는 학습 데이터와 합성을 비교한다.
Anonymeter는 학습·합성·독립 대조 각각 최소 10행 및 2개 컬럼이 필요하다.
미실행·예외·신뢰 불가 경고는 null 위험도와 NOT_EVALUATED/ERROR 상태로 기록한다.
필수 측정이 누락되면 종합 점수는 null, 통과 여부는 false이며 UI/HWPX도 미측정·검토 필요로 표시한다.
보고서와 화면의 수치형 JSD는 동일한 20구간 및 결측 버킷으로 계산한다.
이 변경은 새 작업부터 적용되며 기존 산출물과 기존 판정은 다시 쓰지 않는다.

JSON의 `config`에는 학습/평가 컬럼, 제외 컬럼, 제약조건, 시드, 패키지 버전,
실제 배치 크기와 평가 방식을 저장한다. `sampling`에는 시도별 생성·제외·확보 행 수와
수리 방식을 기록한다. 원본 일치율은 실제 재식별 확률과 구분해서 해석한다.

시드가 서로 섞이지 않도록 동일 API 프로세스의 파이프라인 실행을 직렬화한다.
동일 환경의 CPU CTGAN 반복 학습 재현성을 테스트한다. GPU·장치·라이브러리 버전이
달라지는 경우 비트 단위로 동일한 결과까지 보장하지 않는다. SDV의 샘플링에는
라이브러리의 고정 난수 흐름을 사용하고, 사용자 시드는 학습 난수와 부가 처리에 적용한다.

검증: `uv run --locked --all-packages python -m pytest packages/synthetic_engine/tests/test_notebook_parity.py apps/api/tests/test_synthesis_options.py`

CTGAN 배치 규칙 및 GPU 옵션 기준: [SDV 공식 문서](https://docs.sdv.dev/sdv/single-table-data/modeling/synthesizers/ctgansynthesizer).
