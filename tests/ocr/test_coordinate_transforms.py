# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_coordinate_transforms.py
# 경로: tests/ocr/test_coordinate_transforms.py
# 목적: OCR 바운딩 박스 기하 변환 및 좌표 보정 로직을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import pytest

from ocr.pipeline.models import BoundingBox
from ocr.preprocessing.transforms import CoordinateTransform, TransformMetadata


# assert 바운딩 박스 close 작업을 수행함
def assert_bbox_close(actual, expected, *, abs=1e-6):
    assert actual == pytest.approx(expected, abs=abs)


# scale 바운딩 박스 round trip 기능의 정상 동작 및 제약조건을 테스트함
def test_scale_bbox_round_trip():
    transform = CoordinateTransform.scale(2.0, 1.5, source_size=(100, 80), target_size=(200, 120))
    source = BoundingBox(10, 12, 30, 20)

    ocr_bbox = transform.transform_bbox(source)
    restored = transform.inverse_bbox(ocr_bbox)

    assert_bbox_close(ocr_bbox, (20, 18, 60, 30))
    assert_bbox_close(restored, (10, 12, 30, 20))


# affine 바운딩 박스 round trip 기능의 정상 동작 및 제약조건을 테스트함
def test_affine_bbox_round_trip():
    transform = CoordinateTransform.affine(
        [[1.25, 0.0, 8.0], [0.0, 0.75, -3.0]],
        source_size=(100, 80),
        target_size=(133, 57),
    )
    source = (14.0, 20.0, 32.0, 18.0)

    ocr_bbox = transform.transform_bbox(source)
    restored = transform.inverse_bbox(ocr_bbox)

    assert_bbox_close(ocr_bbox, (25.5, 12.0, 40.0, 13.5))
    assert_bbox_close(restored, source)


# homography 바운딩 박스 round trip 기능의 정상 동작 및 제약조건을 테스트함
def test_homography_bbox_round_trip():
    transform = CoordinateTransform.homography(
        [[1.1, 0.0, 5.0], [0.0, 0.9, 7.0], [0.0, 0.0, 1.0]],
        source_size=(100, 80),
        target_size=(115, 79),
    )
    source = (9.0, 11.0, 44.0, 17.0)

    ocr_bbox = transform.transform_bbox(source)
    restored = transform.inverse_bbox(ocr_bbox)

    assert_bbox_close(ocr_bbox, (14.9, 16.9, 48.4, 15.3))
    assert_bbox_close(restored, source)


# true projective homography point round trip 기능의 정상 동작 및 제약조건을 테스트함
def test_true_projective_homography_point_round_trip():
    transform = CoordinateTransform.homography(
        [[1.0, 0.1, 3.0], [0.05, 0.9, -2.0], [0.001, 0.002, 1.0]]
    )

    point = (33.0, 17.0)
    restored = transform.inverse_point(*transform.transform_point(*point))

    assert restored == pytest.approx(point, abs=1e-6)


# transform metadata composes 바운딩 박스 round trip 기능의 정상 동작 및 제약조건을 테스트함
def test_transform_metadata_composes_bbox_round_trip():
    metadata = TransformMetadata.identity((100, 80))
    metadata = metadata.append(
        CoordinateTransform.scale(2.0, 2.0, source_size=(100, 80), target_size=(200, 160))
    )
    metadata = metadata.append(
        CoordinateTransform.affine(
            [[1.0, 0.0, 4.0], [0.0, 1.0, -6.0]],
            source_size=(200, 160),
            target_size=(200, 160),
            name="translate",
        )
    )
    source = BoundingBox(7, 13, 21, 9)

    ocr_bbox = metadata.original_to_ocr_bbox(source)
    restored = metadata.ocr_to_original_bbox(ocr_bbox)

    assert metadata.coordinate_transform.source_size == (100, 80)
    assert metadata.coordinate_transform.target_size == (200, 160)
    assert_bbox_close(ocr_bbox, (18, 20, 42, 18))
    assert_bbox_close(restored, (7, 13, 21, 9))
