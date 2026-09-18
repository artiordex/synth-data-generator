# {{guide.title}}

{{dataset.title}}

| 문서 정보 | 내용 |
| :--- | :--- |
| 데이터셋 문서 제목 | {{dataset.title}} |
| 제공기관 | {{dataset.publisher}} |
| 문서 생성 시각 | {{document.generated_utc}} |
| 문서 검토 상태 | {{document.review_notice}} |

## 머리말

{{guide.preamble}}

## {{guide.sections.dataset_overview.number}}. {{guide.sections.dataset_overview.title}}

### {{guide.sections.dataset_overview.children.basic_info.number}} {{guide.sections.dataset_overview.children.basic_info.title}}

| 항목 | 표준 속성 | 내용 |
| :--- | :--- | :--- |
| 데이터셋 식별자 | dct:identifier | {{dataset.identifier}} |
| 데이터셋명 | dct:title | {{dataset.title}} |
| 제공기관 | dct:publisher | {{dataset.publisher}} |
| 소관부서 | dct:creator | {{dataset.creator}} |
| 총괄 운영부서 | governance:managingDepartment | {{governance.managing_department}} |
| 담당자 | dcat:contactPoint | {{dataset.contact_point.name}} |
| 담당자 이메일 | vcard:hasEmail | {{dataset.contact_point.email}} |
| 담당자 연락처 | vcard:hasTelephone | {{dataset.contact_point.phone}} |
| 등록일 | dct:issued | {{dataset.version_info.issued}} |
| 수정일 | dct:modified | {{dataset.version_info.modified}} |

### {{guide.sections.dataset_overview.children.introduction.number}} {{guide.sections.dataset_overview.children.introduction.title}}

| 항목 | 내용 |
| :--- | :--- |
| 데이터 설명 | {{dataset.description}} |
| 시간 범위 시작 | {{dataset.temporal.start}} |
| 시간 범위 종료 | {{dataset.temporal.end}} |
| 공간·대상 범위 | {{dataset.spatial}} |

### {{guide.sections.dataset_overview.children.source_purpose.number}} {{guide.sections.dataset_overview.children.source_purpose.title}}

| 항목 | 내용 |
| :--- | :--- |
| 원천 데이터 | {{lineage.source_datasets}} |
| 연계 데이터 | {{dataset.relations}} |
| 관련 법령·근거 | {{dataset.legal_references}} |
| 구축·개방 목적 | {{dataset.purpose}} |

### {{guide.sections.dataset_overview.children.coverage.number}} {{guide.sections.dataset_overview.children.coverage.title}}

| 항목 | 내용 |
| :--- | :--- |
| 제공 유형 | {{structure.data_category}} |
| 루트 구조 | {{structure.root_type}} |
| 미디어 유형 | {{dataset.media_type}} |
| 데이터 규모(바이트) | {{dataset.byte_size}} |
| 레코드 수 | {{statistics.total_records}} |
| 필드 수 | {{statistics.total_fields}} |
| 버전 | {{dataset.version_info.version}} |
| 버전 설명 | {{dataset.version_info.version_notes}} |

### {{guide.sections.dataset_overview.children.keywords_classification.number}} {{guide.sections.dataset_overview.children.keywords_classification.title}}

