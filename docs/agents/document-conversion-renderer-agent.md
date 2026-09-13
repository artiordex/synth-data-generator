# 문서 변환 렌더러·화면 에이전트 프롬프트

먼저 `AGENTS.md`, `저장소작업지침.md`, `docs/agents/document-conversion-two-agent.md`를 읽는다. 파서 에이전트가 확정한 `MathIR`을 입력으로 받아 사람이 검토 가능한 결과를 만드는 것이 역할이다.

## 시작 조건

파서 에이전트가 `MathIR` 필드, 예시 JSON, fallback 규칙, 테스트 결과를 전달하기 전에는 공통 타입을 추측하지 않는다. 시작 전에 계약을 읽고, 계약이 부족하면 변경 요청을 남긴다.

## 작업 범위

단독 소유 파일은 다음과 같다.

- `packages/synthetic_engine/synthetic_engine/document_conversion/renderers/html_renderer.py`
- `packages/synthetic_engine/synthetic_engine/document_conversion/renderers/markdown_renderer.py`
- `apps/web/src/`의 변환 미리보기·검토 화면 관련 파일
- 위 모듈에 대응하는 새 렌더러/UI 테스트

`core/ir.py`, `parsers/`, `document_conversion_service.py`는 수정하지 않는다.

## 구현 순서

1. 일반 텍스트·표·이미지의 기존 렌더링을 먼저 회귀 테스트로 고정한다.
2. `MathIR`을 inline/display 수식으로 구분해 렌더링한다.
3. HTML은 MathML 또는 프로젝트가 채택한 수식 렌더링 방식으로 출력하고, fallback resource를 접근 가능한 대체 콘텐츠로 제공한다.
4. Markdown에서 복잡한 수식이나 여러 줄 셀은 GFM 표에 강제로 넣지 않는다. 필요한 경우 HTML 표 fallback을 사용한다.
5. 표 셀은 최소 너비, 줄바꿈, overflow, rowspan/colspan을 함께 검증한다.
6. 변환 실패·저신뢰 수식·원본 보존 상태를 미리보기에서 숨기지 않는다.
7. 웹 변경 후 반드시 `npm run build --workspace=apps/web`를 실행한다.

## 화면 검증 기준

- 수식이 한 글자 폭의 세로 열로 표시되지 않는다.
- 긴 수식은 표 전체 폭을 무한히 늘리지 않고 가로 스크롤 또는 적절한 줄바꿈을 사용한다.
- 원본과 결과를 비교할 때 수식의 위치와 검토 상태를 확인할 수 있다.
- 실패 상태를 성공처럼 보이는 초록색 PASS로 표시하지 않는다.
- 모바일과 데스크톱에서 표·수식·검토 배지가 서로 겹치지 않는다.

## 필수 테스트

- inline 수식 HTML
- display 수식 HTML
- Markdown의 표 안 수식
- 긴 수식과 긴 한글 텍스트가 있는 셀
- rowspan/colspan과 수식이 함께 있는 표
- MathIR fallback 출력
- 렌더링 실패 및 `needs_review` 표시
- 웹 빌드

## 파서 에이전트에 보낼 요청 형식

```text
PARSER_REQUEST:
- problem: <렌더링에 필요한 계약 부족 내용>
- required_field: <필요한 MathIR 필드>
- reason: <현재 출력이 불가능한 이유>
- reproduction: <테스트 또는 fixture>
```

