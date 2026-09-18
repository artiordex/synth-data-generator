# ADR-003: Canonical Metadata 및 검토 상태 기반 단일 진실 원천(SSOT) 아키텍처

- 상태: Accepted
- 결정일: 2026-09-16
- 작성자: 시스템 아키텍처팀
- 적용 범위: 분석 결과 모델, AI 가이드 메타데이터, 검토 체계 및 전 출력 포맷 렌더러

---

## 1. 배경 (Context)

AI 친화 공공데이터 가이드 시스템은 HWPX/DOCX/Markdown(사람이 읽는 AI 친화 데이터 가이드), JSON(기계 판독형 메타데이터), XML(행정 연계), JSON-LD(시맨틱 웹) 등 복수의 출력 포맷을 동시에 제공해야 한다.

만약 각 출력 포맷의 생성기가 원천 데이터를 개별적으로 분석하거나 자체적인 변환 규칙을 둘 경우, 다음과 같은 치명적인 데이터 불일치(Data Discrepancy)가 발생한다:
1. **문서 간 수치 불일치**: 동일한 데이터셋임에도 HWPX의 레코드 수나 결측률과 JSON/XML의 수치가 달라지는 현상.
2. **사실과 추정의 혼동**: 프로그램으로 계산된 정확한 통계치와 AI 모델이 추론한 설명 초안, 담당자가 입력한 기관 정보가 구분 없이 뒤섞여 신뢰성을 훼손함.
3. **법적 검토 누락**: 개인정보, 라이선스, 관련 법령 등 사람이 직접 확인해야 할 항목이 임의로 확정 처리되어 배포되는 위험.

따라서 모든 파생 문서와 API 응답이 참조하는 **단일 진실 원천(Single Source of Truth, SSOT)**으로서 표준화된 **Canonical Metadata Model**과 **엄격한 상태 코드(Status Code) 체계**를 도입한다.

이 결정에서 Canonical의 구조적 최상위 기준은
`apps/api/src/synthetic_api/data/ai_guide/templates/schemas/canonical-metadata.schema.json`으로 한다.
JSON 템플릿, XML/XSD, JSON-LD, Markdown 및 HWPX/DOCX는 이 JSON Schema에 맞는
Canonical 인스턴스의 초기화·직렬화·표현·검증을 담당하는 하위 자산이다.

---

## 2. 참조 공식 출처 (Official References)

- **[REF-07] 국가데이터 통합 연계를 위한 데이터 카탈로그 표준 가이드 v1.0 (행정안전부)**
  - DCAT-AP-KR (Data Catalog Vocabulary for Korea Public Data) 표준 프로파일
  - Dublin Core (`dct:`), ADMS (`adms:`), W3C Data Quality Vocabulary (`dqv:`) 등 공공 표준 메타데이터 어휘 체계
- **[REF-08] 공공데이터베이스 표준화 관리 매뉴얼 (행정안전부, 2026.4)**
  - 테이블/컬럼 논리명·물리명, 표준 데이터 도메인, 유효값 정의 및 데이터 사전 표준화 지침
- **[REF-06] AI Ready Data의 개념적 구조와 한국의 AI Ready 공공데이터 정책 분석 (한국행정연구원)**
  - 구문적(Syntax), 의미적(Semantics), 맥락적·윤리적(Context & Ethics) 3계층 준비도 모델 및 데이터 계보(Lineage) 관리 요건

---

## 3. 결정 사항 (Decisions)

### 3.1 단일 진실 원천(SSOT) 처리 파이프라인

모든 분석, 사용자 상호작용, 문서 렌더링은 반드시 다음의 단방향 파이프라인을 준수해야 한다.

```text
[원천 데이터 (CSV/JSON/XML/XLSX)]
                │
                ▼ (결정적 프로파일링 및 스키마 추출)
    [Canonical Metadata Model v2] ◀── [AI 설명 초안 보완 (추론 영역 한정)]
                │
                ▼ (사용자 검토 및 기관 승인)
    [Canonical Metadata 확정본]
                │
   ┌────────────┼────────────┬────────────┐
   ▼            ▼            ▼            ▼
[HWPX/DOCX]  [JSON]        [XML]      [JSON-LD]
(사람용 가이드) (기계판독형) (행정연계)  (시맨틱DCAT)
```

