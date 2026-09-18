# [작업 명세서] 합성데이터 엔진 결함 방어 및 범용성 하드닝 (5-Step Hardening Plan)

## 📌 배경 및 목적
1차 심의 지적사항(선후관계, 조건부 결측, 0값 모순, 5세 단위 구간화, 원본 유일 레코드 100% 차단, pMSE, Dual DCR/NNDR/CAP 등)이 반영된 상태에서, 통계적·프라이버시 관점에서 발생할 수 있는 5대 잠재 결함(통계적 왜곡, 소수자 소외, 순환모순, DP 경계 파괴, 부분공간 안전성 착시)을 선제적으로 차단하고, **지원 가능한 정형·표형(tabular) 공공데이터에 대해 데이터셋별 하드코딩 없이 동작할 수 있도록 범용성을 강화**한다.

> [!IMPORTANT]
> **핵심 안전 원칙 (Fail-Safe & Evaluation Policy)**
> 1. 어떠한 임의의 데이터에서도 100% 동작한다고 단정하지 않는다. 입력 데이터만으로 판단할 수 없는 경우에는 `FAIL_SAFE` 또는 `NOT_EVALUATED` / `UNKNOWN` 상태를 사용한다.
> 2. **평가 실패 != 안전**: 어떠한 privacy/quality metric 계산이 실패하더라도 기본값으로 `safe=True`를 반환해서는 절대 안 된다.
> 3. 테스트 통과를 위한 assertion 삭제, 임계값 완화, skip/xfail 처리를 엄격히 금지한다.

---

## 📌 실행 규칙 (Agent Execution Protocol)
1. 에이전트는 본 명세서의 **Step 1부터 Step 5까지 순차적으로 실행**한다.
2. 각 Step마다 **[요구사항 분석 → 신규 단위 테스트 작성 → 최소 코드 수정 → 신규 및 기존 회귀 테스트 통과]** 순서로 진행한다.
3. 모든 테스트 통과가 확인되면 본 문서의 해당 Step 체크박스를 `[ ]`에서 `[x]`로 수정한다.
4. 사용자에게 중간 확인을 묻지 않고 루프를 자율 완결한다.
5. 장시간 외부 학습/대규모 실험은 금지하며, 빠르고 재현 가능한 `pytest` 단위 테스트로만 검증한다.

---

### [x] Step 1. 고정 상수 스파이크 왜곡 방지 및 확률적 통계 스무딩 보정

#### 1. 문제점 및 배경
- 날짜/수치 선후관계 보정 시 `퇴거일 = 입주일 + 30일`, `지원시작일 = 신청일 + 7일` 처럼 고정 상수를 가산하면 특정 간격에 비정상 스파이크(Dirac Delta)가 발생하여 원본의 시계열 간격 분포가 심각하게 왜곡되고 합성데이터 식별 핑거프린트가 됨.
- 또한 모든 간격(lag)이 항상 LogNormal 분포를 따른다고 일률적으로 가정할 수 없음.

#### 2. 상세 구현 요구사항
1. **`sample_empirical_lags()` 우선순위 알고리즘**:
   - `random_state` 주입 가능 (`np.random.default_rng(random_state)`).
   - **우선순위 1 (충분한 양의 lag 표본 $\ge 30$)**:
     - 원본의 유효 양수 lag($\Delta = T_2 - T_1 > 0$) 표본에서 직접 empirical bootstrap 또는 empirical quantile sampling 수행.
     - 극단치 영향을 줄이기 위해 상위 99.5% 윈저라이징(robust clipping) 적용.
   - **우선순위 2 (표본 부족 $1 \le N < 30$)**:
     - Median, IQR, MAD 등 robust 통계량 기반 parametric fallback (Robust LogNormal 적합).
   - **우선순위 3 (원본 참조정보 부재)**:
     - bounded generic fallback 사용 (예: 최소 1일 ~ 최대 60일 범위 명시적 제한 난수).
     - fallback 사용 여부를 metadata/log에 명시 기록.
2. **`DatasetRuleEngine.postprocess()` 리팩토링**:
   - 고정된 `+ pd.Timedelta(days=30)`, `+ pd.Timedelta(days=7)` 구현 완전 제거.
   - 원본 데이터셋(`orig`)의 해당 컬럼 간격 분포를 참조하는 `sample_empirical_lags(orig, col1, col2, size=len(too_early), random_state=seed)` 적용.
   - 상한/하한 경계 보정(예: 12개월) 시에도 모든 값이 단일 경계점에 몰리지 않도록 미세 스무딩 처리.

