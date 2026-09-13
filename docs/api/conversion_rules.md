# 데이터 변환 규칙

변환 API의 호환성 규칙은 `apps/api/src/synthetic_api/application/services/conversion_rules.py`가 단일 소스입니다. 프론트엔드가 임의로 조합을 만들지 않도록 `GET /api/v1/converter/rules`로 같은 계약을 조회할 수 있습니다.

## 정규화

- 입력 파일명은 마지막 확장자를 소문자로 변환합니다.
- `.pq` 입력은 `.parquet`으로 정규화합니다.
- `markdown`과 `.md`는 `md`, `htm`은 `html`로 정규화합니다.
- `word`와 `doc`은 `docx`, `xls`는 `xlsx`, `pq`는 `parquet`으로 정규화합니다.
- 지원되지 않는 입력 확장자, 빈 대상 포맷, 허용되지 않은 소스/대상 조합은 업로드 전에 HTTP 400으로 차단합니다.

## 미리보기 모드

| 대상 | 모드 | 의미 |
| --- | --- | --- |
| `html` | `html` | HTML 결과만 렌더링 |
| `md` | `markdown` | Markdown 결과만 표시 |
| `sql` | `sql` | SQL 코드 결과만 표시 |
| 데이터셋의 `csv`, `xlsx`, `tsv`, `json`, `jsonl`, `parquet` | `table` | 표 데이터 결과 |
| 그 외 문서 출력 | `none` | 다운로드 결과만 제공 |

## 허용 조합

문서 입력(`hwp`, `hwpx`, `doc`, `docx`, `pdf`, `md`)은 입력별 구현된 변환기만 노출합니다.

| 입력 | 허용 대상 |
| --- | --- |
| `hwp`, `hwpx` | `md`, `txt`, `pdf`, `hwpx`, `html`, `xlsx`, `docx`, `hwp` |
| `doc`, `docx` | `md`, `txt`, `pdf`, `hwpx`, `html`, `xlsx`, `docx` |
| `pdf` | `md`, `txt`, `pdf`, `hwpx`, `html`, `xlsx`, `docx`, `hwp` |
| `md` | `md`, `txt`, `pdf`, `hwpx`, `html`, `xlsx`, `docx` |

데이터셋 입력(`csv`, `xlsx`, `xls`, `tsv`, `txt`, `json`, `jsonl`, `parquet`)은 `md`, `html`, `csv`, `xlsx`, `tsv`, `json`, `jsonl`, `parquet`, `sql`을 허용합니다.

새 변환기를 추가할 때는 구현 분기와 함께 규칙 매트릭스, 출력 확장자, 미리보기 모드, 규칙 테스트를 동시에 갱신해야 합니다.
