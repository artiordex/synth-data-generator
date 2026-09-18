"""Data classes shared by OCR table reconstruction and document exporters.

The reconstruction pipeline historically declared these objects inside the
synthetic-engine exporter.  Keeping them in the OCR package gives all
consumers one owner while retaining the tuple-based coordinate representation
used by the legacy reconstruction algorithms.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ReconstructionOCRWord:
    text: str
    bbox: Tuple[int, int, int, int]
    confidence: float

    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2.0,
            (self.bbox[1] + self.bbox[3]) / 2.0,
        )


def _line_text(words: List[ReconstructionOCRWord]) -> str:
    return " ".join(word.text.strip() for word in words if word.text.strip()).strip()


@dataclass
class OCRTableCell:
    row: int
    col: int
    rowspan: int
    colspan: int
    bbox: Tuple[int, int, int, int]
    words: List[ReconstructionOCRWord] = field(default_factory=list)
    bg_color_hex: str = "#ffffff"
    border_styles: Dict[str, str] = field(default_factory=dict)
    text_align: str = "left"
    is_border_detected: bool = True
    confidence: float = 1.0
    control_type: Optional[str] = None
    control_state: Optional[str] = None
    figures: List["OCRFigureBlock"] = field(default_factory=list)
    borders: Dict[str, bool] = field(default_factory=dict)
    border_confidence: Dict[str, float] = field(default_factory=dict)
    grid_confidence: float = 1.0
    source: str = "ruled_legacy"

    @property
    def text(self) -> str:
        words = sorted(self.words, key=lambda word: (word.center[1], word.bbox[0]))
        return _line_text(words)


@dataclass
class OCRTable:
    bbox: Tuple[int, int, int, int]
    cells: List[OCRTableCell] = field(default_factory=list)
    rows_count: int = 0
    cols_count: int = 0
    x_lines: Tuple[int, ...] = ()
    y_lines: Tuple[int, ...] = ()
    grid_confidence: float = 1.0
    source: str = "ruled_legacy"

    def to_grid(self) -> List[List[str]]:
        grid = [["" for _ in range(self.cols_count)] for _ in range(self.rows_count)]
        for cell in self.cells:
            if cell.row < self.rows_count and cell.col < self.cols_count:
                grid[cell.row][cell.col] = cell.text
        return grid


@dataclass
class OCRTextBlock:
    text: str
    bbox: Tuple[int, int, int, int]
    is_heading: bool = False
    font_scale: float = 1.0


@dataclass
class OCRFigureBlock:
    bbox: Tuple[int, int, int, int]
    image_bytes: bytes
    format: str = "png"
    width: int = 0
    height: int = 0

    @property
    def base64_src(self) -> str:
        b64 = base64.b64encode(self.image_bytes).decode("ascii")
        mime = "image/jpeg" if self.format.lower() in ("jpg", "jpeg") else "image/png"
        return f"data:{mime};base64,{b64}"


@dataclass
class OCRPageResult:
    page_num: int
    width: int
    height: int
    tables: List[OCRTable] = field(default_factory=list)
    text_blocks: List[OCRTextBlock] = field(default_factory=list)
    figures: List[OCRFigureBlock] = field(default_factory=list)
    ocr_engine: str = ""
    mean_confidence: float = 0.0
    requires_review: bool = False
    warnings: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        parts = [block.text for block in self.text_blocks]
        for table in self.tables:
            parts.extend(" | ".join(row) for row in table.to_grid())
        return "\n".join(parts)


__all__ = [
    "OCRFigureBlock",
    "OCRPageResult",
    "OCRTable",
    "OCRTableCell",
    "OCRTextBlock",
    "ReconstructionOCRWord",
]
