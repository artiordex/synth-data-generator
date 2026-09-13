# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_model_manifest.py
# 경로: packages/synthetic_engine/tests/test_model_manifest.py
# 목적: 로컬 AI/ML 모델 매니페스트 등록 및 조회를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import json

import pytest

from synthetic_engine.model_manifest import (
    ModelManifestError,
    load_model_manifest,
    validate_model_manifest,
)


# 모델 매니페스트 records license and commercial review 기능의 정상 동작 및 제약조건을 테스트함
def test_model_manifest_records_license_and_commercial_review(tmp_path):
    model_file = tmp_path / 'ocr' / 'rapidocr' / 'model.onnx'
    model_file.parent.mkdir(parents=True)
    model_file.write_bytes(b'onnx')
    manifest = {
        'schema_version': 1,
        'models': [
            {
                'path': 'ocr/rapidocr/model.onnx',
                'license': 'Apache-2.0',
                'commercial_use_reviewed': True,
                'sha256': 'a' * 64,
            }
        ],
    }

    normalized = validate_model_manifest(
        manifest,
        base_dir=tmp_path,
        require_files=True,
    )

    assert normalized['models'][0]['license'] == 'Apache-2.0'
    assert normalized['models'][0]['commercial_use_reviewed'] is True
    assert normalized['models'][0]['path'] == 'ocr/rapidocr/model.onnx'


# 모델 매니페스트 rejects missing commercial review 기능의 정상 동작 및 제약조건을 테스트함
def test_model_manifest_rejects_missing_commercial_review():
    with pytest.raises(ModelManifestError, match='commercial_use_reviewed'):
        validate_model_manifest({
            'schema_version': 1,
            'models': [{'path': 'model.onnx', 'license': 'Apache-2.0'}],
        })


# 모델 매니페스트 rejects unsafe 경로 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_model_manifest_rejects_unsafe_paths():
    with pytest.raises(ModelManifestError, match='manifest-relative'):
        validate_model_manifest({
            'schema_version': 1,
            'models': [
                {
                    'path': '../model.onnx',
                    'license': 'Apache-2.0',
                    'commercial_use_reviewed': False,
                }
            ],
        })


# load 모델 매니페스트 validates json 파일 기능의 정상 동작 및 제약조건을 테스트함
def test_load_model_manifest_validates_json_file(tmp_path):
    manifest_path = tmp_path / 'models.json'
    manifest_path.write_text(
        json.dumps({
            'schema_version': 1,
            'models': [
                {
                    'path': 'ocr/easyocr/korean_g2.pth',
                    'license': 'Apache-2.0',
                    'commercial_use_reviewed': False,
                    'source': 'local-vendor-review-pending',
                }
            ],
        }),
        encoding='utf-8',
    )

    manifest = load_model_manifest(manifest_path)

    assert manifest['models'][0]['source'] == 'local-vendor-review-pending'
