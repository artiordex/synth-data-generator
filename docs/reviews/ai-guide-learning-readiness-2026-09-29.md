# AI 가이드의 AI 활용·학습 포맷 검토 의견

- 검토일: 2026-09-29~2026-09-30 (KST)
- 기준 커밋: `396f2a2` (`main`)
- 범위: AI 가이드 입력 화면, 정규 메타데이터(Canonical) 생성, 검토 상태, JSON/XML/JSON-LD/Turtle 및 사람용 문서 출력
- 방법: 코드·템플릿 확인, 기존 테스트, 가상 데이터로 생성·확장·직렬화 재현
- 검토 결과: 아래 F1–F8은 기준 커밋 당시 확인한 문제와 제안이다. 후속 개선은 2026-09-30에 적용하고 아래 적용 기록에 남긴다.

## 1. 종합 의견

**AI가 읽을 수 있는 구조화 포맷의 기반은 구현되어 있다. 다만 가이드를 AI 지식으로 안정적으로 제공하고, 검증된 학습 자료로 재사용하려면 보완이 필요하다.**

단일 Canonical 모델, JSON Schema, 필드 사전, 원천 해시, 항목별 출처와 검토 상태는 좋은 기반이다. 실제로 JSON/XML 생성과 기본 검증도 동작한다. 그러나 일부 출력에서 의미가 유실되고, 포맷에 존재하는 항목을 사람이나 AI가 완성할 입력 경로가 부족하다. 형식 검증의 `PASS`를 학습 적합성으로 해석해서는 안 된다.

사용자가 말한 “학습”을 다음 두 용도로 나누어 판단했다.

| 사용 목적 | 현재 판단 | 필요한 보완 |
| --- | --- | --- |
| 가이드를 LLM에 문맥으로 제공하거나 검색 증강 생성(RAG)에 사용 | 조건부 사용 가능 | 깨진 표 제목 복구, 필요한 사실과 검토 상태를 함께 담은 소형 문서 단위, 원문 근거 연결 |
| JSON/XML을 파싱해 데이터 구조와 이용 조건을 이해 | 기반 구현 | 입력 누락 해소, 의미·참조·범위 검증 강화 |
| JSON-LD/Turtle을 지식 그래프로 사용 | 수정 필요 | JSON-LD 속성 유실, Turtle 필드 충돌·타입·라이선스 직렬화 수정 |
| 가이드에 근거한 질문·답변 등으로 모델을 추가 학습 | 준비 과정 추가 필요 | 근거가 있는 학습 예시, 승인 이력, 목적별 분할, 별도 평가 세트와 모델별 내보내기 |

