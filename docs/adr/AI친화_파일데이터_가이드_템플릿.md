# AI친화·고가치 파일데이터 데이터셋 설명서

> 메타데이터 공통 정의: `AI친화_메타데이터_템플릿.json`·`.jsonld`·`.xml` (v2.3). 파일데이터는 `structure.data_category=file`, 오픈API는 `api`로 구분하며, 프로파일별 설명서의 값은 동일한 Canonical Metadata에서 가져옵니다.

> **문서 상태**: {{document.status}} | **발간일자**: {{document.generated_utc}} | **명세 버전**: v{{document.specification_version}}

---

## □ 1. 데이터셋 개요

| 항목 | 내용 |
| :--- | :--- |
| **데이터셋명** | {{dataset.title}} |
| **데이터 설명** | {{dataset.description}} |
| **구축 및 개방 목적** | {{dataset.purpose}} |
| **제공기관 / 소관기관** | {{dataset.publisher}} / {{dataset.creator}} |
| **데이터 특성·모달리티** | {{structure.traits}} |
| **전체 데이터 용량** | {{dataset.byte_size}} |
| **총 레코드 건수** | {{statistics.total_records}} 건 |
| **제공 파일 포맷** | {{structure.distribution.format}} (인코딩: {{structure.distribution.encoding}}) |
| **갱신주기 / 시간범위** | {{dataset.update_frequency}} / {{dataset.temporal.start}} ~ {{dataset.temporal.end}} |

---

## □ 2. 데이터 관리 메타데이터 (행안부 12대 네임스페이스)

