# [작업 명세서] AI 친화 공공데이터 가이드 생성 기능 일반화 및 고도화 (5-Step)

## 📌 실행 규칙 (Agent Execution Protocol)
1. 에이전트는 본 명세서의 **Step 1부터 Step 5까지 순차적으로 실행**한다.
2. 각 Step이 완료될 때마다 명시된 테스트 또는 무결성 검증 명령어를 실행하여 통과하는지 확인한다.
3. 테스트 통과가 확인되면 본 문서의 해당 Step 체크박스를 `[ ]`에서 `[x]`로 수정한다.
4. 사용자에게 "다음 단계를 진행할까요?"라고 묻지 말고 **즉시 다음 Step으로 진행하여 루프를 자율 완결**한다.
5. **절대 금지사항**:
   - 특정 도메인(태양광, 발전량 등) 컬럼명이나 전용 조건문을 비즈니스 로직에 하드코딩하지 말 것.
   - 데이터에서 확인되지 않는 수식/정보를 AI가 임의로 생성(환각)하지 말 것. 미확인은 `REVIEW_REQUIRED`, 해당 없으면 `NOT_APPLICABLE`.
   - 기존 정상 동작 기능(file/api/hybrid 분기, Markdown/DOCX/HWPX/ODT 출력, canonicalItems 상태 관리)을 파괴하지 말 것.
   - 사용자가 직접 테스트할 수 있도록 장시간 학습이나 무거운 외부 호출을 임의로 돌리지 말 것.

---

### [x] Step 1. Canonical Schema 및 메타데이터 템플릿에 `processing` 구조 확장

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/data/ai_guide/templates/schemas/canonical-metadata.schema.json`
  - `apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_metadata_template.json`

#### 2. 상세 구현 요구사항
1. **`canonical-metadata.schema.json` 스키마 확장**:
   - `properties`에 신규 최상위 블록 `processing` 정의:
     ```json
     "processing": {
       "type": "object",
       "additionalProperties": false,
       "properties": {
         "integration": { "$ref": "#/$defs/processingIntegration" },
         "derived_fields": { "type": "array", "items": { "$ref": "#/$defs/derivedField" } },
         "transformations": { "type": "array", "items": { "$ref": "#/$defs/transformationRule" } },
         "missing_value_processing": { "type": "array", "items": { "$ref": "#/$defs/missingValueRule" } },
         "outlier_processing": { "type": "array", "items": { "$ref": "#/$defs/outlierRule" } },
         "quality_flags": { "type": "array", "items": { "$ref": "#/$defs/qualityFlag" } }
       }
     }
     ```
   - `$defs`에 세부 객체 스키마 정의:
     - `processingIntegration`: `is_integrated`(bool), `description`, `method`, `join_type`, `join_keys`(array), `temporal_alignment`, `spatial_alignment`, `source_dataset_ids`, `external_sources`, `output_description`, `limitations`.
     - `derivedField`: `field_id`, `field_name`, `derivation_type`(enum: observed, calculated, derived, aggregated, interpolated, estimated, modeled, mapped, imputed, normalized, encoded, other), `source_fields`(array), `description`, `method`, `formula_or_rule`, `aggregation`, `window`, `unit`, `parameters`, `fallback_rule`, `reproducible`, `confidence`, `notes`.
     - `missingValueRule`: `target_field_ids`(array), `detected_missing_count`, `detected_missing_ratio`, `method`(enum or string: none, drop, constant, forward_fill, backward_fill, linear_interpolation, mean, median, group_mean, temporal_mean, regression, physical_formula, model_based, custom), `method_description`, `steps`(array of objects: step, name, rule), `grouping_keys`, `temporal_window`, `parameters`, `fallback_method`, `clipping_rule`, `affected_record_count`, `quality_flag_field`, `original_value_preserved`, `limitations`.
     - `outlierRule`: `target_field_ids`(array), `detection_method`, `threshold`, `rule`, `action`, `affected_count`, `replacement_method`, `quality_flag_field`, `notes`.
     - `qualityFlag`: `flag_field`, `description`, `target_fields`(array), `values`(array of objects: code, name, meaning, value_origin), `meaning`.
   - `fields[]` 스키마 항목 확장:
     - `value_origin` (enum: observed, derived, calculated, imputed, estimated, modeled)
     - `source_dataset_id`, `source_field`, `derived`(bool), `derivation_ref`, `missing_processing_ref`, `quality_flag_ref`.
   - `ai` 스키마 확장:
     - `recommended_features`(array), `target_candidates`(array), `time_series_characteristics`, `spatial_characteristics`, `bias`, `representativeness`, `quality_flag_usage`, `imputed_data_usage`, `usage_risks`(array).
   - 최상위 `required` 목록에 `processing`을 추가하되, 구버전 역호환을 위해 optional로 다룰 수 있는 필드 정의 점검.

2. **`ai_ready_metadata_template.json` 동기화**:
   - `_canonical.root_blocks`에 `"processing"` 추가.
   - 템플릿 본문에 `"processing"` 기본 객체 구조 추가 (빈 integration, 빈 배열 derived_fields, missing_value_processing, outlier_processing, quality_flags).
   - `fields` 템플릿 아이템에 `value_origin: "observed"`, `derived: false`, `quality_flag_ref: null` 등 기본값 플레이스홀더 제공.

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -c "import json; from jsonschema import Draft202012Validator; s=json.load(open('apps/api/src/synthetic_api/data/ai_guide/templates/schemas/canonical-metadata.schema.json', encoding='utf-8')); Draft202012Validator.check_schema(s); print('Schema valid!')"
```

