# 문서 변환 파서 에이전트 프롬프트

먼저 `AGENTS.md`, `저장소작업지침.md`, `docs/agents/document-conversion-two-agent.md`를 읽는다. 이 문서의 역할은 입력 파일을 의미 있는 IR로 보존하는 것이다.

## 작업 범위

단독 소유 파일은 다음과 같다.

- `packages/synthetic_engine/synthetic_engine/document_conversion/core/ir.py`
- `packages/synthetic_engine/synthetic_engine/document_conversion/parsers/`
- `apps/api/src/synthetic_api/application/services/document_conversion_service.py`
- 위 모듈에 대응하는 `packages/synthetic_engine/tests/document_conversion/` 및 `apps/api/tests/`의 새 테스트 파일

`renderers/`와 `apps/web`은 수정하지 않는다.

## 구현 순서

1. 현재 `TextRunIR`, `TableCellIR`, `BlockIR`, `SourceRef`, `Resource` 구조를 확인한다.
2. 기존 필드로 표현할 수 없는 수식만 `MathIR`로 추가한다. 기존 IR 타입을 중복 생성하지 않는다.
3. `MathIR`에는 원본 참조, 표현 형식, 표시 모드, fallback resource, 검토 상태를 포함한다.
4. DOCX의 `m:oMath`와 `m:oMathPara`를 먼저 처리한다.
5. HWPX/HWP의 수식·개체는 패키지 구조와 XML/record를 확인한 뒤 보존 가능한 원본을 우선 저장한다.
6. PDF/이미지는 수식으로 단정하지 말고, 좌표·이미지·OCR 후보를 진단 정보와 함께 보존한다.
7. `document_conversion_service.py`에서는 파서 선택과 결과 연결만 변경한다. 렌더링 HTML을 이 파일에서 임의로 재구성하지 않는다.

## 보존 규칙

- 원본 텍스트를 정규화하거나 임의로 합치지 않는다.
- 수식 인식 실패를 빈 문자열로 바꾸지 않는다.
- LaTeX 변환이 불확실하면 `needs_review=true`로 남기고 원본 XML/image를 유지한다.
- 신뢰도 숫자를 임의로 1.0 또는 PASS로 채우지 않는다.
- 수식 계산·정답 판정은 구현하지 않는다.

## 필수 테스트

- DOCX inline 수식
- DOCX display 수식
- 일반 텍스트와 수식이 섞인 단락
- 수식 파싱 실패 시 원본 fallback
- 표 셀 안 수식
- 여러 수식의 source reference 분리
- 기존 일반 텍스트와 표 회귀

## 작업 종료 조건

공통 계약의 `MathIR` 예시 JSON과 렌더러가 소비해야 할 규칙을 세션 종료 보고에 기록한다. 렌더러 코드를 직접 수정하지 말고, 필요한 변경은 다음 형식으로 전달한다.

```text
RENDERER_REQUEST:
- input: <MathIR 필드>
- expected_output: <HTML/Markdown 의미>
- fallback: <실패 시 출력>
- test_case: <재현 fixture/test 이름>
```

