# [작업 명세서] 합성데이터 생성·품질·안전성 파이프라인 고도화 (5-Step)

## 📌 실행 규칙 (Agent Execution Protocol)
1. 에이전트는 본 명세서의 **Step 1부터 Step 5까지 순차적으로 실행**한다.
2. 각 Step이 완료될 때마다 명시된 `pytest` 단위 테스트 명령어를 반드시 실행하여 **100% 통과(PASS)**하는지 확인한다.
3. 테스트 통과가 확인되면 본 문서의 해당 Step 체크박스를 `[ ]`에서 `[x]`로 수정한다.
4. 사용자에게 "다음 단계를 진행할까요?"라고 묻지 말고 **즉시 다음 Step으로 진행하여 루프를 자율 완결**한다.
5. 임의로 기존 동작 로직을 파괴하지 않고, 명시된 함수 시그니처와 수식/조건을 엄격히 준수한다.

---

### [x] Step 1. 시맨틱 컬럼 매퍼 및 데이터 관계 자동 탐색 엔진 구축

#### 1. 목표 및 대상 파일
- **생성/수정 대상 파일**:
  - `packages/synthetic_engine/synthetic_engine/rules/base.py`
  - `packages/synthetic_engine/synthetic_engine/rules/catalog.py`
  - `packages/synthetic_engine/synthetic_engine/rules/discovery.py`

#### 2. 상세 구현 요구사항
1. **`base.py` (규칙 데이터 모델)**
   - Enum `RuleType`: `DATE_ORDER`, `NULLABLE_IF`, `REQUIRED_IF`, `MIN_MAX`, `LESS_THAN_OR_EQUAL`, `CALCULATED_FIELD`, `UNIQUE_RECORD_MATCH_BLOCK` 정의.
   - Enum `ActionType`: `RECALCULATE`, `REPAIR_CONDITIONAL`, `DROP` 정의.
   - Dataclass `DatasetRule`: `name`, `rule_type`, `columns`, `action`, `params`, `description` 필드 및 `preceding_column`, `succeeding_column`, `primary_column`, `implied_zero_column`, `condition_column`, `target_null_column` 프로퍼티 구현.
   - Dataclass `DatasetSchemaConfig`: `dataset_name`, `dataset_id`, `aliases`, `quasi_identifiers`, `sensitive_columns`, `numerical_columns`, `categorical_columns`, `date_columns`, `rules` 필드 정의.

2. **`catalog.py` (시맨틱 컬럼 매퍼)**
   - `resolve_column_name(target: Any, candidates: Any) -> str | None`:
     - 인자 순서 역전(`resolve_column_name("신청일자", cols)` vs `resolve_column_name(cols, "신청일자")`) 자동 감지 및 보정.
     - `target`이 DataFrame, list, Index 등 모든 형태를 지원.
     - 공백, 언더바, 괄호 제거 정규화(`normalize`).
     - 동의어 사전(`canonicalize`): `자산 <-> 가액`, `일자 <-> 일`, `금액 <-> 액`, `보증금 <-> 전세금`, `체납 <-> 연체`, `나이 <-> 연령` 치환 매칭.
   - `match_dataset_schema(df=None, dataset_hint="", cols=None, dataset_name="") -> DatasetSchemaConfig | None`:
     - 힌트명(파일명/별칭/ID) 우선 매칭 및 컬럼 매칭 스코어(2개 이상 일치) 기반 카탈로그 스키마 자동 식별.