---

### [x] Step 2. 분석 엔진 및 바인딩 계약(Contract) 확장

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/application/services/ai_guide_analysis.py`
  - `apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py`

#### 2. 상세 구현 요구사항
1. **`ai_guide_analysis.py` 분석 확장**:
   - 데이터 분석 결과 프로파일링 시 다음을 추론/분석하되 임의의 환각 없이 사실 기반으로 생성:
     - 컬럼별 결측치 통계 기반으로 결측이 있는 경우 `missing_value_processing` 후보 추출 (단, 명확한 대체 규칙이 없으면 `status="REVIEW_REQUIRED"`, `reason="결측치 처리 방식 기관 확인 필요"`).
     - 파생/계산 가능성이 있는 컬럼 탐색(예: 날짜 컬럼에서 연/월/시 추출, 누적 컬럼 등) 및 `derivation_type` 기본값(`observed`) 부여.
     - 결측 플래그/품질 플래그 컬럼(0, 1, 2 등의 코드나 Y/N) 후보 감지 및 `quality_flags` 연결.
   - 단일 파일/단일 데이터 소스인 경우 `processing.integration.is_integrated = False` 설정.
2. **`binding.py`의 `Contract` 및 `canonical()` 함수 확장**:
   - `canonical()` 생성 함수에서 `model['processing']` 초기화 및 `canonicalItems`에 `processing` 관련 항목의 RFC 6901 JSON Pointer 경로 등록.
   - `Contract.resolve`에 새 별칭 등록:
     - `derived` -> `processing.derived_fields`
     - `missing_rule` -> `processing.missing_value_processing`
     - `outlier_rule` -> `processing.outlier_processing`
     - `quality_flag` -> `processing.quality_flags`
   - `fields`의 `value_origin`, `derivation_ref`, `quality_flag_ref`와 `canonicalItems` 상태 연동.

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_guide.py -k "test_analysis or test_binding or test_canonical" -v
```

---

### [x] Step 3. Presentation Model 및 목차 리팩토링 (`render.py`)

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/application/services/ai_guide_document/render.py`

#### 2. 상세 구현 요구사항
1. **`GUIDE_SECTION_DEFINITIONS` 전면 개편**:
   - 2장 `management` (데이터 구축 및 관리) 12개 하위절 반영:
     - `sources_collection` (2.1 데이터 원천 및 수집)
     - `integration` (2.2 데이터 연계·결합)
     - `cleaning` (2.3 데이터 정제)
     - `derivation_transformation` (2.4 데이터 파생·변환)
     - `missing_outlier_processing` (2.5 결측·이상값 처리)
     - `processing_validation` (2.6 데이터 가공 및 검수)
     - `quality` (2.7 데이터 품질)
     - `quality_flags` (2.8 품질 플래그 및 값 구분)
     - `metadata_interoperability` (2.9 메타데이터 및 표준화)
     - `lineage_changes` (2.10 데이터 계보 및 변경이력)
     - `privacy_deidentification` (2.11 개인정보 및 비식별화)
     - `rights_conditions` (2.12 저작권 및 이용조건)
   - 4장 `ai` (AI 활용 가이드) 8개 하위절 반영:
     - `ai_summary` (4.1 AI 활용성 요약)
     - `tasks` (4.2 AI 활용 가능 과업)
     - `training_info` (4.3 AI 학습·분석 활용 정보)
     - `recommended_features` (4.4 추천 입력변수 및 활용정보)
     - `bias_representativeness` (4.5 데이터 편향 및 대표성)
     - `limitations` (4.6 알려진 한계)
     - `corrected_estimated_usage` (4.7 보정·추정 데이터 활용 유의사항)
     - `usage_risks` (4.8 AI 활용 위험 및 유의사항) - *기존 `leakage_usage`의 호환 alias 유지*
2. **`_presentation_model(model, category)` 확장**:
   - Canonical `processing` 및 `ai`에서 뷰 바인딩용 컬렉션 투영:
     - `view['integrations']`: `processing.integration`이 활성화된 경우 단일 항목 리스트, 비활성화 시 빈 리스트
     - `view['derivedFields']`: `processing.derived_fields`
     - `view['missingValueRules']`: `processing.missing_value_processing`
     - `view['outlierRules']`: `processing.outlier_processing`
     - `view['qualityFlags']`: `processing.quality_flags`
     - `view['aiRecommendedFeatures']`: `ai.recommended_features`
     - `view['aiLimitations']`: `ai.limitations` 또는 `responsible_ai.known_limitations`
3. **하드코딩된 장 번호 제거 (DOCX / HWPX / ODT)**:
   - `_docx_remove_branch_sections`, `_hwpx_remove_branch`, `_odt_remove_branch` 함수 리팩토링:
     - `disabled = 4 if category == 'file' else 3` 제거!
     - 목차 번호 숫자 비교 대신, 해당 헤딩 텍스트 내의 **키워드(예: '오픈API' / 'OpenAPI' / '파일데이터' / '파일 데이터')** 또는 **semantic marker / section title**을 기반으로 대상 장 범위를 찾아 삭제하도록 개선.

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_guide_documents.py -k "test_render or test_docx or test_hwpx" -v
```

