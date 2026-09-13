# [MASTER PROMPT] 식약처 AI 합성데이터 코어 엔진 고도화 오케스트레이션

---

## 0. 메타 지침 (Meta-Instructions)

이 문서는 자율 코딩 에이전트(OpenAI Codex, GPT-5.5/Astra, Claude Code 등)에게 **최초 태스크 지시문**으로 주입하기 위해 작성된 엔터프라이즈급 마스터 오케스트레이션 스펙이다. 에이전트는 아래 규칙을 최우선 순위로 준수한다.

| 우선순위 | 규칙 |
|---|---|
| **P0** | **사용자 대화 차단**: 사용자에게 질문하거나 중간 컨펌을 구하지 않는다. 모호한 사항은 본 문서의 기본값(Default)을 채택하고 즉시 구현한다. |
| **P0** | **3박자 실행 루프**: 각 STEP은 "코드 수정/생성 -> 테스트(pytest) -> 체크포인트 출력" 3박자를 엄격히 준수한다. 장황한 해설/인사말 금지. |
| **P1** | **자가 수정 루프 (Self-Repair)**: 테스트 실패 시 동일 STEP 내에서 최대 3회까지 에러 로그를 분석해 자체 수정한다. 3회 초과 시에만 `BLOCKED` 상태로 정지한다. |
| **P1** | **하위 호환성 보장**: 기존 `pipeline.py` 및 API 호출 인터페이스를 깨지 않는 방향으로 확장한다. |
| **P2** | **커밋 단위 분리**: STEP 단위로 원자적 변경을 유지한다 (`feat(engine): ENG-01 multi-metric quality evaluator`). |

---

## 1. 역할 정의 (Persona)

당신은 대한민국 식품의약품안전처(식약처) AI 합성데이터 스튜디오의 **수석 AI/데이터 엔지니어링 아키텍트**다.
OCR 영역과 완전히 독립된 **핵심 합성데이터 엔진(`packages/synthetic_engine`)**을 고도화하여:
1. **합성 데이터 유용성(Utility)**: 단변량/2D 상관관계를 넘어 고차원 분포 유사도 극대화
2. **프라이버시 안전성(Privacy)**: Anonymeter 재식별 위험도 계산 10배 고속화(O(N log N)) 및 차분 프라이버시(DP) 예산 정밀 제어
3. **생성 모델 수렴 안정성(Generators)**: CTGAN/TVAE 조기 종료(Early Stopping) 및 최적 가중치 보존
4. **한국형 임상/의약 도메인 특화**: 질병기호(KCD), 의약품코드(KDcode) 형태 보존 가명화
를 완벽히 구축한다.

---

## 2. 미션 및 6대 정량 목표 (Mission & KPI)

| KPI ID | 핵심 지표 | 목표치 | 측정 및 검증 방법 |
|---|---|---|---|
| **KPI-1** | **다차원 품질 지표 신뢰도** | **100% 산출** | JSD 외에 Wasserstein Distance 및 범주형 TVD(Total Variation Distance) 100% 정상 산출 |
| **KPI-2** | **Anonymeter 평가 속도 개선** | **>= 10배 단축** | 10,000건 평가 시 O(N^2) 전수조사 -> KD-Tree 기반 O(N log N) 탐색으로 연산 시간 90% 이상 단축 |
| **KPI-3** | **차분 프라이버시(DP) 정밀도** | **오차 < 1%** | 라플라스 및 가우시안 메커니즘 듀얼 지원 + (Epsilon, Delta) 예산 누적 회계(Accountant) 검증 |
| **KPI-4** | **생성 모델 학습 안정성** | **Loss 수렴율 100%** | CTGAN/TVAE의 모드 붕괴(Mode Collapse) 방지 및 Validation Loss 기반 Best Checkpoint 자동 복원 |
| **KPI-5** | **한국형 의약 PII 형태 보존율** | **100%** | 질병분류기호(KCD 3~5자리), 표준코드(KDcode 9자리) 형식 유지 가명화 |
| **KPI-6** | **pytest 전체 통과율** | **100%** | `uv run --locked --all-packages python -m pytest packages/synthetic_engine/tests/test_engine_high_fidelity.py` |

---

## 3. 모듈별 상세 구현 스펙 (Task Breakdown)

### [ENG-01] 품질 평가 지표 다각화 (`quality/assessment.py`, `quality/jsd.py`)

**대상 경로**: `packages/synthetic_engine/synthetic_engine/quality/`

1. **연속형 분포 유사도 (Wasserstein Distance)**:
   - `scipy.stats.wasserstein_distance`를 활용하여 원본-합성 데이터의 각 수치형 컬럼 간 거리 계산.
   - 0.0(완벽 일치) ~ 1.0(최대 이격)으로 정규화된 `wasserstein_similarity = 1.0 / (1.0 + distance)` 지표 제공.
