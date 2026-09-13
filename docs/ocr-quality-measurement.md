# 무료 로컬 OCR 품질 측정 기준

이 문서는 무료 로컬 OCR의 품질을 테스트와 벤치마크에서 같은 방식으로 해석하기 위한 기준이다. 실제 사용자 문서 대신 테스트가 생성한 임시 fixture를 사용한다.

## 원칙

- 유료 API, 클라우드 OCR, 클라우드 VLM을 품질 기준으로 사용하지 않는다.
- confidence는 정확도 증명이 아니라 review 신호다.
- ground truth가 있는 fixture에서만 CER/WER와 문자 정확도를 실제 정확도로 해석한다.
- 문자 정확도는 실제 OCR 평가 구현인 `ocr.evaluation.metrics.text_metrics`와 같은 정의를 사용한다. 삽입 오류가 기준 문자열보다 길면 음수 정확도도 가능하다.
- 95% 목표는 텍스트, 구조, 시각 지표를 분리해서 판정한다.

## 페이지별 필수 지표

| 지표 | 설명 |
|---|---|
| `page_no` | 원본 문서의 페이지 번호 |
| `confidence` | OCR 엔진의 추정 신뢰도 |
| `text_length` | 인식 텍스트 길이 |
| `cell_count` | 인식된 표 셀 수 |
| `image_count` | 인식 또는 보존된 이미지 수 |
| `processing_time_ms` | 페이지 처리시간 |
| `numeric_damage_count` | 숫자 토큰 손상 수 |
| `date_damage_count` | 날짜 토큰 손상 수 |
| `amount_damage_count` | 금액 토큰 손상 수 |
| `special_character_damage_count` | 체크박스, 괄호, 기호 등 특수문자 손상 수 |
| `rotation_deg` | 감지 또는 보정된 회전 각도 |
| `empty_result_error` | OCR 결과가 비었는지 여부 |

## Detection 지표 해석

- `detection_match_rate`와 `annotation_coverage`는 하나의 OCR 박스가 여러 원천 annotation을 덮는 데이터셋 구조를 반영한 coverage 지표다. 기존 리포트 호환성을 위해 두 필드를 유지한다.
- `detection_precision`은 예측 박스 중 하나 이상의 annotation과 연결된 비율이다.
- `one_to_one_detection_precision`, `one_to_one_detection_recall`, `one_to_one_detection_f1`, `one_to_one_bbox_iou`는 source annotation을 단위로 고유 박스끼리만 매칭한다. 문자 단위 annotation 데이터셋에서는 단어 단위 detector 성능보다 박스 granularity 차이를 강하게 반영하므로 coverage와 함께 해석한다.
- confidence는 위 검출 지표와 별도다. 높은 confidence의 오인식은 `high_confidence_wrong_rate`로 측정한다.

## 누락 검출 보완 설정

Primary OCR 결과가 이미지의 text-like foreground를 충분히 설명하지 못할 때에만 secondary detector를 전체 페이지에 적용한다. 표 테두리, 긴 선, 큰 이미지 영역은 routing component에서 제외하며 기존 박스와 실질적으로 겹치는 secondary 결과는 중복 추가하지 않는다.

| 환경변수 | 기본값 | 설명 |
|---|---:|---|
| `OCR_SUPPLEMENTAL_DETECTION` | `true` | geometry 기반 누락 검출 보완 사용 여부 |
| `OCR_UNCOVERED_COMPONENT_RATIO` | `0.20` | secondary 전체 페이지 검출을 시작하는 미설명 foreground 비율 |
| `OCR_SUPPLEMENTAL_MIN_CONFIDENCE` | `0.55` | 새 박스를 추가할 최소 confidence |

OCR 엔진의 `raw_text`와 `OCRWord.text`에는 인식 원문을 보존한다. 날짜·금액의 보수적 형식 보정 결과는 `normalized_text`에만 저장하여 평가와 감사 시 원문을 재현할 수 있게 한다.

## 95% 목표 분리

| 목표 | 필드 | 합격 기준 |
|---|---|---|
| 텍스트 | `text_fidelity`, `meets_text_target_95` | 문자 정확도 >= 0.95 |
| 구조 | `structure_fidelity`, `meets_structure_target_95` | 기대 셀 수 대비 보존된 셀 수 >= 0.95 |
| 시각 | `visual_fidelity`, `meets_visual_target_95` | 이미지 수, 이미지 relationship, 병합 범위, 열 너비 보존율 평균 >= 0.95 |

세 목표 중 하나라도 미달하면 전체 결과는 검토 대상이다. 단일 평균 점수로 미달 항목을 숨기지 않는다.

## Review 신호

다음 중 하나라도 발생하면 `review_required=true`로 기록한다.

- OCR 결과가 비어 있다.
- confidence가 0.85 미만이다.
- 텍스트, 구조, 시각 지표 중 하나가 0.95 미만이다.
- 숫자, 날짜, 금액, 특수문자 손상이 있다.
- confidence가 높더라도 `0/O`, `1/l/I`, `5/S` 같은 숫자 유사 문자 손상이 있다.
- 날짜와 금액 손상은 각각의 필드에서 집계하고, 일반 숫자/코드 손상에서는 중복 집계하지 않는다.
- 벤치마크에는 빈 결과 negative control을 포함하며, 이 샘플은 pass나 success로 기록하지 않는다.

## 테스트 위치

- `benchmarks/ocr_quality_report.py`: 페이지별 품질 리포트 계산 계약
- `tests/ocr/test_quality_measurement_contract.py`: OCR 품질 지표와 review 신호 테스트
- `packages/synthetic_engine/tests/document_conversion/test_ocr_quality_preservation.py`: 이미지 relationship, 병합, 열 너비 보존 회귀 테스트
