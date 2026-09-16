# AI친화·고가치 OpenAPI 데이터 설명서

> 메타데이터 공통 정의: `AI친화_메타데이터_템플릿.json`·`.jsonld`·`.xml` (v2.3). 파일데이터는 `structure.data_category=file`, 오픈API는 `api`로 구분하며, 프로파일별 설명서의 값은 동일한 Canonical Metadata에서 가져옵니다.

> **문서 상태**: {{document.status}} | **발간일자**: {{document.generated_utc}} | **명세 버전**: v{{document.specification_version}}

---

## □ 1. API 데이터셋 개요

| 항목 | 내용 |
| :--- | :--- |
| **API명 (국문/영문)** | {{dataset.title}} / {{structure.api_specification.operations.0.operation_id}} |
| **API 설명** | {{dataset.description}} |
| **제공기관 / 소관기관** | {{dataset.publisher}} / {{dataset.creator}} |
| **데이터 내용** | {{dataset.purpose}} |
| **주요 활용 목적** | {{ai.purpose}} |
| **데이터 갱신주기** | {{dataset.update_frequency}} |
| **API 버전** | {{dataset.version_info.version}} |
| **기본 호출 Base URL** | `{{structure.api_specification.base_url}}` |

---

## □ 2. API 관리 메타데이터 (W3C DCAT / Dublin Core 표준)