| 표준 식별자 | 메타데이터 항목 | 정의 및 규격 | 바인딩 값 |
| :--- | :--- | :--- | :--- |
| `dct:title` | 데이터명 | 데이터셋 공식 명칭 (필수) | {{dataset.title}} |
| `dct:description` | 데이터 설명 | 데이터 내용 및 보유 목적 (필수) | {{dataset.description}} |
| `dct:references` | 관련법령 | 법령 참조 및 법적 근거 URL (필수) | {{dataset.legal_references}} |
| `dct:creator` | 소관기관 | 생산·관리 운영부서 (필수) | {{dataset.creator}} |
| `dct:publisher` | 제공기관 | 대외 배포·제공 기관 (필수) | {{dataset.publisher}} |
| `dcat:keyword` | 키워드 | 핵심 검색어 목록 (필수) | {{#dataset.keywords}}{{keyword}}, {{/dataset.keywords}} |
| `dcat:theme` | 주제분류체계 | 공공데이터 16대 표준 분류 (필수) | {{dataset.theme}} |
| `dct:identifier` | 고유식별자 | 영구 고유 식별자 URN (필수) | {{dataset.identifier}} |
| `dcat:contactPoint` | 담당자 연락처 | vCard 표준 연락 정보 (필수) | {{dataset.contact_point.name}} ({{dataset.contact_point.email}}) |
| `dct:language` | 언어 | ISO 639-1 언어 코드 (필수) | {{dataset.language}} |
| `dcat:byteSize` | 데이터 용량 | 파일 크기 (바이트 단위) | {{dataset.byte_size}} |
| `dcat:mediaType` | 미디어 타입 | 파일 MIME 타입 (필수) | {{dataset.media_type}} |
| `dct:temporal` | 시간범위 | 수집 대상 시간 범위 | {{dataset.temporal.start}} ~ {{dataset.temporal.end}} |
| `dct:spatial` | 공간범위 | 지리적 수집 영역 | {{dataset.spatial}} |
| `dct:license` | 적용 라이선스 | 이용허락 조건 URI (필수) | {{usage.license}} |
| `dct:rights` | 저작권 | 저작권 및 이용 권한 (필수) | {{usage.rights}} |

---

## □ 3. 데이터셋 구성 및 데이터사전

### 3.1 파일 구성 및 폴더 체계
* **폴더 체계**: `{{structure.distribution.folder_structure}}`
* 원천·라벨·파생·외부 연계·배포 자산은 `lineage.source_datasets`, `pipeline`, `artifacts`에서 확인된 항목만 표시한다. 확인되지 않은 포맷·파일 수·폴더는 생성하지 않는다.

### 3.2 시트·테이블 구성
* **레코드셋 ID**: `{{modality_specifications.tabular_numeric_metadata.record_set_id}}`
* **루트 타입**: `{{structure.root_type}}`

### 3.3 필드 데이터사전 (컬럼 정의서 - cr:Field 표준)
| 컬럼 물리명 | 컬럼 논리명 | 데이터 타입 | 필수 (PK) | 단위 | 허용 코드/범위 | 컬럼 설명 |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
{{#fields}}
| `{{name}}` | {{name_ko}} | {{data_type}} | {{required}} | {{unit}} | {{constraints}} | {{description}} |
{{/fields}}

### 3.4 코드·범주값 명세
* 도메인 코드 정의서 및 정규식 규칙 준수

### 3.5 데이터 유형별 추가 구조 (모달리티 특화 메타데이터)
* **이미지 (`image_metadata`)**: 가로 `{{modality_specifications.image_metadata.width}}`px, 세로 `{{modality_specifications.image_metadata.height}}`px, 장비 `{{modality_specifications.image_metadata.exif_make}}`
* **영상 (`video_metadata`)**: 해상도 `{{modality_specifications.video_metadata.width}}x{{modality_specifications.video_metadata.height}}`, 재생시간 `{{modality_specifications.video_metadata.duration}}`, 코덱 `{{modality_specifications.video_metadata.codec}}`
* **음성 (`audio_metadata`)**: 재생시간 `{{modality_specifications.audio_metadata.duration}}`, 샘플레이트 `{{modality_specifications.audio_metadata.sample_rate}}`Hz, 채널 `{{modality_specifications.audio_metadata.channels}}`

---

## □ 4. 데이터 구축·수집·가공 방법

### 4.1~4.7 수집 및 정제 공정도
| 단계 | 공정명 | 작업 내용 및 정제 규칙 | 산출물 |
| :---: | :--- | :--- | :--- |
{{#pipeline}}
| {{step}} | {{name}} | {{rules}} | {{output}} |
{{/pipeline}}

---

## □ 5. 데이터 계보 및 변경이력 (Data Lineage)

* **원천 데이터 출처**: {{lineage.source_datasets}}
* **수집 및 정제 이력**: {{lineage.preprocessing_history}}
* **결측·이상치 보정 방식**: {{lineage.imputation_method}}
* **버전 및 변경 노트**: v{{dataset.version_info.version}} ({{dataset.version_info.version_notes}})

---

## □ 6. 데이터 표준화 및 상호운용성

* **문자 인코딩**: `{{structure.distribution.encoding}}` (UTF-8 권장)
* **구분자 및 압축**: 구분자 `{{structure.distribution.delimiter}}`, 압축 `{{structure.distribution.compression}}`
* **오픈포맷 여부**: {{interoperability.is_open_format}}

---

## □ 7. 데이터 이용·배포·접근

* **배포 포맷**: {{structure.distribution.format}}
* **다운로드 URL**: [데이터 다운로드 바로가기]({{dataset.access_url}})
* **대표 웹페이지**: [공공데이터포털 상세]({{dataset.landing_page}})
* **적용 라이선스**: {{usage.license}} (상태: {{usage.status}})
* **저작권 및 이용권한**: {{usage.rights}} (상태: {{usage.status}})

---

## □ 8. 데이터 품질 (Quality)

### 8.1 책임있는 AI 메타데이터 (Responsible AI)
* **데이터 편향성 (`rai:dataBiases`)**: {{responsible_ai.data_biases}}
* **데이터 한계 (`rai:knownLimitations`)**: {{responsible_ai.known_limitations}}
* **결측치 정보 (`rai:dataCollectionMissingData`)**: {{responsible_ai.missing_data_info}}
* **품질 검증 정보 (`dqv:hasQualityAnnotation`)**: {{responsible_ai.quality_annotation}}

### 8.2 AI 친화 6대 품질지표 진단 결과
| 품질축 | 지표 정의 | 측정 점수 | 상태 | 진단 근거 및 산출 모수 |
| :--- | :--- | :---: | :---: | :--- |
| **완전성 (Completeness)** | 필수 데이터 결측치 부재율 | {{quality.metrics.completeness.score}}점 | {{quality.metrics.completeness.status}} | {{quality.metrics.completeness.evidence}} |
| **유효성 (Validity)** | 도메인, 형식 및 규칙 준수율 | {{quality.metrics.validity.score}}점 | {{quality.metrics.validity.status}} | {{quality.metrics.validity.evidence}} |
| **일관성 (Consistency)** | 포맷 및 표준 코드체계 일치율 | {{quality.metrics.consistency.score}}점 | {{quality.metrics.consistency.status}} | {{quality.metrics.consistency.evidence}} |
| **정확성 (Accuracy)** | 이상치(Outlier) 부재율 | {{quality.metrics.accuracy.score}}점 | {{quality.metrics.accuracy.status}} | {{quality.metrics.accuracy.evidence}} |
| **유일성 (Uniqueness)** | 기본키(PK) 중복 부재율 | {{quality.metrics.uniqueness.score}}점 | {{quality.metrics.uniqueness.status}} | {{quality.metrics.uniqueness.evidence}} |
| **적시성 (Timeliness)** | 갱신주기 준수 및 시의성 | {{quality.metrics.timeliness.score}}점 | {{quality.metrics.timeliness.status}} | {{quality.metrics.timeliness.evidence}} |

---

## □ 9. AI 활용성 (AI-Ready)

* **추천 AI Task**: {{ai.purpose}}
* **추천 학습 모델**: {{#ai.recommended_models}}{{model_name}}, {{/ai.recommended_models}}
* **권고 데이터 분할 비율**: 학습(Train: {{ai.split_ratio.train}}%) : 검증(Val: {{ai.split_ratio.validation}}%) : 시험(Test: {{ai.split_ratio.test}}%)
* **대용량 최적화 권고**: 청크 적용 {{ai.large_data_optimization.is_chunk_applied}}, Parquet 권고 {{ai.large_data_optimization.parquet_recommended}}, 파티셔닝 키 {{ai.large_data_optimization.partitioning_key}}
* **데이터 누출(Data Leakage) 주의**: 시계열/센서 데이터의 경우 과거-미래 셔플링 절대 금지

---

## □ 10. 데이터 관리체계 및 거버넌스

* **총괄 책임부서**: {{governance.managing_department}}
* **담당자 / 연락처**: {{governance.contact_point.name}} / {{governance.contact_point.phone}} ({{governance.contact_point.email}})
* **개인정보 포함 여부**: {{governance.privacy_security.contains_pii}}
* **비식별·보호조치**: {{governance.privacy_security.anonymization_method}} / {{governance.privacy_security.security_level}}

---

## □ 11. 기관 확인 및 발간 전 점검

* **검토 상태**: {{document.status}}
* **미검토/주의 항목**:
{{#reviewRequired}}
* [{{status}}] {{label}}: {{reason}} (조치: {{action}})
{{/reviewRequired}}

---

### [부록 A] 전체 필드 데이터사전
(본문 3.3절 참조)

### [부록 B] 상세 품질진단 결과표
(본문 8.2절 참조)

### [부록 C] 기계판독형 메타데이터 연계 파일
* `AI친화_메타데이터_템플릿.json`
* `AI친화_메타데이터_템플릿.xml`
* `AI친화_메타데이터_템플릿.jsonld`
* `AI친화_메타데이터_스키마.xsd` (행정연계 XML 유효성 검증용)
