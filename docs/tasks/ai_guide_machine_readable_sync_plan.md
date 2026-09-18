# [작업 명세서] 기계판독형 메타데이터 5종 동기화 및 템플릿 바인딩 카탈로그 구축 (Next-Step)

## 📌 선행 조건 (Prerequisite)
본 작업은 [ai_guide_generalization_plan.md](ai_guide_generalization_plan.md)의 Step 1~Step 5(Canonical Schema 확장 및 파이썬 바인딩/렌더링 엔진 구축)가 **완료된 상태에서 실행**한다.

---

## 📌 실행 규칙 (Agent Execution Protocol)
1. 에이전트는 본 명세서의 **Step 1부터 Step 4까지 순차적으로 실행**한다.
2. 사용자가 **사람이 읽는 문서 템플릿(`.md`, `.docx`, `.hwpx`)을 직접 수정할 예정**이므로, 에이전트는 문서 서식 파일을 임의로 훼손하지 말고 **기계판독형 포맷 5종(`.xsd`, `.xml`, `.jsonld`, `.ttl`, `.template.json`)과 직렬화 엔진(`exchange.py`)에만 집중**한다.
3. 각 Step 완료 시 명시된 검증 스크립트(lxml XSD 검증, rdflib TTL 검증 등)를 실행하여 **100% 통과(PASS)**를 확인한다.
4. 사용자에게 묻지 않고 루프를 자율 완결하며, 완료 후 사용자가 문서 템플릿 수정 시 바로 참고할 수 있는 **플레이스홀더 바인딩 참조 가이드(`docs/guides/ai_guide_template_binding_reference.md`)**를 생성한다.

---

