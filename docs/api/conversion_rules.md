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

데이터셋 입력(`csv`, `xlsx`, `xls`, `tsv`, `txt`, `json`, `jsonl`, `xml`, `parquet`)은 `md`, `html`, `csv`, `xlsx`, `tsv`, `json`, `jsonl`, `xml`, `parquet`, `sql`을 허용합니다.

새 변환기를 추가할 때는 구현 분기와 함께 규칙 매트릭스, 출력 확장자, 미리보기 모드, 규칙 테스트를 동시에 갱신해야 합니다.

## 공공데이터 응답 구조와 양방향 변환

CSV/XLSX/XLS를 JSON 또는 XML로 변환할 때 기본 `dataset_profile=auto`는
`docs/adr/청주시cctv.json`·`.xml`의 응답 구조를 적용합니다. 청주시의 특정
컬럼·URL·건수는 복사하지 않습니다. 국가 공인 응답 표준 인증이나 운영 API 계약을 생성하는 기능은 아닙니다.

- JSON: `response.header`, `response.body`, `response.body.items[]`
- XML: `<response><header>…</header><body>…<items><item>…</item></items></body></response>`
- `totalCount`와 `numOfRows`는 선택한 입력의 실제 행 수, `pageNo`는 단일 배포 묶음의 0입니다.
  **새로 만드는 응답에만** 해당합니다. 기존 포털형 JSON/XML 응답은 전체 건수·페이지 번호·페이지 크기·헤더 및 추가 응답 메타데이터를 그대로 보존합니다.
  청주시 CCTV 예시는 전체 100,755건 중 1,000개 행이 담겨 있으므로 `totalCount`를 1,000으로 바꾸지 않습니다.
- `resultCode=00`, `resultMsg=NORMAL_CODE(정상)`은 로컬 파일 생성 성공 표기입니다. 실제 기관 API 호출 결과가 아닙니다.
- `dataset_profile=records`는 기존 JSON 레코드 배열·XML records/record/field 구조와 원천 컬럼명을 유지합니다.
  이 옵션은 CSV·엑셀 입력에만 적용합니다. JSON/XML 입력의 JSON·XML·CSV 출력은 원본 응답 구조 보존 경로로 고정하며, 이전 클라이언트가 `records`를 보내도 응답을 경로형 컬럼으로 평탄화하지 않습니다.
- JSON/XML 공공데이터 응답을 CSV로 다시 읽을 때는 body.items의 행을 읽고 응답 헤더를 데이터 컬럼으로 섞지 않습니다.

### 기본 변환 분기 (`dataset_profile=auto` 또는 `public_data`)

| 입력 | 출력 | 동작 |
| --- | --- | --- |
| CSV·XLSX·XLS | JSON·XML | 확인된 컬럼명으로 포털형 응답 생성 |
| XML | JSON | 포털 응답 또는 일반 레코드 구조를 읽고 포털형 JSON 생성 |
| JSON | XML | 동일한 응답 모델에서 items/item XML 생성 |
| JSON·XML | CSV | 응답 메타데이터를 제외한 데이터 행만 저장 |
| JSON·XML | JSON·XML | 기존 포털 응답의 헤더·페이지 정보를 보존하며 정규화 |

JSON의 레코드 배열, 단일 객체, `data.rows[]` 같은 래퍼, `items.item`의 단일 객체/배열을 지원합니다.
일반 XML의 반복 레코드, 단일 레코드 및 기존 `records/record/field` 구조도 지원합니다.
`response` 래퍼 없이 `header/body`가 바로 있는 응답도 정규화합니다. 기존 body/items 응답에서 헤더가 누락되면 null로 두며 기관 응답 성공 코드를 만들어 넣지 않습니다.
특정 CCTV 컬럼을 하드코딩하지 않으며 각 입력에서 필드를 읽습니다. 누락 키를 JSON/XML에 새로 삽입하지 않습니다.

객체 레코드 배열이 여러 곳에 있으면 임의로 선택하지 않고 HTTP 400과 후보 경로를 반환합니다.
화면의 데이터 목록 경로 또는 multipart `record_path`에 `/data/rows`, `/root/rows/row` 같은 JSON Pointer 경로를 입력합니다.
`~`는 `~0`, `/`가 포함된 키는 `~1`로 이스케이프합니다. 포털 응답의 경로는 `/response/body/items`로 고정합니다.
XML 경로는 XML을 객체로 읽은 트리 기준이며 루트 요소를 포함합니다. 네임스페이스 필드 키는 `{URI}이름`으로 구분합니다.
일반 JSON 객체 전체를 단일 레코드로 선택하려면 `record_path=$`를 지정합니다.
알려진 목록 래퍼가 아닌 단일 객체의 코드·이름 같은 단일 값과 함께 존재하는 내부 배열은 별도 레코드 목록으로 추출하지 않습니다.

### 값 보존과 한계

- CSV 구분자는 쉼표·세미콜론·탭·파이프 중 자동 감지하며 판별 실패 시 쉼표를 사용합니다. 헤더·행 길이 오류는 HTTP 400입니다.
- XML 업무 필드의 `001`, `false` 같은 텍스트를 숫자나 boolean으로 임의 추론하지 않습니다.
- 반복 요소는 배열, 중첩 요소는 객체, 속성은 `@이름`, 속성을 가진 요소의 텍스트는 `#text`로 보존합니다.
- JSON의 중첩 객체·배열을 XML로 직렬화할 때 `urn:synthetic-studio:json-types:v1`의 `type` 속성으로 배열·빈 객체·숫자·boolean을 구분합니다.
  이는 **로컬 왕복 변환용 확장**이며 정부 표준 속성이나 기관의 XSD 준수 인증이 아닙니다. 문자열만 있는 CCTV 업무 필드는 원래 요소 구조를 유지합니다.
