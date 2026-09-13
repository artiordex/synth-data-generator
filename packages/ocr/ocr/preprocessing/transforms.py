# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: transforms.py
# 경로: packages/ocr/ocr/preprocessing/transforms.py
# 목적: 기울기 보정, 회전, 크기 재조정 등 기하학적 이미지 변환을 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Coordinate transform metadata for OCR preprocessing."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Protocol

import numpy as np


class BoundingBoxLike(Protocol):
    """Minimal bbox protocol shared by OCR model objects and tests."""

    x: float
    y: float
    width: float
    height: float


BBoxInput = BoundingBoxLike | tuple[float, float, float, float]
BBox = tuple[float, float, float, float]
Size = tuple[int, int]
Matrix = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


@dataclass(frozen=True)
class CoordinateTransform:
    """Project points and boxes between original and OCR image spaces."""

    matrix: Matrix
    name: str = "custom"
    source_size: Size | None = None
    target_size: Size | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    # identity 작업을 수행함
    @classmethod
    def identity(
        cls,
        *,
        size: Size | None = None,
        name: str = "identity",
        parameters: dict[str, Any] | None = None,
    ) -> "CoordinateTransform":
        return cls(
            matrix=_to_matrix(np.eye(3, dtype=float)),
            name=name,
            source_size=size,
            target_size=size,
            parameters=parameters or {},
        )

    # scale 작업을 수행함
    @classmethod
    def scale(
        cls,
        sx: float,
        sy: float | None = None,
        *,
        source_size: Size | None = None,
        target_size: Size | None = None,
        name: str = "scale",
        parameters: dict[str, Any] | None = None,
    ) -> "CoordinateTransform":
        if sy is None:
            sy = sx
        _require_finite("sx", sx)
        _require_finite("sy", sy)
        if sx <= 0.0 or sy <= 0.0:
            raise ValueError("scale factors must be positive")
        return cls(
            matrix=_to_matrix(np.array([[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]], dtype=float)),
            name=name,
            source_size=source_size,
            target_size=target_size,
            parameters=parameters or {"sx": sx, "sy": sy},
        )

    # affine 작업을 수행함
    @classmethod
    def affine(
        cls,
        matrix: Any,
        *,
        source_size: Size | None = None,
        target_size: Size | None = None,
        name: str = "affine",
        parameters: dict[str, Any] | None = None,
    ) -> "CoordinateTransform":
        return cls(
            matrix=_normalize_matrix(matrix, expected_rows=(2, 3)),
            name=name,
            source_size=source_size,
            target_size=target_size,
            parameters=parameters or {},
        )

    # homography 작업을 수행함
    @classmethod
    def homography(
        cls,
        matrix: Any,
        *,
        source_size: Size | None = None,
        target_size: Size | None = None,
        name: str = "homography",
        parameters: dict[str, Any] | None = None,
    ) -> "CoordinateTransform":
        return cls(
            matrix=_normalize_matrix(matrix, expected_rows=(3,)),
            name=name,
            source_size=source_size,
            target_size=target_size,
            parameters=parameters or {},
        )

    # then 작업을 수행함
    def then(
        self,
        next_transform: "CoordinateTransform",
        *,
        name: str | None = None,
    ) -> "CoordinateTransform":
        """Return a transform that applies this transform, then the next one."""

        matrix = _as_array(next_transform.matrix) @ _as_array(self.matrix)
        return CoordinateTransform(
            matrix=_to_matrix(matrix),
            name=name or f"{self.name}+{next_transform.name}",
            source_size=self.source_size,
            target_size=next_transform.target_size,
            parameters={},
        )

    # inverse 작업을 수행함
    def inverse(self, *, name: str | None = None) -> "CoordinateTransform":
        """Return the inverse coordinate transform."""

        matrix = _as_array(self.matrix)
        try:
            inverse = np.linalg.inv(matrix)
        except np.linalg.LinAlgError as exc:
            raise ValueError("coordinate transform is not invertible") from exc
        return CoordinateTransform(
            matrix=_to_matrix(inverse),
            name=name or f"{self.name}:inverse",
            source_size=self.target_size,
            target_size=self.source_size,
            parameters=self.parameters,
        )

    # transform point 작업을 수행함
    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        """Map one point through the transform."""

        _require_finite("x", x)
        _require_finite("y", y)
        result = _as_array(self.matrix) @ np.array([x, y, 1.0], dtype=float)
        weight = float(result[2])
        if not isfinite(weight) or abs(weight) < 1e-12:
            raise ValueError("homogeneous coordinate is not finite")
        return float(result[0] / weight), float(result[1] / weight)

    # inverse point 작업을 수행함
    def inverse_point(self, x: float, y: float) -> tuple[float, float]:
        """Map one point through the inverse transform."""

        return self.inverse().transform_point(x, y)

    # transform 바운딩 박스 작업을 수행함
    def transform_bbox(self, bbox: BBoxInput) -> BBox:
        """Map an axis-aligned bbox and return the enclosing axis-aligned bbox."""

        x, y, width, height = _bbox_values(bbox)
        if width < 0.0 or height < 0.0:
            raise ValueError("bbox width and height must be non-negative")
        points = (
            self.transform_point(x, y),
            self.transform_point(x + width, y),
            self.transform_point(x + width, y + height),
            self.transform_point(x, y + height),
        )
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        left = min(xs)
        top = min(ys)
        return left, top, max(xs) - left, max(ys) - top

    # inverse 바운딩 박스 작업을 수행함
    def inverse_bbox(self, bbox: BBoxInput) -> BBox:
        """Map a bbox through the inverse transform."""

        return self.inverse().transform_bbox(bbox)