### [x] Step 1. XML 스키마(`ai_ready_metadata_schema.xsd`) 및 XML 템플릿(`ai_ready_metadata_template.xml`) 동기화

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_metadata_schema.xsd`
  - `apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_metadata_template.xml`

#### 2. 상세 구현 요구사항
1. **`ai_ready_metadata_schema.xsd` 확장**:
   - `xs:complexType name="ProcessingType"` 정의:
     - `integration` (`ProcessingIntegrationType`)
     - `derived_fields` (`DerivedFieldsType` -> `derived_field` 복수 요소)
     - `missing_value_processing` (`MissingValueProcessingType` -> `rule` 복수 요소)
     - `outlier_processing` (`OutlierProcessingType` -> `rule` 복수 요소)
     - `quality_flags` (`QualityFlagsType` -> `flag` 복수 요소)
   - 최상위 메타데이터 요소 시퀀스 내에 `<xs:element name="processing" type="ProcessingType" minOccurs="0"/>` 선언.
   - `FieldType` 요소에 `value_origin`, `derivation_ref`, `missing_processing_ref`, `quality_flag_ref` 속성/요소 추가.
   - `AIType` 요소에 `recommended_features`, `time_series_characteristics`, `usage_risks` 요소 추가.
2. **`ai_ready_metadata_template.xml` 템플릿 확장**:
   - Canonical `processing` 객체와 매핑되는 XML 마커 작성:
     - `<!-- {{#processing.derived_fields}} -->` 블록을 활용한 `<derived_field>` 반복 템플릿 노드
     - `<!-- {{#processing.missing_value_processing}} -->` 결측 보정 템플릿 노드
     - `<!-- {{#processing.quality_flags}} -->` 품질 플래그 템플릿 노드
   - `fields/field` XML 노드에 `value_origin="{{field.value_origin}}"` 및 `quality_flag_ref` 마커 주입.

#### 3. 검증 명령어
```powershell
.venv\Scripts\python.exe -c "from lxml import etree; schema=etree.XMLSchema(file='apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_metadata_schema.xsd'); print('XSD Schema valid!')"
```

---

### [x] Step 2. RDF/Turtle 온톨로지(`ontology.ttl`) 어휘 정의 확장

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/data/ai_guide/templates/ontology.ttl`

#### 2. 상세 구현 요구사항
1. W3C 표준(PROV-O, DQV, DCAT)에 부합하는 신규 클래스 및 속성 트리플 정의:
   - 클래스:
     - `aig:Processing` (rdfs:subClassOf prov:Activity)
     - `aig:DerivedField` (rdfs:subClassOf aig:Field)
     - `aig:MissingValueProcessing` (rdfs:subClassOf prov:Activity)
     - `aig:QualityFlag` (rdfs:subClassOf dqv:QualityAnnotation)
   - 속성(Object/Datatype Properties):
     - `aig:derivationType` (aig:DerivedField -> xsd:string)
     - `aig:sourceField` (aig:DerivedField -> aig:Field)
     - `aig:valueOrigin` (aig:Field -> xsd:string: observed, derived, imputed, estimated)
     - `aig:imputationMethod` (aig:MissingValueProcessing -> xsd:string)
     - `aig:qualityFlagField` (aig:MissingValueProcessing -> aig:Field)
     - `aig:flagValueMeaning` (aig:QualityFlag -> xsd:string)
2. 온톨로지 네임스페이스 및 프리픽스 정합성 유지 (`aig:`, `dcat:`, `dqv:`, `prov:` 등).

#### 3. 검증 명령어
```powershell
.venv\Scripts\python.exe -c "import rdflib; g=rdflib.Graph(); g.parse('apps/api/src/synthetic_api/data/ai_guide/templates/ontology.ttl', format='turtle'); print(f'Ontology valid! Triples: {len(g)}')"
```

---

### [x] Step 3. JSON-LD 템플릿(`ai_ready_metadata_template.jsonld`) 및 직렬화 엔진(`exchange.py`) 확장

#### 1. 목표 및 대상 파일
- **수정 대상 파일**:
  - `apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_metadata_template.jsonld`
  - `apps/api/src/synthetic_api/application/services/ai_guide_document/exchange.py`

#### 2. 상세 구현 요구사항
1. **`ai_ready_metadata_template.jsonld` 확장**:
   - `@context`에 `processing`, `integration`, `derived_fields`, `missing_value_processing`, `quality_flags`, `value_origin` 매핑 정의 (`ontology.ttl` URI 기반).
   - `@graph` 내에 `processing` 관련 노드 구조 및 반복 바인딩 템플릿 추가.
2. **`exchange.py` (직렬화 로직 동기화)**:
   - `xml_output(model, contract)`:
     - `ai_ready_metadata_template.xml`을 파싱하여 모델의 `processing` 데이터를 XML 노드로 정상 전개하도록 보장.
     - 최종 생성된 XML 트리가 `ai_ready_metadata_schema.xsd` 검증을 완벽하게 통과(validate)하는지 확인.
   - `jsonld_output(model, contract)`:
     - Canonical 모델의 `processing` 블록이 누락 없이 유효한 JSON-LD 노드로 투영되도록 보장.

#### 3. 검증 명령어
```powershell
.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_guide_documents.py -k "test_xml or test_jsonld or test_exchange" -v
```

---

### [x] Step 4. 사용자를 위한 템플릿 바인딩 참조 카탈로그(`binding_reference.md`) 작성

#### 1. 목표 및 생성 파일
- **신규 생성 파일**:
  - `docs/guides/ai_guide_template_binding_reference.md`

#### 2. 상세 구현 요구사항
사용자가 직접 Markdown(`ai_ready_public_data_guide_template.md`), Word(`.docx`), 한글(`.hwpx`) 템플릿을 수정할 때 즉시 복사하여 사용할 수 있도록, 시스템이 지원하는 모든 Mustache 태그 및 바인딩 키를 일목요연하게 정리한 레퍼런스 문서를 생성한다.

반드시 포함할 내용:
1. **신규 12개 구축관리 절 & 8개 AI 절별 권장 바인딩 태그**:
   - 데이터 연계/결합: `{{#integrations}} ... {{description}}, {{method}}, {{join_keys}} ... {{/integrations}}`
   - 파생 필드: `{{#derivedFields}} ... {{field_name}}, {{derivation_type}}, {{source_fields}}, {{method}}, {{formula_or_rule}} ... {{/derivedFields}}`
   - 결측 처리: `{{#missingValueRules}} ... {{target_field_ids}}, {{method}}, {{method_description}}, {{quality_flag_field}} ... {{/missingValueRules}}`
   - 품질 플래그: `{{#qualityFlags}} ... {{flag_field}}, {{description}}, {{#values}}{{code}}: {{meaning}}{{/values}} ... {{/qualityFlags}}`
   - AI 추천 변수: `{{#aiRecommendedFeatures}} ... {{name}}, {{role}}, {{importance}} ... {{/aiRecommendedFeatures}}`
2. **컬럼별 단일 필드 속성 키**:
   - `{{field.value_origin}}`, `{{field.derivation_ref}}`, `{{field.quality_flag_ref}}` 등
3. **조건부 숨김 처리(`prune_blocks`) 규칙 안내**:
   - 값이 없을 때(`NOT_APPLICABLE`) 섹션이 자동으로 접히는 조건 정리.

---

## 📋 완료 보고 규격
작업 완료 후 다음 4가지를 보고할 것:
1. 수정한 기계판독형 파일 5종 목록 및 변경 내역 요약
2. XSD 및 RDFLib 온톨로지 문법 유효성 검증 통과 결과
3. XML / JSON-LD 직렬화 회귀 테스트 결과
4. 사용자용 `docs/guides/ai_guide_template_binding_reference.md` 파일 생성 경로 및 주요 바인딩 키 요약