- XML 이름으로 표현할 수 없는 JSON 키는 `<field name="원래 키">`로 보존합니다. XML null은 `xsi:nil="true"`입니다.
- CSV 중첩 셀은 유효한 JSON 텍스트로 저장합니다. 숫자 코드와 문자열의 공백은 보존합니다.
  CSV 자체는 원래 셀 타입·누락 키·null과 빈 문자열을 구분하지 못합니다. CSV를 다시 JSON으로 읽으면 셀은 문자열이며, 중첩 텍스트를 자동 재해석하지 않습니다.
- XML의 혼합 콘텐츠(요소 사이 본문 텍스트), DTD·엔터티 선언, JSON 중복 키·비유한 숫자, 과도한 중첩은 손실 변환 대신 오류로 반환합니다.
- 입력은 최대 100 MiB, XML은 최대 1,000,000개 노드, 구조화 중첩은 최대 128단계, 표는 최대 2,000,000개 셀입니다.

매핑 파일의 `response_metadata`는 응답 헤더·페이지 정보·추가 메타데이터를,
일반 래퍼 입력의 `source_metadata`는 선택한 데이터 목록 밖의 메타데이터를 보존합니다.
`response` 밖 최상위 JSON 메타데이터는 JSON 출력에는 유지하지만 XML 응답 루트에는 넣지 않고 매핑 파일에 저장합니다.
CSV 파일만으로 이 정보를 복원하지 않으며, 현재 매핑 파일을 재입력하여 타입·메타데이터를 복원하는 기능은 제공하지 않습니다.
변환 결과에 주의사항을 표시합니다. API의 `structured_preview` 요약은 첫 100개 행을 포함합니다.
웹 대조 화면은 이 요약을 원문으로 사용하지 않고 업로드 원본과 실제 다운로드 파일을 각각 읽습니다.
JSON·XML·JSONL·SQL·Markdown·TXT는 코드, CSV·TSV는 표/원문, 엑셀은 선택 시트의 표, HTML은 스크립트·외부 요청이 차단된 격리 뷰로 표시합니다.
JSON 표시용 공백 정리는 큰 정수·키 순서·문자열 값을 변경하지 않습니다. 원본 컬럼을 변환 후 이름으로 대체하지 않습니다.
텍스트 미리보기는 처음 2 MiB, 표는 최대 200개 데이터 행, 엑셀은 20 MiB 파일·512열까지 지원합니다.
Parquet는 서버 데이터 행의 표 요약을 제공하며 바이너리 원문을 JSON 코드로 위장하지 않습니다.

### 영문 변수명 추천과 사용자 확인

`POST /api/v1/converter/field-names`의 multipart 필드는 `file`, 선택적
`encoding`(UTF-8/CP949), `sheet_name`, `use_ai`(기본 true)입니다.
서버의 `OPENAI_API_KEY`가 설정되어 있으면 GPT-4o-mini의 구조화 출력으로
영문명을 추천합니다. 외부 모델에는 컬럼명과 인덱스만 보내며 데이터 셀 값·원천 파일은 보내지 않습니다.

추천 응답에는 원천명, 추천명, 검토 상태, `sourceType`, `confidence`, `reason`이 있습니다.
AI 추천은 `AUTO_INFERRED`, 원천의 유효한 영문명은 `AUTO_CONFIRMED`입니다.
키 미설정·추론 실패 시 `field1` 등의 수동 입력용 임시명은 `REVIEW_REQUIRED`이며
AI 추론 결과로 위장하지 않습니다. 평가하지 않은 신뢰도는 null입니다.

사용자는 추천명을 수정하고 확인 체크 후 변환합니다. 변환 요청의 추가 필드는 다음과 같습니다.

```json
{
  "dataset_profile": "public_data",
  "field_names": "{\"지역명\":\"regionName\",\"코드\":\"regionCode\"}",
  "field_names_confirmed": true,
  "sheet_name": "Sheet1"
}
```

위 항목들은 `/converter/convert`의 multipart Form 값입니다. `field_names`는 JSON 문자열입니다.
모든 컬럼을 정확히 한 번 매핑해야 하며 영문자로 시작하는 영문·숫자·밑줄 1~64자,
xml 접두사 제외, 대소문자를 무시한 중복 금지 규칙을 적용합니다.
수정·확인된 이름은 `USER_CONFIRMED`로 기록합니다. 사용자가 매핑을 제공하지 않았을 때는
모든 원천명이 이미 유효한 영문명인 경우만 그대로 자동 변환하고, 그 외에는 확인을 요청합니다.

엑셀은 첫 행을 헤더로 읽고 기본 첫 시트 또는 지정한 한 시트만 변환합니다.
시트 목록을 화면에 표시하며 다른 시트를 임의 결합하지 않습니다. XLS는 xlrd가 필요합니다.
CSV 값은 문자열로 유지하여 `001`, `NA`, 빈 문자열이 타입 추론으로 변형되지 않습니다.
엑셀 숫자·boolean·null은 JSON 원래 타입, 날짜는 ISO 8601 문자열로 보존합니다.
XLSX 수식은 평가하지 않은 원문, XLS 수식은 파일에 저장된 캐시 결과로 읽습니다. 수식을 실행하지 않습니다.
XML null은 `xsi:nil=true`, 빈 문자열은 빈 요소, boolean은 true/false로 표현합니다.
XML 1.0에서 허용하지 않는 제어문자는 손실 제거하지 않고 오류로 반환합니다.

확인된 원천명↔영문명 매핑은 출력 파일 옆의 `.field-mappings.json`에 저장합니다.
변환 응답의 `field_mapping_url` 및 화면의 매핑 다운로드 버튼으로 받을 수 있습니다.