JSON-LD라는 확장자나 여러 다운로드 형식을 제공하는 것만으로 학습 자료가 완성되지는 않는다. JSON-LD는 연결 데이터의 표현 형식이다. 학습 예시와 정답의 품질은 별도로 평가해야 한다. [W3C JSON-LD 1.1](https://www.w3.org/TR/json-ld11/)

## 2. 확인된 장점

- **출력의 공통 기준이 있다.** `service.generate()`가 프로파일 → 담당자 입력 → AI 보완 → `finalize()` → 렌더링 순서로 동작한다.
- **미확정과 확정 정보를 구분한다.** `AUTO_CONFIRMED`, `AUTO_INFERRED`, `USER_CONFIRMED`, `REVIEW_REQUIRED`, `NOT_APPLICABLE` 상태와 초안 표시를 유지한다.
- **미확정 값을 임의로 채우지 않는다.** 법령·라이선스·운영 계약은 근거가 없으면 `null`로 남기며, 담당자 입력을 AI가 덮어쓰지 않도록 한다.
- **필드와 가공 이력을 연결할 기반이 있다.** 원천 경로, 필드 ID, 원천 파일 해시, 파생·결측 처리 참조를 보관한다.
- **기본 기계 검증이 있다.** Canonical 스키마, 값과 JSON Pointer의 일치, 검토 목록의 일치, XML XSD, JSON-LD 오프라인 확장을 확인한다.
- **품질 해석을 과장하지 않는다.** 관측값 채움률을 정확성·대표성·편향 평가와 구별하고, 국가 프로파일/SHACL 적합성은 미검증으로 표시한다.

근거: [생성 서비스](../../apps/api/src/synthetic_api/application/services/ai_guide_document/service.py#L496), [검토 상태와 무결성 검사](../../apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py#L488).

## 3. 우선 수정 의견

P1은 해당 산출물을 AI 지식·학습 자료로 채택하기 전에 수정할 결함, P2는 활용 범위를 확대할 때 필요한 보완을 뜻한다.

### F1 · P1 — 포맷의 항목을 사람과 AI가 완성할 경로가 부족하다

**현상**

- 필드에는 `required`, `is_pk`, `constraints`가 존재하지만 담당자 필드 입력 바인더는 영문명·표시명·설명·단위·코드·타입만 반영한다.
- `training_split` 입력은 `ai.split_ratio.strategy` 문자열에만 들어간다. 구조화된 `train`, `validation`, `test`, `leakage_review`를 채우는 경로는 없다.
- AI 요청 형식은 작업에 `type`, `description`만 요구한다. 출력 템플릿은 추가로 `input_fields`, `target_fields`, `evaluation_metrics`, `evidence`, `status`, `reason`까지 요구한다.
- 작업 항목의 값은 바인더에서 일괄 `str(...)`로 바뀐다. 향후 필드 ID 목록을 AI가 배열로 반환해도 구조화된 배열로 보존되지 않는다.
- 현재 수정 이벤트는 해당 값을 `USER_CONFIRMED`로 처리한다. AI 제안을 수정 없이 채택하는 명시적 승인 동작이나 모든 검토 경로를 편집하는 기능은 확인되지 않았다.

**재현**

`/*/value` 필드에 `required=true`, `is_pk=true`, `constraints=">= 0"`, `unit="mg"`를 전달했을 때 단위만 반영되고 나머지는 `null`이었다. `training_split="80/10/10"`도 비율 세 값은 `null`로 남았다. 현재 AI 프롬프트 예시에 맞는 작업을 바인딩하면 작업 한 건에서 위 추가 6개 항목이 모두 검토 목록으로 들어간다.

이는 담당자가 정보를 충분히 알고 있어도 “기관 확인 필요”를 해소하기 어려운 원인이다. AI에 빈칸을 더 많이 채우라고 지시하는 것만으로 해결되지 않는다.

**제안**

1. 출력 경로별로 담당자 입력, 관측 계산, AI 초안, 비해당 판정 중 어떤 방식으로 완성하는지 대응표를 만든다.
2. 필수 여부·키·제약·목표 필드·평가 지표·분할 기준을 타입이 있는 입력으로 연결한다.
3. AI에는 근거가 있는 후보와 그 근거를 구조화하여 요청하고, 담당자에게 채택·수정·보류 동작을 제공한다.
4. 모르는 값과 해당 없는 값을 구별하고, 용도별 필수 항목을 정한다. 모든 선택 항목의 확인을 강제하지 않는다.

근거: [필드 입력 바인더](../../apps/api/src/synthetic_api/application/services/ai_guide_document/service.py#L316), [분할 기준 매핑](../../apps/api/src/synthetic_api/application/services/ai_guide_document/service.py#L57), [AI 작업 바인더](../../apps/api/src/synthetic_api/application/services/ai_guide_document/service.py#L414), [AI 요청 형식](../../apps/api/src/synthetic_api/routes/v1/ai_guide.py#L364), [프런트엔드 전송 항목](../../apps/web/src/features/aiguide/AiRuleGuideStudio.tsx#L1269).

### F2 · P1 — JSON-LD 확장에 성공해도 가공 규칙의 의미가 유실된다

**현상과 재현**

`processing.integration`의 `is_integrated`, `method`, `join_type`, `join_keys` 등은 접두사가 없고 `@context`에도 매핑이 없다. 유효한 Canonical 모델에 다음 값을 넣고 JSON-LD를 생성한 뒤 PyLD로 확장했다.

```json
{"is_integrated": true, "method": "inner join", "join_type": "inner", "join_keys": ["recordId"]}
```

확장된 `integration` 노드에는 `@type`과 전역 매핑이 있는 `description`만 남고 위 속성들은 사라졌다. 현재 검증은 확장 성공과 최상위 노드 개수만 확인하므로 `PASS`가 나온다.

`ai:canonicalItems`의 보조 레코드에는 원래 값이 남아 있으므로 전체 JSON의 값이 모두 사라지는 문제는 아니다. 그러나 가공 그래프를 일반 RDF 도구로 질의하는 소비자는 결합 규칙을 얻지 못한다. JSON-LD에서 IRI로 확장되지 않는 키는 처리 과정에서 무시된다. [W3C JSON-LD의 컨텍스트 설명](https://www.w3.org/TR/json-ld11/#the-context)

**제안**

- 가공 블록의 모든 의미 있는 속성에 명시적 어휘 매핑을 지정한다.
- 값이 있는 중요 경로를 대상으로 확장 전후의 값·타입·참조 보존을 검사한다.
- `PASS` 결과를 구문 검사, 의미 보존, 프로파일 적합성으로 분리한다.

근거: [JSON-LD 컨텍스트](../../apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_metadata_template.jsonld#L86), [가공 블록](../../apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_metadata_template.jsonld#L721), [현재 확장 검증](../../apps/api/src/synthetic_api/application/services/ai_guide_document/exchange.py#L114).

### F3 · P1 — Turtle에서 필드가 합쳐지고 자료형·라이선스가 잘못 표현된다

**재현 결과**

| 입력/상태 | 실제 Turtle 결과 | 영향 |
| --- | --- | --- |
| 서로 다른 `/*/지역`, `/*/기관` | 둘 다 `:_____` 속성 | 다른 필드가 한 속성으로 합쳐짐 |
| `value=1.25`, Canonical 타입 `number` | `rdfs:range xsd:string` | 수치 필드의 의미가 문자열로 바뀜 |
| `license_type=KOGL_TYPE_1` | `<공공누리 제1유형(출처표시)>` | URI가 아닌 표시명을 IRI 위치에 삽입 |

RDFLib는 마지막 사례를 경고와 함께 읽었지만 N-Triples 재직렬화는 실패했다. 따라서 “파서가 한 번 읽었다”는 사실만으로 적합성을 판정할 수 없다. Turtle의 `<...>` IRI에는 공백을 그대로 넣을 수 없다. [W3C Turtle 문법](https://www.w3.org/TR/turtle/#grammar-production-IRIREF)

현재 Turtle은 Canonical의 검토 상태를 투영하지 않으며, 데이터셋 주소도 원천 식별자 대신 제목으로 만든 `https://data.go.kr/ontology/...`를 사용한다. 다른 데이터가 같은 제목을 쓰면 같은 주소가 생긴다. 생성 코드가 해당 기관의 공식 주소로 등록되는 동작은 없다.

**제안**

- 검증된 Canonical 필드 ID를 사용하고, 표시명은 별도 라벨로 보관한다.
- `number`, 혼합 타입, 배열·객체의 표현 규칙을 명시한다.
- 라이선스의 코드·표시명·공식 URI를 분리하고 JSON-LD와 Turtle에서 같은 규칙을 적용한다.
- 문자열 연결 대신 RDF 라이브러리로 출력하고, 필드 수·타입·식별자·상태 보존을 확인한다.

근거: [라이선스 표시명 매핑](../../apps/api/src/synthetic_api/application/services/ai_guide_document/service.py#L77), [Turtle 주소·라이선스 출력](../../apps/api/src/synthetic_api/application/services/ai_guide_document/exchange.py#L153), [필드명·타입 출력](../../apps/api/src/synthetic_api/application/services/ai_guide_document/exchange.py#L204).

### F4 · P1 — 사람용 가이드 일부 표 제목이 실제로 `??`로 저장되어 있다

원본 Markdown 템플릿의 구축·수집·가공·AI 활용 표 등에 `| ?? | ?? |`, `| ?? ID | ??? | ...`가 들어 있다. 생성된 Markdown에서도 같은 문자열을 확인했다. 터미널 표시 문제와 구별하여 원본 파일과 생성 파일을 함께 확인했다.

이 문서를 읽는 AI는 값이 수집 방법인지, 결합 규칙인지, 제한사항인지 표 제목에서 구분하기 어렵다. 현행 왕복 검증은 깨진 템플릿을 그대로 출력해도 통과한다.

**제안:** 템플릿의 의미 있는 한국어 제목을 복구하고, 주요 섹션별 필수 라벨이 출력되는지 확인한다. Office 문서의 시각적 배치는 별도 확인이 필요하다.

근거: [원본 템플릿](../../apps/api/src/synthetic_api/data/ai_guide/templates/ai_ready_public_data_guide_template.md#L92), [현재 출력 검증](../../apps/api/src/synthetic_api/application/services/ai_guide_document/render.py#L1494).

### F5 · P2 — 스키마 통과가 AI 활용 정보의 유효성을 보장하지 않는다

`ai`, `quality` 등의 세부 구조는 넓게 허용되어 있다. 스키마는 객체의 존재를 검사하지만 분할 비율·작업 참조·품질 점수의 세부 조건까지 검사하지 않는다.

서비스 내부 `finalize()`를 직접 호출한 검증에서 다음 잘못된 값도 통과했다.

```json
{
  "split_ratio": {"train": -30, "validation": 200, "test": "wrong"},
  "recommended_features": [17],
  "completeness_score": 500
}
```

위 코드는 검증 결과를 간추린 예시이며, 실제 입력은 각각 `ai.split_ratio`, `ai.recommended_features`, `quality.metrics.completeness.score`에 넣었다. 일반 화면에서 이 값을 모두 입력할 수 있다는 의미는 아니다.

**제안:** 비율의 수치 범위·합계, 품질 점수 범위, 작업 타입, 필드 ID 참조, 평가 지표, 코드 목록·값 제약을 검사한다. 기존 초안의 `null`은 허용하되 “미평가”를 적합 판정과 구별한다. `additionalProperties`로 허용한 값에는 별도 세부 규칙이 필요하다. [JSON Schema 객체 속성 규칙](https://json-schema.org/understanding-json-schema/reference/object#additionalproperties)

근거: [AI·품질 스키마](../../apps/api/src/synthetic_api/data/ai_guide/templates/schemas/canonical-metadata.schema.json#L75), [검증 진입점](../../apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py#L542).

### F6 · P2 — AI 지식 제공·추가 학습을 위한 전용 내보내기가 없다

현재 ZIP에는 사람용 문서 4종, JSON/XML/JSON-LD, Turtle, 품질보고서가 들어간다. JSON에는 본문, 원천 프로파일, `canonicalItems`, `reviewRequired`가 함께 들어간다.

가상 입력 한 행·업무 필드 5개에서 컨테이너 경로까지 포함한 필드가 7개, Canonical 항목이 862개, 검토 항목이 261개 생성되었다. 해당 모델을 `ensure_ascii=False`로 JSON 직렬화한 크기는 약 626 KB였다. 이는 이번 작은 재현 사례의 바이트 크기이며 일반적인 비율이나 토큰 수로 확대 해석해서는 안 된다.

이 구조는 추적과 검토에는 유용하지만 통째로 프롬프트·검색 문서에 넣으면 같은 사실과 미확정 문구가 반복된다. ZIP에는 스키마 파일, 내보내기 규칙, 승인된 지식 단위, 학습 예시, 별도 평가 세트가 포함되지 않는다. 초안 다운로드 자체는 정상적인 사용 목적이며, AI 투입용 산출물을 추가하는 방향이 적절하다.

**제안**

- **지식 제공용:** 장/필드/규칙 단위로 `id`, `dataset_id`, `version`, `text`, `source_paths`, `evidence`, `review_status`를 담은 소형 출력을 추가한다. AI 추론·샘플값·미확정 사항을 사실 문장과 구분한다.
- **추가 학습용:** 목표 모델·작업이 정해진 경우에만 근거가 있는 질문·답변 또는 입력·정답 예시, 승인 정보, 데이터셋/버전 단위 분할, 평가 세트를 만든다. JSONL은 가능한 전달 형식 중 하나다.
- **공통:** 스키마·해시·버전·승인 범위가 있는 manifest와 소비 방법을 동봉한다. 항목 근거를 현재의 공통 문구에서 파일·필드·문서 위치로 구체화한다.

근거: [ZIP 패키징](../../apps/api/src/synthetic_api/routes/v1/ai_guide.py#L421), [항목별 근거 생성](../../apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py#L521).

### F7 · P2 — 원본 예시값의 AI 재사용 정책이 필요하다

현재 샘플 보호는 비밀키·토큰으로 보이는 필드명 및 일부 서명 URL에 집중되어 있다. `contains_pii=true`로 표시한 가상 이메일 값 `review-fixture@example.invalid`도 JSON·Markdown·XML·JSON-LD에 그대로 포함되었다.

개인정보 포함 표시가 마스킹 실행을 의미하지 않는다는 점을 명확히 해야 한다. 이 검토에서는 실제 개인정보를 사용하거나 외부 AI로 전송하지 않았다.

**제안:** AI 투입용 출력에서 예시값 제외·마스킹·가상값 대체를 선택할 수 있게 하고, 필드별 공개 여부와 처리 결과를 기록한다. 구조 설명에 불필요한 원본 값은 해당 출력에서 제외한다.

근거: [현재 샘플 보호 범위](../../apps/api/src/synthetic_api/application/services/ai_guide_document/profile.py#L27), [개인정보 상태 바인딩](../../apps/api/src/synthetic_api/application/services/ai_guide_document/service.py#L219).

### F8 · P2 — 여러 가이드와 버전을 함께 적재할 식별자 규칙이 부족하다

- Canonical 데이터셋 URI는 첫 번째 입력 파일의 해시로만 생성한다. 두 번째 파일 내용만 바꾼 재현에서 전체 데이터셋 URI가 같았다.
- `canonicalItems[].id`는 경로만 해시한다. 서로 다른 데이터셋의 `/fields/0/name` 항목 ID가 동일했다. 문서 내부 키로는 사용할 수 있지만 전역 키로 사용하면 충돌한다.
- 필드 ID는 데이터셋 URI와 필드 순번에 의존하므로 컬럼 추가·순서 변경 시 이전 버전과의 대응을 별도로 관리해야 한다.

**제안:** 데이터셋의 논리 ID, 전체 입력과 설정을 반영하는 버전/산출물 ID, 원천과 경로를 반영하는 필드 ID를 구분한다. RAG 적재·변경 감지·학습 예시 중복 제거에 같은 규칙을 사용한다.

근거: [데이터셋 URI](../../apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py#L340), [필드 ID](../../apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py#L370), [항목 ID](../../apps/api/src/synthetic_api/application/services/ai_guide_document/binding.py#L521).

## 4. 권장 진행 순서와 완료 기준

| 순서 | 작업 | 완료 기준 |
| --- | --- | --- |
| 1 | 출력의 의미 보존: F2·F3·F4 | 가공 규칙·한글 필드·수치 타입이 포맷 간 유지되고 주요 표 제목이 정상 출력됨 |
| 2 | 사람+AI 작성 경로: F1 | 필수/제약/목표/분할 정보를 입력·제안·승인하면 대응 Canonical 경로와 문서에 반영됨 |
| 3 | 계약과 식별자 강화: F5·F8 | 잘못된 타입·비율·참조가 거부되고 데이터셋·버전 간 충돌이 없음 |
| 4 | AI 지식 제공용 출력: F6·F7 | 승인 범위·원천 근거·샘플 처리 상태를 가진 소형 지식 단위와 manifest 생성 |
| 5 | 활용 효과 평가 | 실제 업무 질문으로 정답성, 근거 인용, 모를 때의 응답을 측정한 뒤 필요하면 추가 학습용 예시 생성 |

사람은 업무 정의·권리·운영 계약·정답을 확인하고, AI는 관측 정보와 확인된 자료를 바탕으로 설명·후보·질문 초안을 작성하는 흐름을 권장한다. 확인할 수 없는 값을 지어내지 않으면서도 사람이 제공한 근거를 빠짐없이 반영하는 것이 우선이다.

성능 개선율은 이번 검토로 산정할 수 없다. “정확도 90% → 95%”를 평가하려면 먼저 업무 질문과 정답·근거를 고정한 평가 세트를 만들고 동일 조건에서 전후 결과를 비교해야 한다.

## 5. 검증 기록과 범위

실행 명령:

```bash
uv.exe run --project apps/api pytest apps/api/tests/test_ai_guide_documents.py apps/api/tests/test_ai_guide_quality_report.py -q
```

- 결과: **51 passed, 1 warning**, 약 71초.
- 경고: Starlette 테스트 클라이언트의 `httpx` 사용 관련 deprecation 경고.
- 추가 확인: 가상 JSON 파일로 실제 문서·ZIP 생성, PyLD 오프라인 확장, RDFLib 파싱과 재직렬화, 입력 바인더와 Canonical 검증 직접 호출.
- F2의 결합 규칙은 직렬화 경계를 검증하기 위해 유효한 Canonical 모델에 명시적으로 주입했다. 담당자 화면에서 현재 이 규칙을 모두 입력할 수 있다는 의미는 아니다.
- 원격 모델 생성 품질, 실제 기관 데이터의 정확성, Office 문서의 시각적 배치, 국가 프로파일 인증 및 실제 학습 성능은 이번 검증에 포함하지 않았다.
- 로컬 재현 스크립트와 상세 결과: `apps/storage/ai-guide-review-20260929/` (`probe.py`, `evidence.json`, `jsonld-evidence.json` 등). 저장소의 생성물 제외 정책을 따르는 로컬 자료다.

기존 테스트 통과는 정상 경로의 회귀 결과다. 위 의미 유실·입력 대응·학습 활용 적합성까지 통과했다는 의미는 아니다.

## 6. 후속 개선 적용 기록 (2026-09-30)

F1–F8의 제안에 대응해 담당자 입력과 승인 흐름, 구조화된 AI 작업·분할 정보, Canonical 제약 검증, JSON-LD/Turtle 의미 보존, 사람용 표 제목, 지식 제공용 JSONL 및 manifest, 샘플값 제외 정책, 데이터셋/항목 식별자를 보완했다. 기존 사람용 문서와 교환 포맷은 유지했다.

이 적용으로 RAG/검색 문맥 제공용 내보내기 기반은 추가됐지만, 승인된 질의·정답 쌍, 별도 평가 세트, 실제 기관 데이터로 측정한 검색·답변 정확도는 아직 별도 과제다. 따라서 이 작업만으로 추가 학습 적합성이나 정확도 향상을 주장하지 않는다.

검증 결과:

- AI 가이드 회귀: `uv.exe run --project apps/api pytest apps/api/tests/test_ai_guide.py apps/api/tests/test_ai_guide_documents.py` — **74 passed, 1 warning**.
- 전체 필수 회귀: `uv.exe run --project apps/api pytest apps/api/tests tests/ocr packages/synthetic_engine/tests/document_conversion` — **665 passed, 1 skipped, 160 warnings**, 291.80초.
- 웹 프로덕션 빌드: `npm run build --workspace=apps/web` — 통과. Vite가 큰 번들 청크에 대한 크기 안내를 출력했다.
- `git diff --check` — 통과. 검증 과정에서 자동 갱신된 의존성 목록 문서는 생성 파일이라 변경분에서 제외했다.
- 전체 회귀 경고는 Starlette 테스트 클라이언트의 `httpx` 사용 중단 예정 경고와 기존 SQLAlchemy `datetime.utcnow()` 사용 중단 예정 경고다.