1. **출력기의 재분석 절대 금지**: HWPX, JSON, XML, JSON-LD 렌더러는 원천 데이터를 직접 파싱하거나 재계산하지 않으며, 오직 확정된 `Canonical Metadata`만을 읽어 렌더링한다.
2. **HWPX 원본 종속 배제**: HWPX 파일을 메타데이터의 소스로 사용하지 않는다. HWPX는 최종 표현형(Presentation) 산출물일 뿐이다.

---

### 3.2 Canonical Metadata Schema v2 구조

`canonical-metadata.schema.json`은 다음을 규정하는 최상위 구조 계약이다.

- Canonical 최상위 블록 및 필수 구조
- 데이터셋·필드·분석·품질·계보·검토 항목의 JSON 자료형
- 5단계 항목 상태 코드와 문서 검토 상태
- Canonical JSON 인스턴스가 갖춰야 할 최소 식별자·출처·검증 필드

`ai_ready_metadata_template.json`은 JSON Schema를 대체하지 않는다. 해당 파일은
플레이스홀더, 별칭, 반복 바인딩을 보존해야 하는 기존 렌더링 구현의 초기 모델
템플릿으로만 사용하며, 생성 직후 JSON Schema 검증을 통과해야 한다.

Canonical Metadata의 모든 항목은 값(Value)과 함께 **출처 유형(Source Type)**, **신뢰도(Confidence)**, 그리고 **검토 상태(Status)**를 함께 유지한다.

```json
{
  "id": "management.title",
  "label": "데이터셋 명칭",
  "property": "dct:title",
  "namespace": "http://purl.org/dc/terms/",
  "value": "식약처 의약품 품목허가 표준 공시 데이터",
  "sourceType": "FILE_HEADER",
  "status": "AUTO_CONFIRMED",
  "confidence": 1.0,
  "reason": "원천 파일 헤더 및 메타데이터 블록에서 직접 추출됨",
  "updatedAt": "2026-09-16T18:00:00Z"
}
```

---

### 3.3 표준 5단계 상태 코드 (Status Codes) 체계

데이터 항목의 생성 및 검증 주체를 명확히 구분하기 위해 다음 5가지 상태 코드를 엄격히 적용한다.

```text
┌─────────────────┬────────────────────────────────────────────────────────┐
│ 상태 코드       │ 정의 및 적용 기준                                      │
├─────────────────┼────────────────────────────────────────────────────────┤
│ AUTO_CONFIRMED  │ 알고리즘으로 직접 측정·검증되어 사실이 확정된 값       │
│ AUTO_INFERRED   │ AI 또는 휴리스틱이 추론한 값 (사람의 검토가 권장됨)    │
│ USER_CONFIRMED  │ 업무 담당자가 직접 입력하거나 검토 후 최종 승인한 값   │
│ REVIEW_REQUIRED │ 자동 확정 금지! 반드시 담당자의 공식 확인이 필요한 값  │
│ NOT_APPLICABLE  │ 데이터 포맷 또는 범주 특성상 해당되지 않는 항목        │
└─────────────────┴────────────────────────────────────────────────────────┘
```

#### 1. `AUTO_CONFIRMED` (자동 확정)
- **적용 대상**: 파일 크기(bytes), 총 레코드 수, 필드 수, 관측 데이터 타입, 결측치(Null/Empty) 개수 및 비율, 고유값 수, 중복 레코드 수, 관측된 날짜/수치 범위.
- **원칙**: 수학적·결정론적으로 계산된 값이며 변경되지 않는다.

#### 2. `AUTO_INFERRED` (자동 추론 초안)
- **적용 대상**: 데이터 도메인 카테고리 후보, 컬럼 설명 초안, 후보 식별자(Candidate Key), AI 활용 시나리오 요약.
- **원칙**: LLM 또는 규칙 엔진이 원천 데이터를 바탕으로 생성한 제안이며, 가이드 문서에는 "AI 작성 초안 (검토 필요)" 뱃지가 부여된다.