@dataclass(frozen=True)
class TransformMetadata:
    """Applied preprocessing transforms from original to OCR image space."""

    original_size: Size | None = None
    ocr_size: Size | None = None
    transforms: tuple[CoordinateTransform, ...] = ()

    # identity 작업을 수행함
    @classmethod
    def identity(cls, size: Size | None = None) -> "TransformMetadata":
        return cls(original_size=size, ocr_size=size, transforms=())

    # 좌표 transform 작업을 수행함
    @property
    def coordinate_transform(self) -> CoordinateTransform:
        if not self.transforms:
            return CoordinateTransform.identity(size=self.original_size)
        combined = self.transforms[0]
        for transform in self.transforms[1:]:
            combined = combined.then(transform)
        return CoordinateTransform(
            matrix=combined.matrix,
            name="composite",
            source_size=self.original_size,
            target_size=self.ocr_size,
            parameters={},
        )

    # append 작업을 수행함
    def append(self, transform: CoordinateTransform) -> "TransformMetadata":
        return TransformMetadata(
            original_size=self.original_size or transform.source_size,
            ocr_size=transform.target_size or self.ocr_size,
            transforms=(*self.transforms, transform),
        )

    # original to OCR 인식 바운딩 박스 작업을 수행함
    def original_to_ocr_bbox(self, bbox: BBoxInput) -> BBox:
        return self.coordinate_transform.transform_bbox(bbox)

    # OCR 인식 to original 바운딩 박스 작업을 수행함
    def ocr_to_original_bbox(self, bbox: BBoxInput) -> BBox:
        return self.coordinate_transform.inverse_bbox(bbox)


# matrix 데이터를 표준 형식으로 정규화함
def _normalize_matrix(matrix: Any, *, expected_rows: tuple[int, ...]) -> Matrix:
    array = np.array(matrix, dtype=float)
    if array.shape == (2, 3) and 2 in expected_rows:
        array = np.vstack([array, np.array([0.0, 0.0, 1.0])])
    elif array.shape != (3, 3) or 3 not in expected_rows:
        expected = " or ".join(f"{rows}x3" for rows in expected_rows)
        raise ValueError(f"matrix must be {expected}")
    return _to_matrix(array)


# matrix 형식으로 변환하여 반환함
def _to_matrix(array: np.ndarray) -> Matrix:
    if array.shape != (3, 3):
        raise ValueError("matrix must be 3x3")
    if not np.all(np.isfinite(array)):
        raise ValueError("matrix values must be finite")
    return tuple(tuple(float(value) for value in row) for row in array)  # type: ignore[return-value]


# as array 작업을 수행함
def _as_array(matrix: Matrix) -> np.ndarray:
    return np.array(matrix, dtype=float)


# 바운딩 박스 values 작업을 수행함
def _bbox_values(bbox: BBoxInput) -> BBox:
    if hasattr(bbox, "x") and hasattr(bbox, "y") and hasattr(bbox, "width") and hasattr(bbox, "height"):
        values = (bbox.x, bbox.y, bbox.width, bbox.height)
    else:
        values = bbox
    try:
        x, y, width, height = (float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError("bbox must contain x, y, width and height") from exc
    for name, value in zip(("x", "y", "width", "height"), (x, y, width, height)):
        _require_finite(name, value)
    return x, y, width, height


# require finite 작업을 수행함
def _require_finite(name: str, value: float) -> None:
    if not isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