---

### [x] Step 4. 공통 템플릿 마크다운 확장 및 조건부 블록 처리

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_public_data_guide_template.md`
  - `apps/api/src/synthetic_api/application/services/ai_guide_document/render.py` (`prune_blocks`)

#### 2. 상세 구현 요구사항
1. **`ai_ready_public_data_guide_template.md` 템플릿 갱신**:
   - 개편된 12개 구축관리 하위절 및 8개 AI 하위절의 번호와 제목 반영.
   - 새롭게 추가되는 표와 설명 블록에 Mustache 반복 태그 구성:
     - `[데이터 연계·결합]`: `{{#integrations}}` ... 연계 설명 및 결합 기준 표 ... `{{/integrations}}`
     - `[데이터 파생·변환]`: `{{#derivedFields}}` ... 파생 필드 정의 표 (`field_name`, `derivation_type`, `source_fields`, `method`, `formula_or_rule`) ... `{{/derivedFields}}`
     - `[결측·이상값 처리]`: `{{#missingValueRules}}` ... 결측 처리 규칙 표 (`target_field_ids`, `method`, `method_description`, `quality_flag_field`) ... `{{/missingValueRules}}`
     - `[품질 플래그 및 값 구분]`: `{{#qualityFlags}}` ... 플래그 정의 및 코드 의미 표 ... `{{/qualityFlags}}`
     - `[추천 입력변수 및 활용정보]`: `{{#aiRecommendedFeatures}}` ... 추천 변수 표 ... `{{/aiRecommendedFeatures}}`
2. **조건부 출력 및 `prune_blocks` 연동**:
   - `is_integrated`가 `false`이거나 `integrations`가 비어 있으면 "데이터 연계·결합" 절 자동 숨김.
   - `derivedFields`가 없으면 "데이터 파생·변환" 절 자동 숨김 또는 대체 안내문 표시.
   - `qualityFlags`가 없으면 기관 확인 필요 여부에 따라 안내문 표기 또는 절 숨김.

---

### [x] Step 5. DOCX / HWPX / ODT 바인딩 동기화 및 종합 검증

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/application/services/ai_guide_document/render.py`
  - `apps/api/tests/test_ai_guide_documents.py`

#### 2. 상세 구현 요구사항
1. **Office Repeat Scope 확장**:
   - `_docx_repeat_scope`, `_docx_scope_items`에 신규 컬렉션 매핑 추가:
     - `integrations`, `derivedFields`, `missingValueRules`, `outlierRules`, `qualityFlags`, `aiRecommendedFeatures`.
   - 템플릿 docx/hwpx 내에 프로토타입 행이 존재하지 않는 신규 표의 경우에도 에러가 발생하지 않도록 graceful fallback 보장.
2. **태양광 검증 시나리오 작성 (테스트 케이스)**:
   - `test_ai_guide_documents.py`에 일반화된 파이프라인 검증 테스트 추가:
     - 외부 기상 데이터 결합(`is_integrated=True`)
     - 시간별 발전량 파생(`derivation_type='derived'`)
     - 일사량/전운량 결측치 보간(`method='linear_interpolation'`)
     - 발전량 결측보정 플래그(`quality_flags`)
     - AI 다변량 시계열 과업 및 변수 추천
     - 단일 CSV 입력 시 미존재 섹션(연계결합 등) 정상 생략 확인.

#### 3. 검증 단위 테스트
```powershell
.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_guide_documents.py -v
.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_guide.py -v
```

---

## 📋 완료 보고 규격 (작업 완료 후 사용자 제출 내용)
1. 수정한 파일 목록
2. Canonical schema 추가/변경 항목
3. GUIDE_SECTION_DEFINITIONS 변경사항
4. 새 binding path 목록
5. 새 반복 테이블 목록
6. 기존 호환성 유지 방식
7. 태양광 예시를 적용했을 때 생성되는 목차
8. 태양광 예시에서 각 정보가 어떤 Canonical path에 저장되는지
9. 정보가 없는 일반 CSV 입력 시 어떤 섹션이 자동으로 생략되는지
10. 단위 테스트 통과 결과