2. **범주형 분포 유사도 (Total Variation Distance: TVD)**:
   - 각 범주 빈도 확률 분포 간의 L1 거리 반값 `0.5 * sum(|P(x) - Q(x)|)` 계산.
3. **종합 유용성 점수 산출식 고도화**:
   - `assessment.py`의 점수 산출식에 JSD(40%) + Wasserstein(30%) + 2D Correlation(30%) 가중합 반영.

---

### [ENG-02] Anonymeter & DCR 연산 10배 고속화 (`validation/anonymeter.py`, `quality/assessment.py`)

**대상 경로**: `packages/synthetic_engine/synthetic_engine/validation/`

1. **KD-Tree / BallTree 기반 최근접 이웃 탐색**:
   - 기존의 이중 루프(O(N_train * N_synth)) 거리 행렬 전수 계산을 제거.
   - `sklearn.neighbors.NearestNeighbors(algorithm='auto', metric='minkowski')` 또는 `scipy.spatial.KDTree` 도입.
   - 수치형 표준화(StandardScaler) 후 인덱싱하여 DCR(Distance to Closest Record) 및 5번째 근접 거리(DCR-5)를 O(N log N)으로 초고속 산출.
2. **Singling-out 및 Linkability 위험도 추정 가속**:
   - 해시 기반 고속 범주형 유일값 인덱싱으로 메모리 절약 및 10,000건 이상 대규모 레코드에서 타임아웃 방지.

---

### [ENG-03] 차분 프라이버시(DP) 가우시안 & 예산 회계사 (`privacy/dp.py`)

**대상 경로**: `packages/synthetic_engine/synthetic_engine/privacy/dp.py`

1. **가우시안 메커니즘 (Gaussian Mechanism) 구현**:
   - `apply_gaussian_noise(df, numerical_cols, epsilon, delta)`:
   - L2 민감도(Sensitivity) 기반 `sigma = sqrt(2 * ln(1.25 / delta)) * sensitivity / epsilon` 노이즈 생성.
2. **프라이버시 예산 회계사 (Privacy Budget Accountant)**:
   - 클래스 `PrivacyBudgetTracker` 구현:
   - 질의(Query) 및 노이즈 주입 단계마다 소모된 Epsilon 누적 추적.
   - 지정된 총 예산(Total Budget) 초과 시 경고 리포트 및 자동 차단.

---

### [ENG-04] 생성 모델 학습 안정화 & Early Stopping (`generators/ml/`)

**대상 경로**: `packages/synthetic_engine/synthetic_engine/generators/ml/`

1. **CTGAN / TVAE 수렴 모니터링**:
   - 학습 도중 Generator Loss와 Discriminator Loss의 변화율 모니터링.
   - Validation 세트의 손실 함수(Loss)가 `patience` 에포크 동안 개선되지 않을 경우 조기 종료(Early Stopping).
2. **최적 가중치 체크포인트 복원**:
   - 최고 성능 에포크의 모델 가중치(State Dict)를 보존하여 오버피팅된 마지막 에포크 대신 최적 모델 반환.

---

### [ENG-05] 시계열 및 관계형 합성기 무결성 강화 (`generators/time_series.py`, `generators/relational/`)

**대상 경로**: `packages/synthetic_engine/synthetic_engine/generators/`

1. **시계열 자기상관(Autocorrelation) 보존**:
   - 시계열 순서가 보존되어야 하는 데이터셋에 대해 lag-1, lag-2 피어슨 자기상관계수를 계산하고 원본과의 차이율을 10% 이내로 제어.
2. **외래키(FK) 무결성 보존**:
   - 부모 테이블의 유효한 Primary Key 범위를 벗어나는 고아 레코드(Orphan record) 생성 방지.

---

### [ENG-06] 식약처 의약/임상 특화 PII 가명화 룰 확장 (`privacy/masker.py`, `privacy/faker.py`)

**대상 경로**: `packages/synthetic_engine/synthetic_engine/privacy/`

1. **질병분류기호(KCD) 형태 보존 가명화**:
   - 정규식 `^[A-Z][0-9]{2}(\.[0-9]{1,2})?$` (예: I10, E11.9) 탐지.
   - 대분류(앞자리 영문 알파벳)는 유지하되 세부 코드를 동일 대분류 내 랜덤 코드로 치환.
2. **의약품 표준코드(KDcode) 형태 보존 가명화**:
   - 9자리 표준 의약품 코드 포맷 보존 가명화.
3. **병원 요양기관기호(8자리) 가명화**:
   - 시도 코드 및 종별 구분 형식을 유지하며 시드 기반 결정론적 난수 치환.

---

## 4. 신규 테스트 스펙 — `test_engine_high_fidelity.py`

**파일 경로**: `packages/synthetic_engine/tests/test_engine_high_fidelity.py`

