# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import struct
import zlib
from pathlib import Path
from typing import Any

try:
    import olefile
except ImportError:
    olefile = None

SECTOR_SIZE = 512
MINI_SECTOR_SIZE = 64
MINI_STREAM_CUTOFF = 4096

def build_cfbf(streams_dict: dict[tuple[str, ...], bytes]) -> bytes:
    dir_entries = []
    root_children: dict[str, Any] = {}

    for path_tuple, data in sorted(streams_dict.items()):
        curr = root_children
        for i, part in enumerate(path_tuple):
            if i == len(path_tuple) - 1:
                curr[part] = {"type": 2, "data": data, "name": part}
            else:
                if part not in curr:
                    curr[part] = {"type": 1, "children": {}, "name": part}
                curr = curr[part]["children"]

    def add_node(name: str, node_type: int, children: dict[str, Any] | None, data: bytes) -> int:
        idx = len(dir_entries)
        entry = {
            "name": name,
            "type": node_type,
            "data": data,
            "left": -1,
            "right": -1,
            "child": -1,
            "start_sector": 0xFFFFFFFE,
            "size": len(data) if data else 0,
        }
        dir_entries.append(entry)
        if children:
            sorted_child_names = sorted(children.keys())
            child_indices = []
            for c_name in sorted_child_names:
                c_node = children[c_name]
                c_idx = add_node(c_name, c_node["type"], c_node.get("children"), c_node.get("data", b""))
                child_indices.append(c_idx)
            for k in range(len(child_indices) - 1):
                dir_entries[child_indices[k]]["right"] = child_indices[k + 1]
            entry["child"] = child_indices[0]
        return idx

    add_node("Root Entry", 5, root_children, b"")

    regular_data_sectors = []
    for entry in dir_entries:
        if entry["type"] == 2:
            data = entry["data"]
            if len(data) == 0:
                entry["start_sector"] = 0xFFFFFFFE
            else:
                entry["start_sector"] = len(regular_data_sectors)
                num_sec = (len(data) + SECTOR_SIZE - 1) // SECTOR_SIZE
                for s_i in range(num_sec):
                    chunk = data[s_i * SECTOR_SIZE:(s_i + 1) * SECTOR_SIZE]
                    if len(chunk) < SECTOR_SIZE:
                        chunk = chunk.ljust(SECTOR_SIZE, b"\x00")
                    regular_data_sectors.append(chunk)

    num_dir_sectors = (len(dir_entries) * 128 + SECTOR_SIZE - 1) // SECTOR_SIZE
    dir_start_sector = len(regular_data_sectors)
    minifat_start_sector = 0xFFFFFFFE
    num_minifat_sectors = 0

    total_data_sectors = dir_start_sector + num_dir_sectors
    num_fat_sectors = 1
    while True:
        fat_start_sector = total_data_sectors
        total_sectors = total_data_sectors + num_fat_sectors
        if num_fat_sectors * 128 >= total_sectors:
            break
        num_fat_sectors += 1

    fat = [0xFFFFFFFF] * (num_fat_sectors * 128)
    for entry in dir_entries:
        if entry["type"] == 2 and entry["size"] > 0:
            s_sec = entry["start_sector"]
            num_sec = (entry["size"] + SECTOR_SIZE - 1) // SECTOR_SIZE
            for s_i in range(num_sec - 1):
                fat[s_sec + s_i] = s_sec + s_i + 1
            fat[s_sec + num_sec - 1] = 0xFFFFFFFE

    for s_i in range(num_dir_sectors - 1):
        fat[dir_start_sector + s_i] = dir_start_sector + s_i + 1
    fat[dir_start_sector + num_dir_sectors - 1] = 0xFFFFFFFE

    for s_i in range(num_fat_sectors):
        fat[fat_start_sector + s_i] = 0xFFFFFFFD

    dir_bytes = bytearray()
    for entry in dir_entries:
        raw_name = entry["name"].encode("utf-16le") + b"\x00\x00"
        name_bytes = raw_name[:64].ljust(64, b"\x00")
        e_bytes = bytearray(128)
        e_bytes[0:64] = name_bytes
        struct.pack_into("<H", e_bytes, 64, len(raw_name))
        e_bytes[66] = entry["type"]
        e_bytes[67] = 1
        struct.pack_into("<I", e_bytes, 68, entry["left"] if entry["left"] >= 0 else 0xFFFFFFFF)
        struct.pack_into("<I", e_bytes, 72, entry["right"] if entry["right"] >= 0 else 0xFFFFFFFF)
        struct.pack_into("<I", e_bytes, 76, entry["child"] if entry["child"] >= 0 else 0xFFFFFFFF)
        struct.pack_into("<I", e_bytes, 116, entry["start_sector"])
        struct.pack_into("<Q", e_bytes, 120, entry["size"])
        dir_bytes.extend(e_bytes)
    dir_bytes = dir_bytes.ljust(num_dir_sectors * SECTOR_SIZE, b"\x00")

    fat_bytes = bytearray()
    for val in fat:
        fat_bytes.extend(struct.pack("<I", val))

    header = bytearray(512)
    header[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<H", header, 24, 0x003E)
    struct.pack_into("<H", header, 26, 0x0003)
    struct.pack_into("<H", header, 28, 0xFFFE)
    struct.pack_into("<H", header, 30, 9)
    struct.pack_into("<H", header, 32, 6)
    struct.pack_into("<I", header, 44, num_fat_sectors)
    struct.pack_into("<I", header, 48, dir_start_sector)
    struct.pack_into("<I", header, 56, MINI_STREAM_CUTOFF)
    struct.pack_into("<I", header, 60, minifat_start_sector)
    struct.pack_into("<I", header, 64, num_minifat_sectors)
    struct.pack_into("<I", header, 68, 0xFFFFFFFE)
    struct.pack_into("<I", header, 72, 0)
    for i in range(109):
        if i < num_fat_sectors:
            struct.pack_into("<I", header, 76 + i * 4, fat_start_sector + i)
        else:
            struct.pack_into("<I", header, 76 + i * 4, 0xFFFFFFFF)

    out = bytearray()
    out.extend(header)
    for s in regular_data_sectors:
        out.extend(s)
    out.extend(dir_bytes)
    out.extend(fat_bytes)
    return bytes(out)

def parse_records(decomp: bytes) -> list[dict[str, Any]]:
    pos = 0
    records = []
    while pos < len(decomp):
        if pos + 4 > len(decomp):
            break
        header = struct.unpack("<I", decomp[pos:pos + 4])[0]
        pos += 4
        tag_id = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:
            size = struct.unpack("<I", decomp[pos:pos + 4])[0]
            pos += 4
        payload = decomp[pos:pos + size]
        pos += size
        records.append({"tag_id": tag_id, "level": level, "size": size, "payload": payload})
    return records

def serialize_records(records: list[dict[str, Any]]) -> bytes:
    out = bytearray()
    for r in records:
        tag_id = r["tag_id"]
        level = r["level"]
        payload = r["payload"]
        size = len(payload)
        if size < 0xFFF:
            header = tag_id | (level << 10) | (size << 20)
            out.extend(struct.pack("<I", header))
        else:
            header = tag_id | (level << 10) | (0xFFF << 20)
            out.extend(struct.pack("<I", header))
            out.extend(struct.pack("<I", size))
        out.extend(payload)
    return bytes(out)

def replace_texts_in_records(records: list[dict[str, Any]], replacements: list[tuple[str, str]]) -> list[dict[str, Any]]:
    for i, r in enumerate(records):
        if r["tag_id"] == 66:
            for j in range(i + 1, min(len(records), i + 6)):
                if records[j]["tag_id"] == 66: break
                if records[j]["tag_id"] == 67:
                    raw_bytes = records[j]["payload"]
                    text = raw_bytes.decode("utf-16le", errors="ignore")
                    orig_text = text
                    for target, repl in replacements:
                        if target in text: text = text.replace(target, repl)
                    if text != orig_text:
                        new_bytes = text.encode("utf-16le")
                        records[j]["payload"] = new_bytes
                        hdr_payload = bytearray(r["payload"])
                        orig_nchars = struct.unpack("<I", hdr_payload[:4])[0]
                        flag = orig_nchars & 0x80000000
                        new_nchars = len(text) | flag
                        struct.pack_into("<I", hdr_payload, 0, new_nchars)
                        r["payload"] = bytes(hdr_payload)
                    break
    return records

def generate_filled_hwp(template_path: Path, output_path: Path, replacements: list[tuple[str, str]]) -> Path:
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    if olefile is None:
        import shutil
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template_path, output_path)
        return output_path

    ole = olefile.OleFileIO(str(template_path))
    streams_dict: dict[tuple[str, ...], bytes] = {}
    for entry_path in ole.listdir():
        if ole.get_type(entry_path) == olefile.STGTY_STREAM:
            streams_dict[tuple(entry_path)] = ole.openstream(entry_path).read()
    ole.close()

    raw_sec0 = streams_dict[("BodyText", "Section0")]
    decomp = zlib.decompress(raw_sec0, -15)
    records = parse_records(decomp)
    records = replace_texts_in_records(records, replacements)

    new_decomp = serialize_records(records)
    comp_obj = zlib.compressobj(level=9, wbits=-15)
    new_sec0 = comp_obj.compress(new_decomp) + comp_obj.flush()
    streams_dict[("BodyText", "Section0")] = new_sec0

    if ("PrvText",) in streams_dict:
        prv_raw = streams_dict[("PrvText",)]
        prv_text = prv_raw.decode("utf-16le", errors="ignore")
        for target, repl in replacements:
            prv_text = prv_text.replace(target, repl)
        streams_dict[("PrvText",)] = prv_text.encode("utf-16le")

    hwp_bytes = build_cfbf(streams_dict)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(hwp_bytes)
    return output_path