#### 3. 검증 단위 테스트 요구사항
신규 테스트 파일 `packages/synthetic_engine/tests/test_hardening_step1.py`:
- `test_empirical_lag_sampling_preserves_variation`: lag 결과가 고정 단일값이 아니며 자연스러운 분산을 유지하는지 검증.
- `test_postprocess_does_not_create_fixed_lag_spike`: 후처리 후 특정 일자 차이의 빈도가 100%에 도달하지 않는지 검증.
- `test_lag_sampling_respects_positive_and_domain_bounds`: 샘플링된 lag가 항상 양수($\Delta > 0$)이며 도메인 범위를 만족하는지 검증.
- `test_lag_sampling_fallback_is_reproducible_with_seed`: 동일 seed 주입 시 동일 결과 재현 검증.
- 기존 회귀 테스트: `test_vulnerable_support_rules`, `test_youth_rent_rules` 통과.

---

### [x] Step 2. 원본 유일 레코드 차단 시 소수자 소외(Minority Vanishing) 방지

#### 1. 문제점 및 배경
- **Full-row Exact Clone**과 **Unique QI Combination**은 서로 다른 문제임.
- 비-QI 연속형 변수만 미세 변경하더라도 QI 조합이 여전히 원본 유일 레코드와 동일하다면 재식별 위험이 잔존함.
- 반대로 유일 레코드를 무조건 전부 Drop하면 희귀 질환/취약계층 소수자 집단의 표본이 완전히 소멸(Minority Vanishing Bias)함.

#### 2. 상세 구현 요구사항
1. **Full-row Exact Clone vs Unique QI 분리 대응**:
   - **(1) Full-row Exact Clone (`raw_all_tuples` 일치)**:
     - 비-QI 연속형 속성 중 perturbation 가능한 속성 탐색.
     - domain constraint를 위반하지 않는 범위에서 컬럼별 robust scale(IQR, MAD, domain width) 기반 local perturbation 적용.
     - perturbation 후 exact clone이 해소되고 모든 rule을 통과하면 유지, 실패 시 최종 drop/resample.
   - **(2) Unique QI Combination (`raw_unique_qi_tuples` 일치)**:
     - non-QI perturbation만으로 안전하다고 오판하지 않음.
     - 해당 행은 안전(safe)으로 분류하지 않고, QI generalization, category grouping, resampling 또는 drop 정책 적용.
2. **Minority Preservation (집단 수준 대표성 보존)**:
   - 개인 식별 가능 패턴(유일 결합)은 차단하되, 소수자 집단의 출현 비율(Prevalence), 주변 분포(Marginal Distribution), 범주 분포의 통계적 대표성은 최대한 보존.
3. **재현성 보장**:
   - `escape_unique_clones(..., random_state=42)` 지원.

#### 3. 검증 단위 테스트 요구사항
신규 테스트 파일 `packages/synthetic_engine/tests/test_hardening_step2.py`:
- `test_minority_group_retention_after_clone_escape`: clone escape 적용 시 소수자 집단 비율 보존 검증.
- `test_unique_qi_combination_is_not_safe_with_non_qi_jitter_only`: non-QI만 지터링된 유일 QI 행이 safe로 오판되지 않는지 검증.
- `test_escape_jitter_preserves_domain_constraints`: 지터링 후에도 도메인 제약(양수, 범위 등) 준수 검증.
- `test_exact_full_row_clone_rate_remains_zero`: 전체 행 원본 완전 일치율은 여전히 0%를 유지하는지 검증.
- `test_escape_jitter_is_reproducible_with_seed`: 동일 seed 시 재현성 검증.
- 기존 회귀 테스트: `test_raw_unique_exact_clones_blocking` 통과.

---

### [x] Step 3. SCC 기반 DAG 사이클 분석 및 순환 규칙 처리 (Generalization)

#### 1. 문제점 및 배경
- $A \le B$ 와 $B \le A$ 는 모순이 아니라 $A = B$ 동치(Equivalence)로 해석 가능함.
- 반면 $A < B, B < C, C < A$ 는 실제 논리 모순(Strict Contradiction)임.
- 단순 cycle 감지로 confidence 낮은 edge를 무조건 지우면 안 되며, SCC(Strongly Connected Component) 기반 의미 분석이 필요함.