3. **`discovery.py` (`DependencyDiscoveryEngine`)**
   - `discover_temporal_orders(df: pd.DataFrame) -> list[DatasetRule]`:
     - 날짜 파싱 성공률 >= 60%인 컬럼 추출.
     - 두 날짜 컬럼 쌍 (T1, T2)에 대해 $P(T_1 \le T_2) \ge 99.5\%$ 일 때 `RuleType.DATE_ORDER` 규칙 도출.
   - `discover_conditional_nulls(df: pd.DataFrame) -> list[DatasetRule]`:
     - (1) 결측 연쇄: $P(B=\text{NULL} \mid A=\text{NULL}) \ge 99.5\%$ 탐색.
     - (2) 상태 기반 결측: 범주형 컬럼 A의 특정 값(예: `'N'`, `'0'`, `'무'`, `'없음'`)일 때 타겟 컬럼 B의 결측 비율 $P(B=\text{NULL} \mid A=\text{val}) \ge 99.5\%$ 탐색.
   - `discover_zero_implications(df: pd.DataFrame) -> list[DatasetRule]`:
     - 수치형 A=0 일 때 수치형 B=0인 비율 $P(B=0 \mid A=0) \ge 99.0\%$ 탐색.

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -m pytest packages/synthetic_engine/tests/test_audit_remediation.py -k "test_semantic_column_resolution or test_schema_matching_by_columns or test_automated_rule_discovery" -v
```

---

### [x] Step 2. 3단계 계층 업무규칙 전처리·후처리 엔진 구축

#### 1. 목표 및 대상 파일
- **생성/수정 대상 파일**:
  - `packages/synthetic_engine/synthetic_engine/rules/engine.py`

#### 2. 상세 구현 요구사항
`DatasetRuleEngine` 클래스 구현:
1. **`preprocess(df, schema=None, dataset_name="", return_report=False)`**:
   - 나이 컬럼(1세 단위) 5세 단위 구간화 (`pd.cut` 또는 `(age // 5) * 5`).
   - 1% 미만 희소 범주값 '기타' 통합 (상태 매핑 딕셔너리 보존).
   - 상위 99.9% 극단값 윈저라이징 캡핑.
2. **`postprocess(synthetic, original=None, schema=None, dataset_name="", raw_df=None, return_violations=False)`**:
   - `original` 또는 `raw_df`가 전달되면 이를 참조 데이터프레임으로 사용.
   - **1단계: 산식 재계산 (`RECALCULATE`)**
     - 연체료합계 = 부과금액 * 연체요율 (또는 세부 연체료 컬럼 합산).
     - 주당근무시간 = 40 - 단축시간 (하한 15, 상한 35).
     - 총수급기간 = 최초수급연월 기준 경과 개월수 (`elapsed_months`).
   - **2단계: 논리 모순 조건부 보정 (`REPAIR_CONDITIONAL`)**
     - 해지사유가 없거나 '정상'인 경우 $\implies$ `퇴거일자 = None` (NULL 강제).
     - 퇴거일자 < 입주일자인 경우 $\implies$ `퇴거일자 = 입주일자 + 30일`.
     - 지원시작일자 < 신청일자인 경우 $\implies$ `지원시작일자 = 신청일자 + 7일`.
     - 자녀수 == 0인 경우 $\implies$ `출산자녀수 = 0`, `출산여부 = 'N'` (또는 0).
     - 총자산 < 0인 경우 $\implies$ `총자산 = 0`.
     - 부동산자산 > 총자산인 경우 $\implies$ `부동산자산 = 총자산`.
     - 체납개월수 == 0인 경우 $\implies$ `체납금액 = 0`.
     - 희망돌보미 나이 $\implies$ 5세 단위 구간화(`(age // 5) * 5`).
   - **3단계: 원본 일치 제거 (`filter_exact_and_unique_clones`)**
     - 원본 빈도=1인 유일 레코드와 일치하는 행 100% 제거.
     - 원본 전체 레코드와 완전 일치하는 행 제거.
3. **`audit_rules(df, schema=None, dataset_name="") -> dict[str, int]`**:
   - 현재 데이터프레임에서 위반되는 업무규칙 건수를 점검하여 딕셔너리 반환.

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -m pytest packages/synthetic_engine/tests/test_audit_remediation.py -k "test_vulnerable_support_rules or test_youth_rent_rules or test_childcare_support_zero_children or test_childcare_helper_age_binning or test_public_rental_arrears_calculation" -v
```

---

### [x] Step 3. 개인정보 안전성 가드레일 고도화 (Dual DCR, NNDR, CAP)

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `packages/synthetic_engine/synthetic_engine/privacy/guardrails.py`

#### 2. 상세 구현 요구사항
`PrivacyGuardrails` 클래스 확장:
1. **`filter_exact_duplicates(raw, synthetic, filter_raw_unique_only=False)`**:
   - `Counter`로 원본 데이터의 행 튜플 빈도 계산.
   - 빈도가 1인 튜플 집합 `raw_unique_tuples` 추출.
   - 합성 데이터 중 `raw_unique_tuples`와 일치하는 행은 **100% 무조건 제거**.
   - `raw_unique_duplicates_found > 0`인 경우 `status = "FAIL"` 판정.
2. **`evaluate_dcr(raw, synthetic, plan, sample_size=500)`**:
   - 수치형 컬럼 Min-Max 정규화.
   - **Syn-to-Raw DCR**: 합성 데이터의 최근접 원본 거리 $d_1$ 및 차근접 거리 $d_2$ 계산.
   - **NNDR**: $d_1 / (d_2 + 10^{-9})$ 계산. $NNDR < 0.2$ 비율을 `nndr_risk_rate`로 집계.
   - **Raw-Internal DCR (Baseline)**: 원본 내부 레코드 간 최근접 거리 5th 백분위수(`raw_internal_dcr_5th_percentile`) 산출.
   - 상대적 근접 위험도: $d_1 < 0.5 \times \text{raw\_5th}$ 비율 산출.
3. **`evaluate_cap(raw, synthetic, plan, qi_columns=None, sensitive_columns=None)`**:
   - 준식별자(QI) 일치 그룹의 민감속성(SA) 최빈값 추론 공격 시뮬레이션.
   - 원본 Baseline 최빈값 추론 성공률 대비 합성데이터 참조를 통한 추론 이득($\text{Inference Advantage} = CAP - CAP_{\text{baseline}}$) 계산. ($> 0.05$이면 `REVIEW`, $> 0.15$이면 `FAIL`).

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -m pytest packages/synthetic_engine/tests/test_audit_remediation.py -k "test_raw_unique_exact_clones_blocking or test_dcr_and_nndr_evaluation or test_cap_attribute_inference" -v
```

---

### [x] Step 4. 다변량 유용성 평가 지표 확장 (pMSE, Spearman, Cramér's V)

#### 1. 목표 및 대상 파일
- **생성 대상 파일**:
  - `packages/synthetic_engine/synthetic_engine/quality/utility.py`
- **수정 대상 파일**:
  - `packages/synthetic_engine/synthetic_engine/quality/assessment.py`

#### 2. 상세 구현 요구사항
1. **`compute_pmse(original, synthetic, plan, max_samples=2000)`**:
   - 원본(라벨 0)과 합성(라벨 1) 결합 후 로지스틱 회귀 모델 학습.
   - 성향 점수 $\hat{p}_i$ 추정 및 $pMSE = \frac{1}{N} \sum_{i=1}^N (\hat{p}_i - c)^2$ 산출 (단, $c = n_{\text{syn}} / N$).
   - 자유도 $k$ 기반 기대치 $\mathbb{E}[pMSE] = \frac{k(1-c)^2 c}{N}$.
   - $pMSE\_Ratio = pMSE / \mathbb{E}[pMSE]$ 산출 ($\le 3.0$ 통과).
2. **`evaluate_spearman_correlations(original, synthetic, numerical_columns)`**:
   - 수치형 변수 쌍별 Spearman 순위 상관계수 보존율 및 MAE 산출.
3. **`evaluate_categorical_associations_with_significance(original, synthetic, categorical_columns)`**:
   - 범주형 쌍의 Cramér's V 계산. 원본에서 $V \ge 0.15$인 유의 연관쌍 목록 추출.
   - 합성 데이터에서 해당 쌍들이 연관성을 유지하고 있는지 보존율(`significant_preservation_rate`) 산출.
4. **`assessment.py` 연동**:
   - `evaluate()` 반환 딕셔너리에 `pmse`, `spearman`, `categorical_associations`, `cap` 추가 및 `build_auto_assessment` 종합 판정에 반영.

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -m pytest packages/synthetic_engine/tests/test_audit_remediation.py -k "test_pmse_computation or test_spearman_correlation_evaluation or test_cramers_v_significant_pairs_preservation" -v
```

---

### [x] Step 5. 생성 파이프라인 결합, 심의 JSON 연동 및 전체 회귀 테스트

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `packages/synthetic_engine/synthetic_engine/generators/sampling.py`
  - `packages/synthetic_engine/synthetic_engine/pipeline.py`

#### 2. 상세 구현 요구사항
1. **`sampling.py`**:
   - 각 샘플링 배치 chunk 생성 직후 `DatasetRuleEngine.postprocess(chunk, raw_df=training)` 호출.
   - 원본 빈도=1인 유일 레코드 집합 `raw_unique_keys`는 `duplicate_policy`와 무관하게 차단 집합(`effective_blocked`)에 무조건 포함.
   - 루프 종료 후 최종 `result`에 대해 1회 더 `postprocess` 적용.
2. **`pipeline.py`**:
   - 모델 학습 전 `DatasetRuleEngine.preprocess(masked, dataset_name=original_filename)` 호출.
   - 샘플링 완료 후 `DatasetRuleEngine.postprocess(synthetic, raw_df=raw, dataset_name=original_filename)` 호출.
   - `DatasetRuleEngine.audit_rules(synthetic, dataset_name=original_filename)` 호출하여 규칙 위반 감사 결과 생성.
   - 최종 `job_id_synthetic_evaluation_report.json` 리포트 페이로드에 `rule_audit`, `safety(DCR, CAP, Unique)`, `utility(pMSE, Spearman, Cramér's V)` 포함하여 저장.

#### 3. 검증 단위 테스트 (전체 회귀 테스트)
```powershell
.venv\Scripts\python.exe -m pytest packages/synthetic_engine/tests/test_audit_remediation.py -v
.venv\Scripts\python.exe -m pytest packages/synthetic_engine/tests/test_temporal_constraints.py -v
```