| 번호 | 키워드 |
| :--- | :--- |
{{#dataset.keywords}}
| {{@number}} | {{keyword}} |
{{/dataset.keywords}}

| 분류 항목 | 내용 |
| :--- | :--- |
| 주제분류명 | {{dataset.theme_label}} |
| 주제분류 식별자 | {{dataset.theme}} |
| 데이터 언어 | {{dataset.language}} |

### {{guide.sections.dataset_overview.children.services.number}} {{guide.sections.dataset_overview.children.services.title}}

| 항목 | 내용 |
| :--- | :--- |
| 대표 페이지 | {{dataset.landing_page}} |
| 데이터 접근 URL | {{dataset.access_url}} |
{{#ai.scenarios}}
| 활용 시나리오: {{title}} | {{description}} |
{{/ai.scenarios}}

## {{guide.sections.management.number}}. {{guide.sections.management.title}}

### {{guide.sections.management.children.sources_collection.number}} {{guide.sections.management.children.sources_collection.title}}

| ?? | ?? |
| :--- | :--- |
| ?? ?? | {{lineage.collection_process}} |
| ?? ??? | {{lineage.source_datasets}} |
| ?? ????? | {{analysis.limitations}} |

### {{guide.sections.management.children.integration.number}} {{guide.sections.management.children.integration.title}}

{{#integrations}}
| ?? | ?? |
| :--- | :--- |
| ?? ?? | {{description}} |
| ?? ?? | {{method}} |
| ?? ?? | {{join_type}} |
| ?? ? | {{join_keys}} |
| ?? ?? | {{temporal_alignment}} |
| ?? ?? | {{spatial_alignment}} |
| ?? ???? | {{source_dataset_ids}} |
| ?? ??? | {{output_description}} |
| ?? ?? | {{limitations}} |
{{/integrations}}

### {{guide.sections.management.children.cleaning.number}} {{guide.sections.management.children.cleaning.title}}

| ?? | ?? |
| :--- | :--- |
| ?? ?? | {{lineage.preprocessing_history}} |
| ?? ?? ?? | {{responsible_ai.missing_data_info}} |
| ?? ?? ?? | ??? ?? ???? ??? ??? ?? ?? ?? |

### {{guide.sections.management.children.derivation_transformation.number}} {{guide.sections.management.children.derivation_transformation.title}}

{{#derivedFields}}
| ?? ID | ??? | ?? | ?? ?? | ?? | ?????? | ?? ??? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| {{field_id}} | {{field_name}} | {{derivation_type}} | {{source_fields}} | {{method}} | {{formula_or_rule}} | {{reproducible}} |
{{/derivedFields}}
### {{guide.sections.management.children.missing_outlier_processing.number}} {{guide.sections.management.children.missing_outlier_processing.title}}

{{#missingValueRules}}
| ?? ?? | ?? ?? ? | ?? ?? | ?? ?? | ?? ?? | ?? ??? | ?? ?? |
| :--- | ---: | ---: | :--- | :--- | :--- | :--- |
| {{target_field_ids}} | {{detected_missing_count}} | {{detected_missing_ratio}} | {{method}} | {{method_description}} | {{quality_flag_field}} | {{original_value_preserved}} |
{{/missingValueRules}}
{{#outlierRules}}
| ??? ?? | ?? ?? | ??? | ?? | ?? ?? | ?? ?? | ?? ??? |
| :--- | :--- | :--- | :--- | :--- | ---: | :--- |
| {{target_field_ids}} | {{detection_method}} | {{threshold}} | {{action}} | {{replacement_method}} | {{affected_count}} | {{quality_flag_field}} |
{{/outlierRules}}

### {{guide.sections.management.children.processing_validation.number}} {{guide.sections.management.children.processing_validation.title}}

| ?? | ??? | ????? | ??? |
| :--- | :--- | :--- | :--- |
{{#pipeline}}
| {{step}} | {{name}} | {{rules}} | {{output}} |
{{/pipeline}}

| ?? ?? | ?? | ?? |
| :--- | :--- | :--- |
| ?? ?? ?? | {{responsible_ai.quality_annotation}} | {{analysis.limitations}} |
| ?? ?? ?? | {{document.review_status}} | {{document.review_notice}} |

### {{guide.sections.management.children.quality.number}} {{guide.sections.management.children.quality.title}}

| ?? ?? | ?? | ?? |
| :--- | :--- | :--- |
| ??? ??? | {{quality.metrics.completeness.score}} | {{quality.metrics.completeness.evidence}} |
| ??? | {{quality.metrics.validity.score}} | {{quality.metrics.validity.evidence}} |
| ??? | {{quality.metrics.consistency.score}} | {{quality.metrics.consistency.evidence}} |
| ??? | {{quality.metrics.accuracy.score}} | {{quality.metrics.accuracy.evidence}} |
| ??? | {{quality.metrics.uniqueness.score}} | {{quality.metrics.uniqueness.evidence}} |
| ??? | {{quality.metrics.timeliness.score}} | {{quality.metrics.timeliness.evidence}} |

### {{guide.sections.management.children.quality_flags.number}} {{guide.sections.management.children.quality_flags.title}}

{{#qualityFlags}}
| ??? ?? | ?? | ?? ?? | ?? | ??? | ?? | ? ?? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{{#values}}
| {{flag_field}} | {{description}} | {{target_fields}} | {{code}} | {{name}} | {{meaning}} | {{value_origin}} |
{{/values}}
{{/qualityFlags}}

### {{guide.sections.management.children.metadata_interoperability.number}} {{guide.sections.management.children.metadata_interoperability.title}}

| ?? | ?? |
| :--- | :--- |
| ?? ??? ?? | {{interoperability.standard_schema_applied}} |
| ??? ???URI | {{interoperability.schema_format}} / {{interoperability.schema_uri}} |
| ?? ?? | {{interoperability.code_systems}} |
| ??? ?? | {{interoperability.identifier_policy}} |

### {{guide.sections.management.children.lineage_changes.number}} {{guide.sections.management.children.lineage_changes.title}}

| ?? | ?? |
| :--- | :--- |
| ????? ??? | {{lineage.source_datasets}} / {{dataset.relations}} |
| ?? ?? | {{lineage.preprocessing_history}} |
| ?? ????? | {{dataset.legal_references}} |
| ????? ?? | {{dataset.version_info.version}} / {{dataset.version_info.version_notes}} |

### {{guide.sections.management.children.privacy_deidentification.number}} {{guide.sections.management.children.privacy_deidentification.title}}

| ?? | ?? |
| :--- | :--- |
| ???? ?? ?? | {{governance.privacy_security.contains_pii}} |
| ???? ?? | {{governance.privacy_security.anonymization_method}} |
| ?? ?? | {{governance.privacy_security.security_level}} |
| ????? ?? | {{governance.privacy_security.retention_period}} / {{governance.privacy_security.deletion_method}} |

### {{guide.sections.management.children.rights_conditions.number}} {{guide.sections.management.children.rights_conditions.title}}

| ?? | ?? |
| :--- | :--- |
| ???? | {{usage.license}} |
| ???????? | {{usage.rights}} |
| ?? ?? | {{usage.access_rights}} |
| ?? ????? ?? | {{usage.access_restrictions}} |
| ?? ?? | {{usage.attribution}} |
| ?? ?? | {{usage.pricing}} |

{{#guide.file}}
## {{guide.sections.file_distribution.number}}. {{guide.sections.file_distribution.title}}

### {{guide.sections.file_distribution.children.file_info.number}} {{guide.sections.file_distribution.children.file_info.title}}

| 파일명 | 형식 | 크기(바이트) | 관측 레코드 수 |
| :--- | :--- | ---: | ---: |
{{#fileSources}}
| {{name}} | {{format}} | {{byte_size}} | {{observed_records}} |
{{/fileSources}}

### {{guide.sections.file_distribution.children.composition_format.number}} {{guide.sections.file_distribution.children.composition_format.title}}

| 항목 | 내용 |
| :--- | :--- |
| 파일 형식 | {{structure.distribution.format}} |
| 구분자 | {{structure.distribution.delimiter}} |
| 압축 방식 | {{structure.distribution.compression}} |
| 파일 구성 | {{structure.distribution.folder_structure}} |
| 문자 인코딩 | {{structure.distribution.encoding}} |

### {{guide.sections.file_distribution.children.data_structure.number}} {{guide.sections.file_distribution.children.data_structure.title}}

| 항목 | 내용 |
| :--- | :--- |
| 루트·중첩 구조 | {{structure.root_type}} |
| 레코드·필드 규모 | {{statistics.total_records}} / {{statistics.total_fields}} |
| 데이터 특성 | {{structure.traits}} |
| 데이터 미디어 유형 | {{dataset.media_type}} |

### {{guide.sections.file_distribution.children.column_definition.number}} {{guide.sections.file_distribution.children.column_definition.title}}

| 번호 | 한글 컬럼명 | 영문 컬럼명 | 설명 | 단위 |
| ---: | :--- | :--- | :--- | :--- |
{{#fileFields}}
| {{@number}} | {{name_ko}} | {{name}} | {{description}} | {{unit}} |
{{/fileFields}}

### {{guide.sections.file_distribution.children.types_constraints.number}} {{guide.sections.file_distribution.children.types_constraints.title}}

| 한글 컬럼명 | 영문 컬럼명 | 데이터 타입 | 필수 | Null 허용 | 기본키 | 카디널리티 | 제약조건 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{{#fileFields}}
| {{name_ko}} | {{name}} | {{data_type}} | {{required}} | {{nullable}} | {{is_pk}} | {{cardinality}} | {{constraints}} |
{{/fileFields}}

### {{guide.sections.file_distribution.children.codes_allowed_values.number}} {{guide.sections.file_distribution.children.codes_allowed_values.title}}

| 영문 컬럼명 | 코드 목록·허용값 | 코드체계 URI |
| :--- | :--- | :--- |
{{#fileFields}}
| {{name}} | {{code_list}} | {{code_system_uri}} |
{{/fileFields}}

### {{guide.sections.file_distribution.children.sample_data.number}} {{guide.sections.file_distribution.children.sample_data.title}}

| 한글 컬럼명 | 영문 컬럼명 | 샘플 값 |
| :--- | :--- | :--- |
{{#fileFields}}
| {{name_ko}} | {{name}} | {{sample_values}} |
{{/fileFields}}

### {{guide.sections.file_distribution.children.field_statistics.number}} {{guide.sections.file_distribution.children.field_statistics.title}}

| 영문 컬럼명 | Null 건수 | 빈 문자열 건수 | 고유값 수 | 최소값 | 최대값 |
| :--- | ---: | ---: | ---: | :--- | :--- |
{{#fileFields}}
| {{name}} | {{statistics.null_count}} | {{statistics.empty_count}} | {{statistics.distinct_count}} | {{statistics.min_value}} | {{statistics.max_value}} |
{{/fileFields}}

### {{guide.sections.file_distribution.children.loading_usage.number}} {{guide.sections.file_distribution.children.loading_usage.title}}

| 항목 | 내용 |
| :--- | :--- |
| 갱신주기 | {{dataset.update_frequency}} |
| 접근 URL | {{dataset.access_url}} |
| 다운로드 URL | {{structure.download_url}} |
| 제공 포맷 | {{usage.distribution_formats}} |
| 적재·이용 유의사항 | {{usage.access_restrictions}} / {{document.review_notice}} |
{{/guide.file}}

{{#guide.api}}
## {{guide.sections.api_service.number}}. {{guide.sections.api_service.title}}

### {{guide.sections.api_service.children.service_info.number}} {{guide.sections.api_service.children.service_info.title}}

| 항목명 | 표준 속성 | 구분 | 작성 내용 |
| :--- | :--- | :--- | :--- |
| 서비스명 | dct:title | 필수 | {{dataset.title}} |
| 서비스 설명 | dct:description | 필수 | {{dataset.description}} |
| 기본 URL | dcat:endpointURL | 필수 | {{structure.api_specification.base_url}} |
| 인터페이스 표준 | dcat:endpointDescription | 필수 | {{structure.api_specification.interface_type}} |
| HTTP 메서드 | 내부 API 계약 | 필수 | {{structure.api_specification.http_methods}} |
| 교환 데이터 형식 | dcat:mediaType | 필수 | {{structure.api_specification.mime_types}} |
| 문자 인코딩 | 내부 API 계약 | 권장 | {{structure.api_specification.character_encoding}} |
| HTTPS 사용 여부 | 내부 API 계약 | 권장 | {{structure.api_specification.https}} |
| 서비스 접근 권한 | dct:accessRights | 필수 | {{structure.api_specification.access_rights}} |
| 서비스 명세 URL | dcat:endpointDescription | 권장 | {{structure.api_specification.specification_url}} |
| API 버전 | owl:versionInfo | 권장 | {{structure.api_specification.version}} |
| 응답 데이터 경로 | 내부 API 계약 | 필수 | {{structure.api_specification.payload_path}} |

### {{guide.sections.api_service.children.authentication_conditions.number}} {{guide.sections.api_service.children.authentication_conditions.title}}

| 항목 | 내용 |
| :--- | :--- |
| 인증 유형 | {{structure.api_specification.auth_type}} |
| 인증 설명 | {{structure.api_specification.authentication_description}} |
| 호출 제한 | {{structure.api_specification.rate_limit}} |
| 페이지네이션 | {{structure.api_specification.pagination}} |
| 접근 권한·이용 조건 | {{usage.access_rights}} / {{usage.access_restrictions}} |

### {{guide.sections.api_service.children.functions_endpoints.number}} {{guide.sections.api_service.children.functions_endpoints.title}}

| 기능명 | 기능 유형 | 기능 설명 | HTTP 메서드 | Endpoint | 지원 형식 |
| :--- | :--- | :--- | :--- | :--- | :--- |
{{#structure.api_specification.operations}}
| {{operation_name}} | {{operation_type}} | {{description}} | {{http_method}} | {{endpoint_path}} | {{data_formats}} |
{{/structure.api_specification.operations}}

### {{guide.sections.api_service.children.request_parameters.number}} {{guide.sections.api_service.children.request_parameters.title}}

{{#structure.api_specification.operations}}
| 항목명(영문) | 항목명(국문) | 위치 | 타입 | 길이/정밀도 | 필수 | 허용값 | 기본값 | 샘플데이터 | 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{{#request_parameters}}
| {{param_name}} | {{name_ko}} | {{location}} | {{data_type}} | {{length}} | {{required}} | {{allowed_values}} | {{default_value}} | {{sample_value}} | {{description}} |
{{/request_parameters}}
{{/structure.api_specification.operations}}

### {{guide.sections.api_service.children.response_fields.number}} {{guide.sections.api_service.children.response_fields.title}}

{{#structure.api_specification.operations}}
| 항목명(영문) | 항목명(국문) | 응답 경로 | 타입 | 출현횟수 | 필수 | 허용값 | 샘플데이터 | 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{{#response_parameters}}
| {{param_name}} | {{name_ko}} | {{path}} | {{data_type}} | {{cardinality}} | {{required}} | {{allowed_values}} | {{sample_value}} | {{description}} |
{{/response_parameters}}
{{/structure.api_specification.operations}}

### {{guide.sections.api_service.children.error_codes.number}} {{guide.sections.api_service.children.error_codes.title}}

| 오류코드 | 오류메시지 | HTTP 상태 | 설명 |
| :--- | :--- | :--- | :--- |
{{#structure.api_specification.error_codes}}
| {{code}} | {{message}} | {{http_status}} | {{description}} |
{{/structure.api_specification.error_codes}}

### {{guide.sections.api_service.children.request_response_examples.number}} {{guide.sections.api_service.children.request_response_examples.title}}

{{#structure.api_specification.operations}}
| 형식 | 예시 |
| :--- | :--- |
| XML | {{sample_messages.xml_sample}} |
| JSON | {{sample_messages.json_sample}} |
{{/structure.api_specification.operations}}

### {{guide.sections.api_service.children.usage_notes.number}} {{guide.sections.api_service.children.usage_notes.title}}

| 항목 | 내용 |
| :--- | :--- |
| 응답 경로·포맷 | {{structure.api_specification.payload_path}} / {{structure.api_specification.mime_types}} |
| 호출 제한·페이지네이션 | {{structure.api_specification.rate_limit}} / {{structure.api_specification.pagination}} |
| 이용·계약 검토 상태 | {{document.review_status}} |
| 기관 확인 필요사항 | {{document.review_notice}} |
{{/guide.api}}

## {{guide.sections.ai.number}}. {{guide.sections.ai.title}}

### {{guide.sections.ai.children.ai_summary.number}} {{guide.sections.ai.children.ai_summary.title}}

| ?? | ?? |
| :--- | :--- |
| AI ?? ?? | {{ai.purpose}} |
| ??? ?? ?? | {{structure.data_category}} |
| ?? ?? ?? | {{ai.time_series_characteristics}} |
| ?? ?? ?? | {{ai.spatial_characteristics}} |

### {{guide.sections.ai.children.tasks.number}} {{guide.sections.ai.children.tasks.title}}

| ?? ?? | ?? | ?? ?? | ?? ?? | ?? ?? |
| :--- | :--- | :--- | :--- | :--- |
{{#ai.tasks}}
| {{type}} | {{description}} | {{input_fields}} | {{target_fields}} | {{evaluation_metrics}} |
{{/ai.tasks}}

### {{guide.sections.ai.children.training_info.number}} {{guide.sections.ai.children.training_info.title}}

| ?? | ?? |
| :--- | :--- |
| ?? ??? ?? ?? | {{ai.split_ratio.strategy}} |
| ?? ?? | {{ai.split_ratio.train}} |
| ?? ?? | {{ai.split_ratio.validation}} |
| ?? ?? | {{ai.split_ratio.test}} |
| ???? ?? | {{ai.split_ratio.leakage_review}} |

### {{guide.sections.ai.children.recommended_features.number}} {{guide.sections.ai.children.recommended_features.title}}

{{#aiRecommendedFeatures}}
| ?? ID | ??? | ?? ?? |
| :--- | :--- | :--- |
| {{field_id}} | {{field_name}} | {{reason}} |
{{/aiRecommendedFeatures}}

### {{guide.sections.ai.children.bias_representativeness.number}} {{guide.sections.ai.children.bias_representativeness.title}}

| ?? | ?? |
| :--- | :--- |
| ??? ?? | {{ai.bias}} / {{responsible_ai.data_biases}} |
| ??? ?? | {{ai.representativeness}} / {{statistics.representativeness}} |
| ?? ?? | {{analysis.scope}} |

### {{guide.sections.ai.children.limitations.number}} {{guide.sections.ai.children.limitations.title}}

| ?? | ?? |
| :--- | :--- |
| ??? ?? | {{aiLimitations}} |
| ?? ?? | {{analysis.limitations}} |
| ??? ?? ?? | {{ai.large_data_optimization}} |

### {{guide.sections.ai.children.corrected_estimated_usage.number}} {{guide.sections.ai.children.corrected_estimated_usage.title}}

| ?? | ?? |
| :--- | :--- |
| ?????? ?? | {{ai.imputed_data_usage}} |
| ?? ?? ?? | {{document.review_notice}} |
| ?????? ?? | ?? ???? ??????? ???? ??? ?? ?? ?? |

### {{guide.sections.ai.children.usage_risks.number}} {{guide.sections.ai.children.usage_risks.title}}

| ??????? |
| :--- |
{{#ai.usage_risks}}
| {{risk}} |
{{/ai.usage_risks}}
| {{ai.quality_flag_usage}} |
| {{governance.privacy_security.security_level}} / {{document.review_notice}} |

## {{guide.sections.governance.number}}. {{guide.sections.governance.title}}

### {{guide.sections.governance.children.confirmation_items.number}} {{guide.sections.governance.children.confirmation_items.title}}

| 항목 | 확인 내용 |
| :--- | :--- |
| 기관명·소관부서 | {{dataset.publisher}} / {{dataset.creator}} |
| 담당자·연락처 | {{dataset.contact_point.name}} / {{dataset.contact_point.email}} / {{dataset.contact_point.phone}} |
| 개인정보 포함 여부 | {{governance.privacy_security.contains_pii}} |
| 품질·대표성·권리 검토 | {{document.review_notice}} |

### {{guide.sections.governance.children.review_status.number}} {{guide.sections.governance.children.review_status.title}}

| 항목 | 상태 |
| :--- | :--- |
| 문서 상태 | {{document.status}} |
| 검토 상태 | {{document.review_status}} |
| 문서 유형 | {{document.doc_type}} |
| 초안 여부 | {{document.is_draft}} |

### {{guide.sections.governance.children.source_document_identity.number}} {{guide.sections.governance.children.source_document_identity.title}}

| 항목 | 내용 |
| :--- | :--- |
| 데이터셋 식별자 | {{dataset.identifier}} |
| 원본 파일 해시 | {{provenance.source_file_sha256}} |
| 생성 시각 | {{document.generated_utc}} |
| 명세 버전 | {{document.specification_version}} |
| 데이터 버전 | {{dataset.version_info.version}} |

### {{guide.sections.governance.children.prepublication_check.number}} {{guide.sections.governance.children.prepublication_check.title}}

| 점검 항목 | 결과·확인 |
| :--- | :--- |
| 구조·필수값·타입 검증 | {{document.review_status}} |
| 품질·통계·샘플 검토 | {{quality.metrics}} / {{statistics}} |
| 개인정보·권리·보안 검토 | {{governance.privacy_security}} / {{usage.rights}} |
| JSON·XML·JSON-LD·TTL 일치 검토 | {{document.review_notice}} |

## {{guide.sections.reference.number}}. {{guide.sections.reference.title}}

### {{guide.sections.reference.children.standards_guidelines.number}} {{guide.sections.reference.children.standards_guidelines.title}}

| 기준 영역 | 적용 기준 |
| :--- | :--- |
| 공통 메타데이터 | Schema.org / DCAT / Dublin Core / vCard / DQV |
| 공공데이터 연계 | 공공데이터포털 메타데이터 및 OpenAPI 제공 명세 |
| AI 활용·책임성 | 데이터 품질·개인정보·편향·정보누출 검토 기준 |
| 기계판독 산출물 | Canonical Metadata Schema 및 JSON/XML/JSON-LD/TTL 매핑 |

### {{guide.sections.reference.children.metadata_mapping.number}} {{guide.sections.reference.children.metadata_mapping.title}}

| Canonical 항목 | 표준 매핑 |
| :--- | :--- |
| dataset.title / description | dct:title / dct:description / schema:name / schema:description |
| dataset.publisher / creator | dct:publisher / dct:creator / schema:publisher |
| access_url / download_url | dcat:accessURL / dcat:downloadURL |
| distribution / format | dcat:distribution / dct:format / schema:encodingFormat |
| field·quality·provenance | dcat:theme·dct:temporal·dqv:hasQualityMeasurement·prov:wasDerivedFrom |