#### 2. 상세 구현 요구사항
1. **`resolve_rule_dependencies_dag()` 파이프라인**:
   - 규칙들을 Directed Graph로 구성.
   - Tarjan / Kosaraju 알고리즘을 통한 SCC(Strongly Connected Component) 탐지.
   - SCC 내부 규칙 의미 분석:
     - non-strict inequality($\le, \ge$)로만 구성된 cycle $\implies$ $A = B$ 동치 관계로 collapse.
     - strict inequality($<, >$)가 포함된 conflicting cycle $\implies$ confidence, support, original violation rate 기반 최하위 edge 가지치기(Pruning).
   - cycle 해소 후 최종 DAG 구축 $\rightarrow$ 위상 정렬(Topological Sort)을 통해 결정론적(deterministic) 실행 순서 확정.
2. **Rule 의미별 엄격 구분**:
   - `DATE_ORDER`, `LESS_THAN`, `LESS_THAN_OR_EQUAL`, `GREATER_THAN`, `EQUALITY` 각각의 속성을 구분 처리.
3. **미등록 데이터셋 자율 적용 임계값**:
   - `DependencyDiscoveryEngine.discover_all_dependencies(df)` 결과 중 최소 신뢰도(예: confidence $\ge 99.5\%$, support $\ge 5\%$)를 통과한 규칙만 자동 적용. 신뢰도 미달 규칙은 discovery 보고서에는 남기되 자동 보정에서는 제외.

#### 3. 검증 단위 테스트 요구사항
신규 테스트 파일 `packages/synthetic_engine/tests/test_hardening_step3.py`:
- `test_rule_dependency_cycle_resolution`: 사이클 포함 그래프 정상 해결 검증.
- `test_non_strict_cycle_collapses_to_equivalence`: $A \le B, B \le A$ 가 동치 관계로 collapse되는지 검증.
- `test_strict_cycle_prunes_lowest_confidence_edge`: strict 사이클에서 최저 신뢰도 엣지만 제거되는지 검증.
- `test_discovered_rules_are_applied_in_topological_order`: 위상 정렬 순서대로 보정이 적용되는지 검증.
- `test_low_confidence_discovered_rule_is_not_auto_applied`: 저신뢰도 규칙 자동 적용 배제 검증.
- `test_rule_resolution_is_deterministic`: 동일 입력에 대해 항상 동일한 위상 정렬 순서 보장 검증.
- 기존 회귀 테스트: `test_automated_rule_discovery` 통과.

---

### [x] Step 4. DP 후 Domain Projection 및 Private Bound 노출 차단

#### 1. 문제점 및 배경
- DP noise 주입 후 도메인을 복원할 때, 원본 private raw dataset의 exact min/max(`raw[col].min()`, `max()`)를 projection bound로 직접 사용하면 **원본의 극단값이 합성데이터에 그대로 누출되는 심각한 프라이버시 결함**이 발생함.
- 또한 컬럼명 하드코딩(`if "나이" in col`)은 범용 엔진의 원칙을 위배함.

#### 2. 상세 구현 요구사항
1. **Domain Bounds 우선순위 체계**:
   - 우선순위 1: Schema / Catalog에 사전 정의된 public bound
   - 우선순위 2: 정책 / 업무규칙으로 정의된 bound
   - 우선순위 3: User-provided bound
   - 우선순위 4: DP-safe하게 계산된 bound (라플라스/가우시안 노이즈가 반영된 추정치)
   - **우선순위 5: 위 정보가 없으면 원본 raw exact min/max의 직접 사용을 엄격히 금지** (하한 0 등 물리적 기본 non-negative 규칙만 적용).
2. **`project_domain_constraints(df, plan, schema=None)` 파이프라인**:
   - 컬럼명 하드코딩 완전 배제 $\rightarrow$ `ColumnPlan`, `schema`, 메타데이터의 타입/제약 정보를 기반으로 판단.
   - 정수형: `np.round()` $\rightarrow$ domain clip $\rightarrow$ nullable dtype 보존 $\rightarrow$ `Int64` (NaN을 강제로 0으로 바꾸지 않음).
   - Non-negative 및 allowed discrete values 투영.
3. **결정론적 재현성**:
   - 노이즈 주입 후 투영 과정의 결정론적(deterministic) 처리.

#### 3. 검증 단위 테스트 요구사항
신규 테스트 파일 `packages/synthetic_engine/tests/test_hardening_step4.py`:
- `test_dp_projection_restores_integer_domain`: 정수형 복원 및 소수점 제거 검증.
- `test_dp_projection_enforces_non_negative_bounds`: 비음수 제약 보장 검증.
- `test_dp_projection_respects_public_schema_bounds`: 공개 스키마 경계값 준수 검증.
- `test_dp_projection_does_not_use_raw_exact_minmax_without_permission`: raw min/max 직접 누출 방지 검증.
- `test_dp_projection_preserves_nullable_values`: 결측값(NaN)의 0 왜곡 방지 및 Nullable 타입 보존 검증.
- `test_dp_projection_is_deterministic_after_seeded_noise`: seed 기반 재현성 검증.
- 기존 회귀 테스트: `test_audit_remediation.py` 전건 통과.