#### 3. `USER_CONFIRMED` (사용자 승인)
- **적용 대상**: 담당자가 UI 상에서 직접 입력하거나, AI가 제안한 `AUTO_INFERRED` 내용을 검토 후 '확인(승인)' 버튼을 누른 값.
- **효력**: 최종 공문서 배포본의 확정값으로 인정된다.

#### 4. `REVIEW_REQUIRED` (검토 필수 - 기관 확인 필요)
- **적용 대상**:
  - 관련 근거 법령 및 공공데이터 제공 지침
  - 공식 이용 라이선스 (공공누리 유형, 저작권 범위)
  - 개인정보 및 민감정보 비식별화 처리 여부
  - API 운영 엔드포인트 URL, 인증 방식, 호출 트래픽 한도
  - 공식 담당 부서 및 연락처
- **원칙**: 데이터 페이로드에서 확인할 수 없는 행정적·법적 정보는 AI가 절대 날조하지 않고 `REVIEW_REQUIRED`로 마킹한다. HWPX 문서에는 `[기관 확인 필요]`로 표시된다.

#### 5. `NOT_APPLICABLE` (해당 없음)
- **적용 대상**: 파일데이터(Track 1)에서의 API 엔드포인트 정보, 수치형이 아닌 텍스트 데이터에서의 평균값 등.

---

## 4. 품질 판정 제한 원칙 (Quality Assertion Guardrails)

본 아키텍처는 [REF-02], [REF-04] 표준에 따라 다음의 허위 품질 주장을 시스템 수준에서 금지한다:
- **파싱 성공 ≠ 품질 합격**: 데이터가 에러 없이 파싱되었다고 해서 AI-Ready 품질 인증을 부여하지 않는다.
- **결측 0건 ≠ 데이터 무결성**: 결측치가 0건이라도 코드값 위반이나 이상치가 존재할 수 있음을 분리 명시한다.
- **타입 일치 ≠ 의미적 정확성**: 숫자로 적혀 있다고 해서 해당 값이 실제 측정 단위나 논리적 의미와 부합함을 보증하지 않는다.
- **샘플 분석 ≠ 전체 인증**: 샘플 1,000건을 프로파일링한 결과를 전체 수백만 행 데이터셋의 종합 품질 인증으로 과장하지 않는다.

---

## 5. 결과 (Consequences)

### 긍정적 효과
- **완벽한 데이터 정합성 보장**: HWPX, JSON, XML, JSON-LD 간의 수치 불일치 가능성을 완전히 제거함.
- **감사 추적성(Audit Trail)**: 각 항목이 어떤 근거(파일 헤더, AI 추론, 담당자 승인)로 작성되었는지 역추적 가능함.
- **행정적 안전성**: 라이선스나 법령 등 민감한 공공 규제 항목의 자의적 작성을 원천 차단함.

### 관리 시 주의사항
- `REVIEW_REQUIRED` 항목이 남아있는 상태에서 문서를 출력할 경우, 시스템은 상단에 **"임시 검토본(Draft for Review)"** 워터마크 또는 주의 문구를 필수 표기해야 한다.

---

## 6. 수용 기준 (Acceptance Criteria)

- [x] 모든 출력 포맷(HWPX, JSON, XML, JSON-LD)이 단일 Canonical Metadata로부터 생성됨.
- [x] 메타데이터 모델에 `status`와 `sourceType` 필드가 필수로 구현됨.
- [x] 5단계 상태 코드(`AUTO_CONFIRMED`, `AUTO_INFERRED`, `USER_CONFIRMED`, `REVIEW_REQUIRED`, `NOT_APPLICABLE`)가 정의됨.
- [x] 라이선스, 법령, API 계약 정보가 누락되었을 때 AI가 날조하지 않고 `REVIEW_REQUIRED`로 분류됨.
- [x] [REF-07], [REF-08], [REF-06]의 메타데이터 및 카탈로그 표준이 근거로 명시됨.