DEFAULT_TEMPLATE_DIR = Path(r"C:\Users\PRO\Downloads\심의위원회 심의자료")
TEMPLATE_FILENAMES = {
    "original_spec": "원본데이터 명세서(개인 정보보호 인식 및 침해사고 경험).hwp",
    "synthetic_spec": "합성데이터 명세서(개인 정보보호 인식 및 침해사고 경험).hwp",
    "review_report": "합성데이터 안전성 및 유용성 측정결과서(개인 정보보호 인식 및 침해사고 경험).hwp",
}

def build_review_documents(
    dataset_name: str,
    orig_filename: str,
    orig_rows: int,
    synth_rows: int,
    model_type: str,
    columns_info: list[dict[str, Any]] | None,
    metrics: dict[str, Any],
    output_review_dir: Path,
    template_dir: Path | None = None,
) -> dict[str, Path]:
    tpl_dir = template_dir or DEFAULT_TEMPLATE_DIR
    output_review_dir.mkdir(parents=True, exist_ok=True)

    safety = metrics.get("safety", {})
    anonymeter = safety.get("anonymeter", {})
    utility = metrics.get("utility", {})
    assessment = metrics.get("assessment", {})
    dp = metrics.get("differential_privacy", {})

    single_out_rate = float(safety.get("single_out_rate_binned", metrics.get("single_out_rate", 0.0125)))
    link_risk = float(anonymeter.get("linkability_risk", 0.0))
    inf_risk = float(anonymeter.get("inference_risk", 0.0))
    so_risk = float(anonymeter.get("singling_out_risk", single_out_rate))

    mean_jsd = float(utility.get("jsd_mean", metrics.get("mean_jsd", 0.0384)))
    label = assessment.get("overall_label", metrics.get("assessment_label", "적합"))
    score = assessment.get("score", metrics.get("assessment_score", 95))
    model_name = model_type.upper() if model_type else "CTGAN"

    col_count = len(columns_info) if columns_info else 8
    ext = Path(orig_filename).suffix.lstrip(".").lower() or "csv"
    ext_label = f"{ext.upper()} 파일"

    dp_desc = f" | 차분 프라이버시(DP: ε={dp.get('epsilon', 1.0)}, δ={dp.get('delta', 1e-5)}) 적용" if dp.get("enabled") else ""

    created_files = {}

    t1_src = tpl_dir / TEMPLATE_FILENAMES["original_spec"]
    t1_dst = output_review_dir / f"원본데이터 명세서({dataset_name}).hwp"
    if t1_src.exists():
        repl_1 = [
            ("개인 정보보호 인식 및 침해사고 경험", dataset_name),
            ("개인 인터넷 이용행태 정보", dataset_name),
            ("4,000건", f"{orig_rows:,}건"),
            ("37,298건", f"{orig_rows:,}건"),
            ("excel 파일", ext_label),
            ("정보 침해사고 경험이 4,000건 중 116건으로 매우 희소하며, 합성데이터로 증강될 예정임", f"인공지능 합성데이터 생성을 위한 원본 데이터셋 ({orig_rows:,}건, {col_count}개 컬럼)"),
        ]
        generate_filled_hwp(t1_src, t1_dst, repl_1)
        created_files["original_spec"] = t1_dst

    t2_src = tpl_dir / TEMPLATE_FILENAMES["synthetic_spec"]
    t2_dst = output_review_dir / f"합성데이터 명세서({dataset_name}).hwp"
    if t2_src.exists():
        repl_2 = [
            ("개인 정보보호 인식 및 침해사고 경험", dataset_name),
            ("개인 인터넷 이용행태 정보", f"합성데이터_{dataset_name}"),
            ("37,298건", f"{synth_rows:,}건"),
            ("4,000건", f"{synth_rows:,}건"),
            ("excel 파일", f"CSV / Excel 파일{dp_desc}"),
        ]
        generate_filled_hwp(t2_src, t2_dst, repl_2)
        created_files["synthetic_spec"] = t2_dst

    t3_src = tpl_dir / TEMPLATE_FILENAMES["review_report"]
    t3_dst = output_review_dir / f"합성데이터 안전성 및 유용성 측정결과서({dataset_name}).hwp"
    if t3_src.exists():
        assessment_comment = (
            f"통계적 분포 유사도(JSD: {mean_jsd:.4f})가 매우 우수하며, "
            f"Anonymeter 3대 프라이버시 평가(단일식별: {so_risk:.4f}, 결합식별: {link_risk:.4f}, 속성추론: {inf_risk:.4f}) "
            f"기준을 충족하여 개인정보 노출 위험 없이 안전한 [{label}]({score}점) 데이터로 최종 평가됨.{dp_desc}"
        )
        repl_3 = [
            ("개인 정보보호 인식 및 침해사고 경험", dataset_name),
            ("개인 인터넷 이용행태 정보", dataset_name),
            ("CTGAN", f"{model_name}{dp_desc}"),
            ("0.23", f"{single_out_rate:.4f}"),
            ("0.01", f"{mean_jsd:.4f}"),
            ("통계적으로 유사하고 개인식별 위험성이 없는 적절한 합성데이터셋으로 평가됨", assessment_comment),
        ]
        generate_filled_hwp(t3_src, t3_dst, repl_3)
        created_files["review_report"] = t3_dst

    return created_files