---

### [x] Step 5. 준식별자(QI) 부분공간 DCR/NNDR 및 Fail-Safe 평가

#### 1. 문제점 및 배경
- QI는 수치형뿐만 아니라 범주형, 혼합형(Mixed) 속성이 공존함.
- 고차원 데이터에서 전체 DCR은 인위적으로 높아 보이지만 준식별자 부분공간에서는 원본과 매우 가까운 '안전성 착시(False Safety)'가 발생할 수 있음.
- **평가 실패 시 `safe=True`를 반환하는 것은 치명적인 결함**임.

#### 2. 상세 구현 요구사항
1. **다양한 QI 타입별 거리 측정 (Mixed Distance)**:
   - numeric QI: Robust scaling (IQR / MAD 기반 표준화 후 유클리디안 거리).
   - categorical QI: Hamming distance 또는 One-Hot distance.
   - mixed QI: 무거운 외부 라이브러리 없이 Numpy/Scipy 기반의 Gower distance 동등 알고리즘 구현.
2. **`evaluate_subspace_dcr()` 함수 구현**:
   - 시그니처: `evaluate_subspace_dcr(raw_train, synthetic, qi_columns, raw_holdout=None, sample_size=500, random_state=None)`
   - 산출값: `sample_size_raw`, `sample_size_synthetic`, `qi_columns`, `dcr_p05`, `dcr_median`, `nndr_p05`, `nndr_median`, `nndr_low_ratio`, `exact_qi_match_rate`, `status`.
   - `raw_holdout`이 주어질 경우: Raw Holdout $\rightarrow$ Raw Train 거리 분포를 산출하여 상대적 근접 위험도(`relative_privacy_risk`)를 비교 평가.
3. **Fail-Safe 원칙**:
   - 샘플 부족, 계산 오류 발생 시: `safe=True` 반환 절대 금지! `status="NOT_EVALUATED"` 또는 `status="ERROR"` 반환.
   - 종합 판정에서도 `NOT_EVALUATED`는 `PASS`로 처리하지 않음.

#### 3. 검증 단위 테스트 요구사항
신규 테스트 파일 `packages/synthetic_engine/tests/test_hardening_step5.py`:
- `test_subspace_dcr_numeric_qi`: 수치형 QI 거리 계산 검증.
- `test_subspace_dcr_categorical_qi`: 범주형 QI 거리 계산 검증.
- `test_subspace_dcr_mixed_qi`: 혼합형 QI Gower 거리 계산 검증.
- `test_subspace_dcr_detects_near_clone_risk`: 부분공간 근접 복제 위험 정상 탐지 검증.
- `test_subspace_dcr_holdout_baseline`: Holdout 베이스라인 대비 상대 위험도 계산 검증.
- `test_subspace_dcr_failure_is_not_safe`: 계산 실패 시 safe=True가 아닌 NOT_EVALUATED 반환 검증.
- `test_subspace_dcr_is_reproducible`: seed 기반 거리 계산 재현성 검증.
- 기존 회귀 테스트: `test_dcr_and_nndr_evaluation` 통과.

---

## 📋 완료 보고 규격 (Step별 상세 보고)
1. **[Step 1]**: 사용한 lag sampling 전략, empirical/fallback 선택 조건, 고정 lag spike 제거 여부, 신규 테스트 결과
2. **[Step 2]**: exact clone 처리 방식, unique QI 처리 방식, minority group retention 지표, exact clone rate, 신규 테스트 결과
3. **[Step 3]**: 발견된 dependency graph, SCC/cycle 처리 방식, 제거된 rule 및 이유, topological order, 신규 테스트 결과
4. **[Step 4]**: DP 이후 projection 대상, 사용한 domain constraint source, integer/non-negative/domain 위반 건수 before/after, raw exact min/max 미사용 확인, 신규 테스트 결과
5. **[Step 5]**: 사용한 QI, QI 타입, 사용한 distance, DCR/NNDR 결과, exact QI match rate, holdout baseline 존재 시 비교 결과, NOT_EVALUATED 발생 여부, 신규 테스트 결과
6. **[최종 회귀]**: 전체 14개 기존 테스트 + 신규 Step 1~5 테스트 100% PASS 확인.