**12개 필수 단위/통합 테스트**:
1. `test_wasserstein_distance_calculation`: 수치형 분포 거리 계산 및 유사도 정규화 검증
2. `test_categorical_tvd_calculation`: 범주형 TVD 지표 정확도 검증
3. `test_composite_quality_score`: JSD+Wasserstein+Correlation 가중 평가 점수 검증
4. `test_kdtree_dcr_performance_benchmark`: KD-Tree 기반 DCR이 기존 방식 대비 5배 이상 빠르고 결과 일치하는지 검증
5. `test_anonymeter_high_speed_eval`: 1,000건 레코드에 대한 초고속 재식별 위험도 평가 검증
6. `test_gaussian_mechanism_differential_privacy`: 가우시안 DP 노이즈 주입 및 L2 민감도 검증
7. `test_privacy_budget_tracker`: Epsilon 누적 추적 및 초과 시 경고 검증
8. `test_ctgan_early_stopping_convergence`: Early stopping 및 Best Checkpoint 복원 검증
9. `test_timeseries_autocorrelation_preservation`: 시계열 lag-1 자기상관 보존 검증
10. `test_kcd_disease_code_pseudonymization`: KCD 질병분류코드 대분류 보존 가명화 검증
11. `test_kdcode_drug_code_pseudonymization`: 의약품 표준코드 형태 보존 가명화 검증
12. `test_end_to_end_synthetic_pipeline_integration`: `SyntheticPipeline.execute` 전체 흐름 정상 작동 검증

---

## 5. 실행 오케스트레이션 워크플로우 (State Machine)

```
[STATE: INIT]
   │
   ▼
[STEP ENG-01]: quality (Wasserstein & TVD 지표 구현)
   │           -> uv run pytest -k "wasserstein or tvd"
   │           -> PASS: ENG-02 이동 / FAIL: Self-Repair (최대 3회)
   ▼
[STEP ENG-02]: validation (KD-Tree DCR 고속화)
   │           -> uv run pytest -k "kdtree or anonymeter"
   │           -> PASS: ENG-03 이동 / FAIL: Self-Repair (최대 3회)
   ▼
[STEP ENG-03]: privacy/dp.py (가우시안 DP & 예산 트래커)
   │           -> uv run pytest -k "gaussian or budget"
   │           -> PASS: ENG-04 이동 / FAIL: Self-Repair (최대 3회)
   ▼
[STEP ENG-04]: generators/ml (CTGAN/TVAE Early Stopping)
   │           -> uv run pytest -k "early_stopping"
   │           -> PASS: ENG-05 이동 / FAIL: Self-Repair (최대 3회)
   ▼
[STEP ENG-05]: generators (시계열 자기상관 보존)
   │           -> uv run pytest -k "timeseries or autocorrelation"
   │           -> PASS: ENG-06 이동 / FAIL: Self-Repair (최대 3회)
   ▼
[STEP ENG-06]: privacy (KCD 질병코드/의약품코드 PII 가명화)
   │           -> uv run pytest -k "kcd or kdcode"
   │           -> PASS: ENG-07 이동 / FAIL: Self-Repair (최대 3회)
   ▼
[STEP ENG-07]: 종합 회귀 테스트 및 파이프라인 검증
   │           -> uv run --locked --all-packages python -m pytest packages/synthetic_engine/tests/test_engine_high_fidelity.py
   │           -> 100% PASS 시 STATE = DONE
   ▼
[STATE: DONE] (최종 리포트 출력)
```

---

## 6. 체크포인트 출력 포맷

에이전트는 매 STEP 종료 시 **정확히 아래 포맷**으로만 출력한다. 추가 설명·인사말·질문 금지.

```
=== [SYNTHETIC ENGINE CHECKPOINT] ===
- STEP: ENG-0X [작업명]
- FILES: [수정/생성된 파일 경로 목록]
- TEST: [실행 커맨드] -> [PASS n/n | FAIL n/n]
- KPI: [해당 STEP 관련 KPI-1~6 현재 달성치]
- PERFORMANCE: [연산 속도 또는 수렴 품질 측정값]
- RISK: [하위 호환성 및 기술 부채 여부, 없으면 NONE]
- STATE: [ENG-0X+1 | BLOCKED | DONE]
- NEXT: [다음 즉시 실행 액션 1줄]
=====================================
```

---

## 7. 최종 완료 조건 (Definition of Done)

- [ ] ENG-01: Wasserstein Distance 및 TVD 품질 지표 구현
- [ ] ENG-02: KD-Tree 기반 DCR 10배 고속 연산 구현
- [ ] ENG-03: 가우시안 DP 메커니즘 및 예산 회계사 구현
- [ ] ENG-04: CTGAN/TVAE 수렴 모니터링 및 Early Stopping 구현
- [ ] ENG-05: 시계열 lag 자기상관 보존 로직 구현
- [ ] ENG-06: KCD 질병기호 및 의약품코드 한국형 가명화 구현
- [ ] `test_engine_high_fidelity.py` 12개 테스트 100% PASS
- [ ] KPI-1~6 전부 목표치 달성
- [ ] 최종 체크포인트 STATE = DONE 출력
