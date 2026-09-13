# OCR 샘플 표준화 규칙

`docs/New_sample`은 `라벨링데이터`와 `원천데이터`가 같은 상대 디렉터리 구조를 공유하는 박스 단위 OCR 데이터셋이다. 표준 로더는 원본 이미지나 라벨을 실행하지 않고 로컬 파일로만 읽는다.

## 고정한 규칙

- 라벨은 UTF-8 또는 UTF-8 BOM JSON이며 `images[0]`, `annotations[]` 구조를 사용한다.
- 이미지 매칭은 `원천데이터/<라벨 상대 디렉터리>/<image.file.name>`을 먼저 사용한다. 같은 파일명이 하나뿐일 때만 파일명 인덱스로 복구한다.
- 이미지 경로가 `원천데이터` 밖으로 나가면 오류다.
- `annotation.bbox`는 `[x, y, width, height]` 픽셀 좌표이고, 음수·0 크기·이미지 밖 좌표는 오류다.
- `annotation.type=rectangle`, `annotation.ttype=textType1`만 정식 입력으로 인정한다.
- annotation 배열 순번이 안정적인 식별자다. 공급자 `id`는 중복될 수 있으므로 메타데이터로만 보관한다.
- 원문 텍스트는 NFC만 적용하고 공백, 숫자, 날짜, 금액, 하이픈, 슬래시, 괄호, URL을 축약하거나 추측해 바꾸지 않는다.
- 읽기 순서는 Y축 행 그룹 후 X축 오름차순이다. 레이아웃 간격만으로 공백을 새로 만들지 않는다.
- 빈 텍스트는 버리지 않고 검토 경고로 남긴다.
- 원천 이미지 누락은 오류이며, 누락 샘플은 OCR 성공률에 포함하지 않는다.

현재 샘플 감사에서 발견된 중복 ID는 데이터 손실 없이 배열 순번으로 보존한다. 빈 라벨과 누락 이미지도 정답을 임의 생성하지 않고 품질 리포트에 남긴다.

## 감사 실행

```bash
python scripts/audit_ocr_samples.py docs/New_sample \
  --json-out output/ocr_sample_audit.json
```

학습/검증 코드가 같은 규칙을 사용하도록 원문 텍스트와 박스를 JSONL manifest로 내보낼 수 있다. 오류 샘플을 제외하려면 `--valid-only`를 사용한다.

```bash
python scripts/export_ocr_sample_manifest.py docs/New_sample \
  --valid-only --output output/ocr_sample_manifest.jsonl
```

빠른 smoke test는 `--limit 10`, 전체 baseline은 `--limit 0`을 사용한다.

```bash
OCR_ALLOW_MODEL_DOWNLOAD=false \
python scripts/benchmark_ocr_samples.py docs/New_sample \
  --limit 10 --output output/ocr_sample_benchmark.json
```

전체 baseline은 다음 네 파일을 생성한다.

```bash
OCR_ALLOW_MODEL_DOWNLOAD=false \
python scripts/benchmark_ocr_samples.py docs/New_sample \
  --limit 0 --max-attempts 1 --output-dir output/ocr-baseline
```

- `ocr_baseline_summary.json`: 전체 지표, 파일/이미지/annotation별 집계
- `ocr_baseline_errors.jsonl`: 오류 annotation 상세
- `ocr_baseline_worst_cases.json`: CER·bbox·고신뢰도·숫자·날짜·금액·특수기호 Top N
- `ocr_baseline_report.md`: 사람이 읽는 baseline 보고서

모델은 기존 `OCR_MODEL_DIR` 아래에만 저장하며, 클라우드 OCR/VLM이나 외부 업로드는 사용하지 않는다.

## Phase 2 검출·인식 재현

RapidOCR DB 검출 기본값은 샘플 전체 측정으로 확정한 다음 값이다. 환경변수로
덮어쓸 수 있지만, 비교 실험에서는 항상 값을 명시해 실행한다.

- `OCR_DET_BOX_THRESH=0.35`
- `OCR_DET_TEXT_THRESH=0.18`
- `OCR_DET_UNCLIP_RATIO=1.3`
- `OCR_DET_LIMIT_SIDE_LEN=960`
- `OCR_INPUT_PADDING=16`

Windows PowerShell에서 baseline과 Phase 2를 비교하려면 다음을 실행한다.

```powershell
$env:OCR_ALLOW_MODEL_DOWNLOAD = "false"
$env:OCR_DET_BOX_THRESH = "0.35"
$env:OCR_DET_TEXT_THRESH = "0.18"
$env:OCR_DET_UNCLIP_RATIO = "1.3"
$env:OCR_DET_LIMIT_SIDE_LEN = "960"
$env:OCR_INPUT_PADDING = "16"
.venv\Scripts\python.exe scripts\benchmark_ocr_samples.py docs\New_sample `
  --limit 0 --max-attempts 1 --top-n 20 `
  --output-dir output\ocr-phase2-final `
  --baseline-summary output\ocr-baseline\ocr_baseline_summary.json
```

Phase 2 출력은 `ocr_phase2_comparison.json`과
`ocr_phase2_comparison.md`에 baseline 대비 증감과 목표별 PASS/PARTIAL을
기록한다. 원본 라벨과 이미지는 수정하지 않는다.

## 폭 변형 OCR 재시도

문자의 가로 폭이 원본보다 늘어나거나 줄어든 스캔은 기본 OCR 1회 결과를
억지로 보정하지 않고, 일반 이미지 파이프라인의 재시도 단계에서 제한된
비등방성 후보를 사용한다. 세로 샘플링과 원본 텍스트는 유지하면서 x축만
변환한다.

- `HORIZONTAL_COMPRESSED`: 기본 `0.80`배
- `HORIZONTAL_EXPANDED`: 기본 `1.25`배
- `OCR_ASPECT_COMPRESS_SCALE`, `OCR_ASPECT_EXPAND_SCALE`로 각각 `0.55~1.80` 범위에서 조정
- 기본 `--max-attempts 1`인 데이터셋 baseline은 변하지 않는다.
- 일반 이미지 파이프라인 기본 재시도 예산은 7회이며, 품질별 전처리 후보 뒤에 폭 변형 후보를 추가한다.
- 폭 변형 결과의 BBox는 변환 이미지 좌표계와 크기를 `OCRPageResult`에 기록하고, benchmark가 원본 크기로 역스케일한다.

재현 예시는 다음과 같다.

```powershell
$env:OCR_ASPECT_COMPRESS_SCALE = "0.80"
$env:OCR_ASPECT_EXPAND_SCALE = "1.25"
.venv\Scripts\python.exe scripts\benchmark_ocr_samples.py docs\New_sample `
  --limit 10 --max-attempts 1 --output-dir output\ocr-aspect-smoke
```

폭 변형 재시도 자체를 확인하려면 이미지 파이프라인 호출에서
`max_attempts=7`을 사용한다. 원본 데이터셋과 라벨에는 아무것도 쓰지 않는다.