| 표준 식별자 | 메타데이터 항목 | 정의 및 규격 | 바인딩 값 |
| :--- | :--- | :--- | :--- |
| `dct:title` | 데이터명 | API 공식 명칭 (필수) | {{dataset.title}} |
| `dct:description` | 데이터 설명 | API 구축 목적 및 범위 (필수) | {{dataset.description}} |
| `dct:creator` | 소관기관 | 생산·관리 운영부서명 (필수) | {{dataset.creator}} |
| `dct:publisher` | 제공기관 | 대외 배포·제공 기관 (필수) | {{dataset.publisher}} |
| `dct:references` | 관련법령 | 법령 참조 및 법적 근거 URL (필수) | {{dataset.legal_references}} |
| `dcat:keyword` | 키워드 | 검색 및 분류 키워드 (필수) | {{#dataset.keywords}}{{keyword}}, {{/dataset.keywords}} |
| `dcat:theme` | 주제분류체계 | 공공데이터 16대 표준 분류 (필수) | {{dataset.theme}} |
| `dct:identifier` | 고유식별자 | 영구 고유 식별자 URN (필수) | {{dataset.identifier}} |
| `dcat:contactPoint` | 담당자 연락처 | vCard 표준 연락 정보 (필수) | {{dataset.contact_point.name}} ({{dataset.contact_point.email}}) |
| `dct:language` | 언어 | ISO 639-1 언어 코드 (필수) | {{dataset.language}} |
| `dct:temporal` | 시간범위 | 데이터 수집/유효 기간 (권장) | {{dataset.temporal.start}} ~ {{dataset.temporal.end}} |
| `dct:spatial` | 공간범위 | 지리적 적용 범위 (권장) | {{dataset.spatial}} |
| `dct:license` | 라이선스 | 적용 라이선스 URI (필수) | {{usage.license}} |
| `dct:rights` | 저작권 | 저작권 및 이용 권한 (필수) | {{usage.rights}} |

---

## □ 3. API 서비스 및 접근 명세

### 3.1 서비스 기본정보
* **서비스명(국문)**: {{dataset.title}}
* **서비스명(영문)**: {{structure.api_specification.base_url}}
* **Base URL**: `{{structure.api_specification.base_url}}`
* **API 버전**: v{{dataset.version_info.version}}
* **서비스 시작일 / 최종 수정일**: {{dataset.version_info.issued}} / {{dataset.version_info.modified}}
* **제공기관 / 담당자**: {{dataset.publisher}} / {{dataset.contact_point.name}} ({{dataset.contact_point.phone}})

### 3.2 인터페이스
* **계약 문서**: {{structure.api_specification.specification_url}}
* **계약 검토 상태**: {{structure.api_specification.contract_status}}
* HTTP Method·응답 형식·인코딩은 확인된 `operations`와 `data_formats`에서만 표시한다.

### 3.3 인증·보안
* **인증 방식**: {{structure.api_specification.auth_type}}
* **인증 설명**: {{structure.api_specification.authentication_description}}
* **접근 권한**: {{usage.access_rights}}
* 실제 인증키·토큰은 문서와 예제에 포함하지 않는다.

### 3.4 응답 형식
* 응답 형식은 기관 계약에서 확인된 `data_formats`만 표시한다.

---

## □ 4. API 기능 목록 (Operations)

| No. | 기능 ID | 기능명 (한글) | Endpoint URI | HTTP Method | 기능 설명 |
| :---: | :--- | :--- | :--- | :---: | :--- |
{{#structure.api_specification.operations}}
| 1 | `{{operation_id}}` | {{operation_name}} | `{{endpoint_path}}` | `{{http_method}}` | {{description}} |
{{/structure.api_specification.operations}}

---

## □ 5. API 기능별 상세 명세

{{#structure.api_specification.operations}}
### 5.1 기능 개요
* **기능 ID**: `{{operation_id}}`
* **기능명**: {{operation_name}}
* **Endpoint**: `{{structure.api_specification.base_url}}{{endpoint_path}}`
* **Method**: `{{http_method}}`
* **설명**: {{description}}

### 5.2 요청(Request) 파라미터 명세
| 영문명 | 국문명 | 위치 | 데이터 타입 | 길이 | 필수 여부 | 허용값 | 기본값 | 샘플값 | 설명 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :--- | :--- |
{{#request_parameters}}
| `{{param_name}}` | {{name_ko}} | {{location}} | {{data_type}} | - | {{required}} | - | - | `{{sample_value}}` | {{description}} |
{{/request_parameters}}

### 5.3 응답(Response) 필드 명세
| JSON/XML Path | 영문명 | 국문명 | 데이터 타입 | Cardinality | 필수 여부 | 코드/허용값 | 샘플값 | 설명 |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
{{#response_parameters}}
| `{{path}}` | `{{param_name}}` | {{name_ko}} | {{data_type}} | 1 | {{required}} | - | `{{sample_value}}` | {{description}} |
{{/response_parameters}}

### 5.4 정상 응답 예제
계약에서 제공되고 인증정보·개인정보를 제거한 예제만 표시한다.
* **XML 응답 예시**:
```xml
{{{sample_messages.xml_sample}}}
```

* **JSON 응답 예시**:
```json
{{{sample_messages.json_sample}}}
```
{{/structure.api_specification.operations}}

---

## □ 6. API 데이터 구조 및 스키마

* **Root Structure**: `{{structure.root_type}}`
* **실제 페이로드 경로**: `{{structure.api_specification.payload_path}}`
* **경로 표현 규칙**: `{{structure.api_specification.path_syntax}}`
* **Pagination 계약**: {{structure.api_specification.pagination}}
* **XML 네임스페이스**: {{structure.api_specification.namespaces}}
* `AI친화_메타데이터_스키마.xsd`는 생성 메타데이터 XML의 검증 계약이며 원천 API 응답 스키마로 사용하지 않는다.

---

## □ 7. API 데이터 품질 (Quality)

### 7.1 품질 메타데이터 요약
* **종합 품질 점수**: **{{quality.overall_score}}점** (100점 만점 기준)

### 7.2~7.7 공통 6대 품질축 진단 결과
| 품질축 | 지표 정의 | 측정 점수 | 상태 | 진단 근거 및 산출 모수 |
| :--- | :--- | :---: | :---: | :--- |
| **완전성 (Completeness)** | 필수 응답 필드 결측 부재율 | {{quality.metrics.completeness.score}}점 | {{quality.metrics.completeness.status}} | {{quality.metrics.completeness.evidence}} |
| **유효성 (Validity)** | 스키마 및 도메인 정규식 규칙 준수율 | {{quality.metrics.validity.score}}점 | {{quality.metrics.validity.status}} | {{quality.metrics.validity.evidence}} |
| **일관성 (Consistency)** | 포맷(날짜 ISO 8601 등) 및 코드 일치율 | {{quality.metrics.consistency.score}}점 | {{quality.metrics.consistency.status}} | {{quality.metrics.consistency.evidence}} |
| **정확성 (Accuracy)** | 이상치(Outlier) 및 비정상 응답 부재율 | {{quality.metrics.accuracy.score}}점 | {{quality.metrics.accuracy.status}} | {{quality.metrics.accuracy.evidence}} |
| **유일성 (Uniqueness)** | PK 및 식별자 중복 레코드 부재율 | {{quality.metrics.uniqueness.score}}점 | {{quality.metrics.uniqueness.status}} | {{quality.metrics.uniqueness.evidence}} |
| **적시성 (Timeliness)** | 갱신 주기 준수 및 데이터 시의성 | {{quality.metrics.timeliness.score}}점 | {{quality.metrics.timeliness.status}} | {{quality.metrics.timeliness.evidence}} |

추가 API 품질은 `quality.trait_checks`에 측정 범위·근거·상태가 있는 항목만 표시한다.

---

## □ 8. API 성능·운영

* **호출 제한**: {{structure.api_specification.rate_limit}}
* 그 밖의 응답시간·응답 크기·TPS·Timeout·운영시간·점검 정책은 기관 계약에 근거가 있을 때 `canonicalItems`에서 표시한다. 미확인 값은 `REVIEW_REQUIRED`이다.

---

## □ 9. API 오류 및 예외 (Error Codes)

### 9.1 HTTP 상태코드
기관 계약에서 확인된 상태코드와 의미만 표시한다.

### 9.2 공통 API 및 제공기관 오류 코드표
| 오류코드 | HTTP Status | 오류명 (메시지) | 발생조건 | 대응 및 조치방법 |
| :---: | :---: | :--- | :--- | :--- |
{{#structure.api_specification.error_codes}}
| `{{code}}` | {{http_status}} | `{{message}}` | 파라미터 및 인증 상태 오류 | {{description}} |
{{/structure.api_specification.error_codes}}

---

## □ 10. 데이터 표준화 및 상호운용성

* **표준 데이터 타입**: XSD 및 JSON Schema 표준 타입 준수 (`string`, `integer`, `dateTime` 등)
* **표준 네임스페이스**: `dcat`, `dct`, `vcard`, `xsd`, `api` W3C 표준 네임스페이스 연계
* **계약 명세 연계**: {{structure.api_specification.specification_url}}

---

## □ 11. AI 활용성 (AI-Ready)

* **주요 AI Task**: {{ai.purpose}}
* **추천 모델**: {{#ai.recommended_models}}{{model_name}}, {{/ai.recommended_models}}
* **활용 시나리오**: 확인되거나 AI 초안 상태가 명시된 `ai.scenarios`만 표시한다.

---

## □ 12. AI Agent·기계 접근 고려사항 (MCP 연계)

* **API Discoverability**: 확인된 엔드포인트 기능과 제약조건을 기계 판독 메타데이터로 제공한다.
* **AI Agent 연계**: 별도 도구 호출 명세가 제공된 경우에만 지원 여부를 표시한다.
* **부분조회 및 페이징**: {{structure.api_specification.pagination}}

---

## □ 13. API 생애주기 및 변경이력

* **현재 버전**: {{dataset.version_info.version}}
* **등록일 / 수정일**: {{dataset.version_info.issued}} / {{dataset.version_info.modified}}
* **변경 내용**: {{dataset.version_info.version_notes}}

---

## □ 14. API 관리체계 및 거버넌스

* **운영 책임자**: {{governance.managing_department}}
* **담당자 / 연락처**: {{governance.contact_point.name}} / {{governance.contact_point.phone}} ({{governance.contact_point.email}})
* **개인정보 포함 여부**: {{governance.privacy_security.contains_pii}}
* **비식별·보호조치**: {{governance.privacy_security.anonymization_method}} / {{governance.privacy_security.security_level}}

---

## □ 15. 기관 확인 및 발간 전 점검

* **검토 상태**: {{document.status}}
* **미검토/주의 항목**:
{{#reviewRequired}}
* [{{status}}] {{label}}: {{reason}} (조치: {{action}})
{{/reviewRequired}}

---

### [부록 A] 전체 요청 파라미터 사전
(본문 5.2절 참조)

### [부록 B] 전체 응답 데이터사전
(본문 5.3절 참조)

### [부록 C] 오류코드 명세
(본문 9.2절 참조)

### [부록 D] 요청·응답 Sample
(본문 5.4, 5.5절 참조)

### [부록 E] 기계판독 메타데이터 연계 파일
* `AI친화_메타데이터_템플릿.json`
* `AI친화_메타데이터_템플릿.xml`
* `AI친화_메타데이터_템플릿.jsonld`
* `AI친화_메타데이터_스키마.xsd` (행정연계 XML 유효성 검증용)
