# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Optional, Dict, List
import pandas as pd


class SmartMasker:
    """
    Format-preserving smart de-identification & masking engine according to
    Korean Personal Information Protection Act (PIPA) and Personal Information Protection Commission (PIPC) guidelines.
    """

    # Regex patterns for auto-detecting PII format from values
    PATTERNS = {
        "ssn": re.compile(r"^(?P<front>\d{6})[-\s]?(?P<gender>[1-8])(?P<back>\d{6})$"),
        "ssn_front_only": re.compile(r"^(?P<front>\d{6})[-\s]?(?P<gender>[1-8])$"),
        "phone_mobile": re.compile(r"^(?P<prefix>01[016789])[-\s]?(?P<mid>\d{3,4})[-\s]?(?P<last>\d{4})$"),
        "phone_tel": re.compile(r"^(?P<prefix>02|0[3-6][1-5])[-\s]?(?P<mid>\d{3,4})[-\s]?(?P<last>\d{4})$"),
        "email": re.compile(r"^(?P<id>[^@\s]+)@(?P<domain>[^@\s]+\.[^@\s]+)$"),
        "business_no": re.compile(r"^(?P<p1>\d{3})[-\s]?(?P<p2>\d{2})[-\s]?(?P<p3>\d{5})$"),
        "corporate_no": re.compile(r"^(?P<p1>\d{6})[-\s]?(?P<p2>\d{7})$"),
        "credit_card": re.compile(r"^(?P<p1>\d{4})[-\s]?(?P<p2>\d{2,4})[-\s]?(?P<p3>\d{2,4})[-\s]?(?P<p4>\d{4})$"),
        "driver_license": re.compile(r"^(?P<region>\d{2})[-\s]?(?P<yy>\d{2})[-\s]?(?P<serial>\d{6})[-\s]?(?P<chk>\d{2})$"),
        "passport": re.compile(r"^(?P<letter>[a-zA-Z])(?P<digits>\d{7,8})$"),
        "car_plate": re.compile(r"^(?P<num>\d{2,3})(?P<hangul>[가-힣])\s?(?P<tail>\d{4})$"),
        "ip_address": re.compile(r"^(?P<o1>\d{1,3})\.(?P<o2>\d{1,3})\.(?P<o3>\d{1,3})\.(?P<o4>\d{1,3})$"),
        "mac_address": re.compile(r"^(?P<b1>[0-9A-Fa-f]{2})[:-](?P<b2>[0-9A-Fa-f]{2})[:-](?P<b3>[0-9A-Fa-f]{2})[:-](?P<b4>[0-9A-Fa-f]{2})[:-](?P<b5>[0-9A-Fa-f]{2})[:-](?P<b6>[0-9A-Fa-f]{2})$"),
        "uuid": re.compile(r"^(?P<g1>[0-9a-fA-F]{8})-(?P<g2>[0-9a-fA-F]{4})-(?P<g3>[0-9a-fA-F]{4})-(?P<g4>[0-9a-fA-F]{4})-(?P<g5>[0-9a-fA-F]{12})$"),
        "date_iso": re.compile(r"^(?P<year>\d{4})[-/.](?P<month>\d{1,2})[-/.](?P<day>\d{1,2})$"),
        "tracking_no": re.compile(r"^(?P<p1>\d{3,4})[-\s]?(?P<p2>\d{3,4})[-\s]?(?P<p3>\d{4})$"),
        "order_no": re.compile(r"^(?P<date>\d{8})[-\s]?(?P<serial>[0-9A-Za-z]{4,8})$"),
        "health_ins": re.compile(r"^(?P<type>\d{1})[-\s]?(?P<mid>\d{8,9})[-\s]?(?P<chk>\d{1})$"),
        "military_no": re.compile(r"^(?P<yy>\d{2})[-\s]?(?P<serial>\d{6,8})$"),
        "pnu": re.compile(r"^(?P<adm>\d{10})(?P<type>\d{1})(?P<bon>\d{4})(?P<bu>\d{4})$"),
    }

    @classmethod
    def mask_ssn(cls, text: str, mask_char: str = "*") -> str:
        """
        주민등록번호 / 외국인등록번호: 생년월일 6자리와 성별 뒷자리 1자리까지 노출, 뒤 6자리 마스킹
        예: 900101-1234567 -> 900101-1******
            9001011234567 -> 9001011******
        """
        clean = text.strip()
        m = cls.PATTERNS["ssn"].match(clean)
        if m:
            front = m.group("front")
            gender = m.group("gender")
            has_dash = "-" in clean
            tail = mask_char * 6
            return f"{front}-{gender}{tail}" if has_dash else f"{front}{gender}{tail}"
        
        # If already partially masked (e.g. 900101-1******)
        if re.match(r"^\d{6}[-\s]?[1-8][*\s]{1,6}$", clean):
            parts = clean.replace(" ", "-").split("-")
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1][0]}{mask_char * 6}"

        # 13 digits raw
        digits = re.sub(r"\D", "", clean)
        if len(digits) == 13:
            return f"{digits[:6]}-{digits[6]}{mask_char * 6}"
        elif len(digits) >= 7:
            return f"{digits[:6]}-{digits[6]}{mask_char * (len(digits) - 7)}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_phone(cls, text: str, mask_char: str = "*", mask_position: str = "mid") -> str:
        """
        전화번호/휴대폰번호:
        기본 (가운데 마스킹): 010-1234-5678 -> 010-****-5678, 02-123-4567 -> 02-***-4567
        뒷자리 마스킹 옵션: 010-1234-****
        """
        clean = text.strip()
        m = cls.PATTERNS["phone_mobile"].match(clean) or cls.PATTERNS["phone_tel"].match(clean)
        if m:
            prefix = m.group("prefix")
            mid = m.group("mid")
            last = m.group("last")
            has_dash = "-" in clean
            
            if mask_position == "last":
                masked_last = mask_char * len(last)
                return f"{prefix}-{mid}-{masked_last}" if has_dash else f"{prefix}{mid}{masked_last}"
            else:
                masked_mid = mask_char * len(mid)
                return f"{prefix}-{masked_mid}-{last}" if has_dash else f"{prefix}{masked_mid}{last}"

        # Digits fallback
        digits = re.sub(r"\D", "", clean)
        if len(digits) == 11 and digits.startswith("01"):
            return f"{digits[:3]}-{mask_char * 4}-{digits[7:]}"
        elif len(digits) == 10 and digits.startswith("01"):
            return f"{digits[:3]}-{mask_char * 3}-{digits[6:]}"
        elif len(digits) >= 9:
            return f"{digits[:3]}-{mask_char * 4}-{digits[-4:]}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_name(cls, text: str, mask_char: str = "*") -> str:
        """
        이름 / 성명:
        - 2글자: 성 + * (예: 김철 -> 김*)
        - 3글자: 성 + * + 끝글자 (예: 홍길동 -> 홍*동)
        - 4글자: 앞 1자 + ** + 끝글자 (예: 남궁선우 -> 남**우)
        - 영문: 앞글자 + *** + 뒷글자 (예: John Doe -> J*** D**)
        """
        clean = text.strip()
        if not clean:
            return clean

        # Korean Name
        if re.match(r"^[가-힣]+$", clean):
            length = len(clean)
            if length <= 1:
                return clean
            elif length == 2:
                return f"{clean[0]}{mask_char}"
            elif length == 3:
                return f"{clean[0]}{mask_char}{clean[2]}"
            elif length == 4:
                return f"{clean[0]}{mask_char * 2}{clean[3]}"
            else:
                return f"{clean[:1]}{mask_char * (length - 2)}{clean[-1:]}"

        # Foreign / Multi-word Name (e.g. John Doe)
        words = clean.split()
        if len(words) > 1:
            masked_words = []
            for w in words:
                if len(w) <= 2:
                    masked_words.append(f"{w[0]}{mask_char}" if len(w) == 2 else w)
                else:
                    masked_words.append(f"{w[0]}{mask_char * (len(w) - 2)}{w[-1]}")
            return " ".join(masked_words)

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_email(cls, text: str, mask_char: str = "*") -> str:
        """
        이메일: ID 앞 2~3글자 노출 후 마스킹, 도메인 보존
        예: honggildong@domain.com -> hon***@domain.com
            abc@domain.com -> ab*@domain.com
            a@domain.com -> *@domain.com
        """
        clean = text.strip()
        m = cls.PATTERNS["email"].match(clean)
        if m:
            email_id = m.group("id")
            domain = m.group("domain")
            id_len = len(email_id)
            if id_len <= 2:
                masked_id = f"{email_id[0]}{mask_char * (id_len - 1)}" if id_len > 1 else mask_char
            elif id_len <= 5:
                masked_id = f"{email_id[:2]}{mask_char * (id_len - 2)}"
            else:
                masked_id = f"{email_id[:3]}{mask_char * (min(id_len - 3, 5))}"
            return f"{masked_id}@{domain}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_address(cls, text: str, mask_char: str = "*") -> str:
        """
        주소: 시/도, 시/군/구, 읍/면/동 또는 도로명까지 보존, 상세 번지/건물번호/동호수 마스킹
        예: 서울특별시 강남구 테헤란로 152 23층 -> 서울특별시 강남구 테헤란로 *** ***
            경기도 성남시 분당구 판교역로 235 N동 402호 -> 경기도 성남시 분당구 판교역로 *** ***
        """
        clean = text.strip().replace("\n", " ")
        parts = [p for p in clean.split() if p]
        if len(parts) <= 2:
            return f"{parts[0]} {mask_char * 3}" if parts else clean

        # Keep up to road name / dong (typically first 3 to 4 tokens)
        keep_tokens = []
        mask_tokens = []
        found_road_or_dong = False

        for idx, token in enumerate(parts):
            keep_tokens.append(token)
            if re.search(r"(로|길|동|리|가|면|읍)$", token) or re.search(r"(대로|로\d*길)$", token):
                found_road_or_dong = True
                mask_tokens = parts[idx + 1:]
                break

        if found_road_or_dong and mask_tokens:
            masked_tail = " ".join([mask_char * 3 for _ in mask_tokens])
            return f"{' '.join(keep_tokens)} {masked_tail}".strip()

        # Fallback: keep first 3 tokens, mask the rest
        if len(parts) >= 3:
            return f"{' '.join(parts[:3])} {' '.join([mask_char * 3 for _ in parts[3:]])}".strip()

        return f"{parts[0]} {mask_char * 3}"

    @classmethod
    def mask_account(cls, text: str, mask_char: str = "*") -> str:
        """
        계좌번호: 앞 3~4자리와 뒷 3~4자리 노출, 중간 마스킹
        예: 110-123-456789 -> 110-***-***789
            352-1234-5678-03 -> 352-****-****-03
        """
        clean = text.strip()
        parts = clean.split("-")
        if len(parts) >= 3:
            # Mask middle parts
            new_parts = [parts[0]]
            for p in parts[1:-1]:
                new_parts.append(mask_char * len(p))
            new_parts.append(parts[-1])
            return "-".join(new_parts)

        digits = re.sub(r"\D", "", clean)
        if len(digits) >= 8:
            return f"{digits[:3]}{mask_char * (len(digits) - 6)}{digits[-3:]}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_credit_card(cls, text: str, mask_char: str = "*") -> str:
        """
        신용카드 번호 (PCI-DSS 표준): 앞 6자리(BIN) 및 끝 4자리 노출, 중간 6자리 마스킹
        예: 1234-5678-9012-3456 -> 1234-56**-****-3456
        """
        clean = text.strip()
        m = cls.PATTERNS["credit_card"].match(clean)
        if m:
            p1 = m.group("p1")
            p2 = m.group("p2")
            p3 = m.group("p3")
            p4 = m.group("p4")
            # Mask p2 tail and p3 all
            p2_masked = f"{p2[:2]}{mask_char * (len(p2) - 2)}" if len(p2) > 2 else mask_char * len(p2)
            p3_masked = mask_char * len(p3)
            return f"{p1}-{p2_masked}-{p3_masked}-{p4}"

        digits = re.sub(r"\D", "", clean)
        if len(digits) == 16:
            return f"{digits[:6]}{mask_char * 6}{digits[-4:]}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_business_no(cls, text: str, mask_char: str = "*") -> str:
        """
        사업자등록번호: 앞 3자리(관할) 및 중간 2자리(유형) 노출, 끝 5자리(일련) 마스킹
        예: 123-45-67890 -> 123-45-*****
        """
        clean = text.strip()
        m = cls.PATTERNS["business_no"].match(clean)
        if m:
            p1 = m.group("p1")
            p2 = m.group("p2")
            p3 = m.group("p3")
            return f"{p1}-{p2}-{mask_char * len(p3)}"

        digits = re.sub(r"\D", "", clean)
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:5]}-{mask_char * 5}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_corporate_no(cls, text: str, mask_char: str = "*") -> str:
        """
        법인등록번호: 앞 6자리 노출, 뒷 7자리 마스킹
        예: 123456-1234567 -> 123456-*******
        """
        clean = text.strip()
        m = cls.PATTERNS["corporate_no"].match(clean)
        if m:
            p1 = m.group("p1")
            p2 = m.group("p2")
            return f"{p1}-{mask_char * len(p2)}"

        digits = re.sub(r"\D", "", clean)
        if len(digits) == 13:
            return f"{digits[:6]}-{mask_char * 7}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_car_plate(cls, text: str, mask_char: str = "*") -> str:
        """
        차량번호: 앞 번호+용도 한글 노출, 뒤 4자리 마스킹
        예: 12가 3456 -> 12가 ****, 123하 4567 -> 123하 ****
        """
        clean = text.strip()
        m = cls.PATTERNS["car_plate"].match(clean)
        if m:
            num = m.group("num")
            hangul = m.group("hangul")
            tail = m.group("tail")
            return f"{num}{hangul} {mask_char * len(tail)}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_driver_license(cls, text: str, mask_char: str = "*") -> str:
        """
        운전면허번호: 지역(2)+연도(2) 노출, 일련번호 및 검증번호 마스킹
        예: 11-20-123456-78 -> 11-20-******-**
        """
        clean = text.strip()
        m = cls.PATTERNS["driver_license"].match(clean)
        if m:
            region = m.group("region")
            yy = m.group("yy")
            serial = m.group("serial")
            chk = m.group("chk")
            return f"{region}-{yy}-{mask_char * len(serial)}-{mask_char * len(chk)}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_passport(cls, text: str, mask_char: str = "*") -> str:
        """
        여권번호: 앞 알파벳 1자리 노출, 뒷 8자리 마스킹
        예: M12345678 -> M********
        """
        clean = text.strip()
        m = cls.PATTERNS["passport"].match(clean)
        if m:
            letter = m.group("letter")
            digits = m.group("digits")
            return f"{letter.upper()}{mask_char * len(digits)}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_ip_address(cls, text: str, mask_char: str = "*") -> str:
        """
        IP 주소: 마지막 1~2개 옥텟 마스킹
        예: 192.168.1.100 -> 192.168.1.***
        """
        clean = text.strip()
        m = cls.PATTERNS["ip_address"].match(clean)
        if m:
            o1 = m.group("o1")
            o2 = m.group("o2")
            o3 = m.group("o3")
            return f"{o1}.{o2}.{o3}.{mask_char * 3}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_date(cls, text: str, mask_char: str = "*") -> str:
        """
        생년월일/날짜: 연도/월 노출, 일자 마스킹
        예: 1990-05-21 -> 1990-05-**
        """
        clean = text.strip()
        m = cls.PATTERNS["date_iso"].match(clean)
        if m:
            year = m.group("year")
            month = m.group("month")
            return f"{year}-{month.zfill(2)}-{mask_char * 2}"

        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_mac_address(cls, text: str, mask_char: str = "*") -> str:
        """MAC 주소: OUI 제조사 3바이트 보존, 디바이스 고유 3바이트 마스킹 (예: 00:1A:2B:3C:4D:5E -> 00:1A:2B:**:**:**)"""
        clean = text.strip()
        m = cls.PATTERNS["mac_address"].match(clean)
        if m:
            sep = ":" if ":" in clean else "-"
            b1, b2, b3 = m.group("b1"), m.group("b2"), m.group("b3")
            return f"{b1}{sep}{b2}{sep}{b3}{sep}{mask_char*2}{sep}{mask_char*2}{sep}{mask_char*2}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_uuid(cls, text: str, mask_char: str = "*") -> str:
        """UUID / GUID: 첫 번째 8자리 그룹 보존, 나머지 마스킹 (예: 123e4567-e89b-12d3-a456-426614174000 -> 123e4567-****-****-****-************)"""
        clean = text.strip()
        m = cls.PATTERNS["uuid"].match(clean)
        if m:
            g1 = m.group("g1")
            return f"{g1}-{mask_char*4}-{mask_char*4}-{mask_char*4}-{mask_char*12}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_tracking_no(cls, text: str, mask_char: str = "*") -> str:
        """택배 송장/운송장 번호: 앞 권역코드 및 끝 4자리 보존, 중간 마스킹 (예: 6521-1234-5678 -> 6521-****-5678)"""
        clean = text.strip()
        m = cls.PATTERNS["tracking_no"].match(clean)
        if m:
            p1, p2, p3 = m.group("p1"), m.group("p2"), m.group("p3")
            return f"{p1}-{mask_char * len(p2)}-{p3}"
        digits = re.sub(r"\D", "", clean)
        if len(digits) >= 10:
            return f"{digits[:4]}-{mask_char * 4}-{digits[-4:]}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_order_no(cls, text: str, mask_char: str = "*") -> str:
        """주문번호: 주문일자(8자리) 보존, 일련번호 마스킹 (예: 20260908-0001234 -> 20260908-*******)"""
        clean = text.strip()
        m = cls.PATTERNS["order_no"].match(clean)
        if m:
            date_str = m.group("date")
            serial = m.group("serial")
            return f"{date_str}-{mask_char * len(serial)}"
        if len(clean) >= 10:
            return f"{clean[:8]}-{mask_char * (len(clean) - 8)}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_health_insurance(cls, text: str, mask_char: str = "*") -> str:
        """건강보험증 번호: 자격구분(1) 및 앞 5자리 보존, 나머지 마스킹 (예: 1-123456789-0 -> 1-12345****-*)"""
        clean = text.strip()
        m = cls.PATTERNS["health_ins"].match(clean)
        if m:
            t = m.group("type")
            mid = m.group("mid")
            return f"{t}-{mid[:5]}{mask_char * (len(mid)-5)}-{mask_char}"
        digits = re.sub(r"\D", "", clean)
        if len(digits) >= 10:
            return f"{digits[:6]}{mask_char * (len(digits)-6)}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_military_no(cls, text: str, mask_char: str = "*") -> str:
        """군번: 입대연도(2) 보존, 일련번호 마스킹 (예: 23-71012345 -> 23-71******)"""
        clean = text.strip()
        m = cls.PATTERNS["military_no"].match(clean)
        if m:
            yy = m.group("yy")
            serial = m.group("serial")
            return f"{yy}-{serial[:2]}{mask_char * (len(serial)-2)}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_pnu(cls, text: str, mask_char: str = "*") -> str:
        """토지/필지 고유번호(PNU 19자리): 행정구역 10자리(시군구/읍면동/리) 보존, 필지번 8자리 마스킹 (예: 1168010100101230001 -> 1168010100********)"""
        clean = re.sub(r"\D", "", str(text).strip())
        if len(clean) == 19:
            return f"{clean[:10]}{clean[10]}{mask_char * 8}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_patient_id(cls, text: str, mask_char: str = "*") -> str:
        """환자등록번호 / 병원차트번호: 기관접두사/연도 보존, 일련번호 마스킹 (예: PT-2024-001234 -> PT-2024-******)"""
        clean = text.strip()
        parts = clean.split("-")
        if len(parts) >= 2:
            return f"{'-'.join(parts[:-1])}-{mask_char * len(parts[-1])}"
        if len(clean) >= 6:
            return f"{clean[:3]}{mask_char * (len(clean)-3)}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_student_id(cls, text: str, mask_char: str = "*") -> str:
        """학번: 입학년도/학과코드(4~6자리) 보존, 개인일련번호 마스킹 (예: 2023123456 -> 202312****)"""
        clean = text.strip()
        digits = re.sub(r"\D", "", clean)
        if len(digits) >= 8:
            return f"{digits[:6]}{mask_char * (len(digits)-6)}"
        elif len(digits) >= 6:
            return f"{digits[:4]}{mask_char * (len(digits)-4)}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_employee_id(cls, text: str, mask_char: str = "*") -> str:
        """사번: 접두사/입사연도 보존, 개인일련번호 마스킹 (예: EMP-2023-0145 -> EMP-2023-****, E2024001 -> E2024***)"""
        clean = text.strip()
        parts = clean.split("-")
        if len(parts) >= 2:
            return f"{'-'.join(parts[:-1])}-{mask_char * len(parts[-1])}"
        if len(clean) >= 6:
            return f"{clean[:4]}{mask_char * (len(clean)-4)}"
        return cls.mask_generic(clean, mask_char=mask_char)

    @classmethod
    def mask_generic(cls, text: str, mask_char: str = "*") -> str:
        """
        일반 문자열/ID: 길이에 비례하여 앞/뒤 일정 부분 유지 후 중간 마스킹
        """
        clean = str(text).strip()
        length = len(clean)
        if length <= 1:
            return mask_char
        elif length == 2:
            return f"{clean[0]}{mask_char}"
        elif length == 3:
            return f"{clean[0]}{mask_char}{clean[2]}"
        elif length == 4:
            return f"{clean[0]}{mask_char * 2}{clean[3]}"
        elif length <= 8:
            return f"{clean[:2]}{mask_char * (length - 3)}{clean[-1]}"
        else:
            return f"{clean[:3]}{mask_char * (length - 6)}{clean[-3:]}"

    @classmethod
    def mask_full_text(cls, text: str, mask_char: str = "*") -> str:
        """
        Scan and smart-mask all inline PII patterns within narrative paragraphs, sentences, or mixed document cells.
        """
        if not isinstance(text, str) or not text.strip():
            return text

        res = text

        # 1. RRN / Resident Registration Number: 900101-1234567 -> 900101-1******
        def _mask_rrn(m):
            front = m.group(1)
            sep = m.group(2) or "-"
            gender = m.group(3)
            return f"{front}{sep}{gender}{mask_char * 6}"
        res = re.sub(r"\b(\d{6})([-\s]?)([1-8])\d{6}\b", _mask_rrn, res)
        res = re.sub(r"\b(\d{6})([-\s]?)([1-8])[*\s]{1,6}\b", _mask_rrn, res)
        res = re.sub(r"\[RRN Omitted[^\]]*\]", f"[주민등록번호-{mask_char * 4}]", res)

        # 2. Phone / Mobile: 010-1234-5678 -> 010-****-5678, 02-412-8823 -> 02-****-8823
        def _mask_phone(m):
            prefix = m.group(1)
            sep1 = m.group(2) or "-"
            sep2 = m.group(4) or "-"
            last = m.group(5)
            return f"{prefix}{sep1}{mask_char * 4}{sep2}{last}"
        res = re.sub(r"\b(01[016789]|02|0[3-6][1-5])([-\s]?)(\d{3,4})([-\s]?)(\d{4})\b", _mask_phone, res)

        # 3. Email: jinwoo.park84@mockmail.kr -> jin*****@mockmail.kr
        def _mask_email(m):
            user = m.group(1)
            domain = m.group(2)
            if len(user) <= 3:
                masked_user = user[0] + mask_char * (len(user) - 1)
            else:
                masked_user = user[:3] + mask_char * 5
            return f"{masked_user}@{domain}"
        res = re.sub(r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", _mask_email, res)

        # 4. Driver License: 11-19-284719-01 -> 11-19-******-01
        def _mask_dl(m):
            r = m.group(1)
            yy = m.group(2)
            chk = m.group(3)
            return f"{r}-{yy}-{mask_char * 6}-{chk}"
        res = re.sub(r"\b(\d{2})[-\s]?(\d{2})[-\s]?\d{6}[-\s]?(\d{2})\b", _mask_dl, res)

        # 5. Passport: M38491827 -> M38****27
        def _mask_passport(m):
            letter = m.group(1)
            num = m.group(2)
            return f"{letter}{num[:2]}{mask_char * 4}{num[-2:]}"
        res = re.sub(r"\b([A-Z])(\d{7,8})\b", _mask_passport, res)

        # 6. Credit Card: 4328-****-****-1928, 1234-5678-9012-3456 -> 4328-56**-****-1928
        def _mask_card(m):
            p1 = m.group(1)
            p2 = m.group(2)
            p4 = m.group(3)
            p2_masked = f"{p2[:2]}{mask_char * 2}" if not "*" in p2 else p2
            return f"{p1}-{p2_masked}-{mask_char * 4}-{p4}"
        res = re.sub(r"\b(\d{4})[-\s]?(\d{4}|\*{4})[-\s]?(?:\d{4}|\*{4})[-\s]?(\d{4})\b", _mask_card, res)

        # 7. Bank Account: 110-382-948123 -> 110-***-***123, 482901-01-382910, 293-910283-48207
        def _mask_bank(m):
            full = m.group(0)
            parts = full.split("-")
            if len(parts) >= 3:
                return f"{parts[0]}-{mask_char * len(parts[1])}-{parts[-1][:2]}{mask_char * (len(parts[-1]) - 2)}"
            return full
        res = re.sub(r"\b\d{3,6}-\d{2,6}-\d{3,6}(?:-\d{1,4})?\b", _mask_bank, res)

        # 8. Health Insurance (11 digits without 010)
        def _mask_health_ins(m):
            s = m.group(0)
            if len(s) == 11 and not s.startswith("010"):
                return f"{s[:4]}{mask_char * 4}{s[-3:]}"
            return s
        res = re.sub(r"\b\d{11}\b", _mask_health_ins, res)

        # 9. Names with prefixes: 예) 환자명: 홍길동, 주문자 이지은, 예금주: 박진우, 거주 홍길동
        def _mask_named_person(m):
            prefix = m.group(1)
            name = m.group(2)
            if len(name) == 2:
                masked = name[0] + mask_char
            elif len(name) == 3:
                masked = name[0] + mask_char + name[2]
            else:
                masked = name[0] + mask_char * (len(name) - 2) + name[-1]
            return f"{prefix}{masked}"
        res = re.sub(r"(환자명\s*:\s*|환자\s*:\s*|성명\s*:\s*|성명\s*\(한글/영문\)\s*:\s*|예금주\s*:\s*|예금주\s*|주문자\s*|담당자\s*:\s*|수신자\s*:\s*|보호자\s*:\s*)([가-힣]{2,4})", _mask_named_person, res)

        # 10. Korean Addresses: 서울시 송파구 올림픽로 300 102동 405호 -> 서울시 송파구 ********** 102동 405호
        def _mask_address(m):
            sido = m.group(1)
            gu_gun = m.group(2)
            rest = m.group(3)
            return f"{sido} {gu_gun} {mask_char * 8}"
        res = re.sub(r"\b(서울시|서울특별시|부산시|부산광역시|대구시|대구광역시|인천시|인천광역시|광주시|광주광역시|대전시|대전광역시|울산시|울산광역시|세종시|세종특별자치시|경기도|강원도|충청북도|충북도|충청남도|충남도|전라북도|전북도|전라남도|전남도|경상북도|경북도|경상남도|경남도|제주도|제주특별자치도)\s+([가-힣]+[시군구])\s+([가-힣0-9\s-]+(?:로|길|동|읍|면|리)\s*[0-9-]+(?:\s*[0-9]+[동호층])?)", _mask_address, res)

        return res

    @classmethod
    def mask_value(cls, value: Any, pii_type: Optional[str] = None, mask_char: str = "*") -> Any:
        """
        Route any single value to the appropriate smart masking handler based on PII type or value pattern.
        """
        if pd.isna(value) or value is None:
            return value

        text = str(value).strip()
        if not text:
            return text

        # 1. If explicit PII type given
        pt = (pii_type or "").lower().strip()
        if pt in ("unstructured_text", "text", "document_text", "all", "paragraph"):
            return cls.mask_full_text(text, mask_char)
        if pt in ("ssn", "resident", "rrn"):
            return cls.mask_ssn(text, mask_char)
        if pt in ("phone_number", "phone", "mobile", "tel", "hp"):
            return cls.mask_phone(text, mask_char)
        if pt in ("name", "korean_name", "user_name"):
            return cls.mask_name(text, mask_char)
        if pt in ("email", "mail"):
            return cls.mask_email(text, mask_char)
        if pt in ("address", "addr", "road_address"):
            return cls.mask_address(text, mask_char)
        if pt in ("account", "bank_account"):
            return cls.mask_account(text, mask_char)
        if pt in ("credit_card", "card"):
            return cls.mask_credit_card(text, mask_char)
        if pt in ("business_number", "biz_no"):
            return cls.mask_business_no(text, mask_char)
        if pt in ("corporate_number", "corp_no"):
            return cls.mask_corporate_no(text, mask_char)
        if pt in ("driver_license", "license"):
            return cls.mask_driver_license(text, mask_char)
        if pt in ("foreigner_id", "arc"):
            return cls.mask_ssn(text, mask_char)
        if pt in ("passport", "passport_no"):
            return cls.mask_passport(text, mask_char)
        if pt in ("car_plate", "plate"):
            return cls.mask_car_plate(text, mask_char)
        if pt in ("ip_address", "ip"):
            return cls.mask_ip_address(text, mask_char)
        if pt in ("mac_address", "mac"):
            return cls.mask_mac_address(text, mask_char)
        if pt in ("uuid", "guid"):
            return cls.mask_uuid(text, mask_char)
        if pt in ("tracking_no", "waybill", "invoice"):
            return cls.mask_tracking_no(text, mask_char)
        if pt in ("order_no", "order"):
            return cls.mask_order_no(text, mask_char)
        if pt in ("health_insurance", "health_ins"):
            return cls.mask_health_insurance(text, mask_char)
        if pt in ("patient_id", "chart_no", "mrn"):
            return cls.mask_patient_id(text, mask_char)
        if pt in ("employee_id", "emp_no", "사번", "직원번호"):
            return cls.mask_employee_id(text, mask_char)
        if pt in ("student_id", "학번", "학생번호"):
            return cls.mask_student_id(text, mask_char)
        if pt in ("military_no", "군번"):
            return cls.mask_military_no(text, mask_char)
        if pt in ("pnu", "필지"):
            return cls.mask_pnu(text, mask_char)
        if pt in ("birth_date", "date", "birth"):
            return cls.mask_date(text, mask_char)

        # 2. Auto-detect from value pattern if pii_type is unknown or generic
        if cls.PATTERNS["ssn"].match(text):
            return cls.mask_ssn(text, mask_char)
        if cls.PATTERNS["phone_mobile"].match(text) or cls.PATTERNS["phone_tel"].match(text):
            return cls.mask_phone(text, mask_char)
        if cls.PATTERNS["email"].match(text):
            return cls.mask_email(text, mask_char)
        if cls.PATTERNS["credit_card"].match(text):
            return cls.mask_credit_card(text, mask_char)
        if cls.PATTERNS["business_no"].match(text):
            return cls.mask_business_no(text, mask_char)
        if cls.PATTERNS["corporate_no"].match(text):
            return cls.mask_corporate_no(text, mask_char)
        if cls.PATTERNS["driver_license"].match(text):
            return cls.mask_driver_license(text, mask_char)
        if cls.PATTERNS["passport"].match(text):
            return cls.mask_passport(text, mask_char)
        if cls.PATTERNS["car_plate"].match(text):
            return cls.mask_car_plate(text, mask_char)
        if cls.PATTERNS["ip_address"].match(text):
            return cls.mask_ip_address(text, mask_char)
        if cls.PATTERNS["mac_address"].match(text):
            return cls.mask_mac_address(text, mask_char)
        if cls.PATTERNS["uuid"].match(text):
            return cls.mask_uuid(text, mask_char)
        if cls.PATTERNS["tracking_no"].match(text):
            return cls.mask_tracking_no(text, mask_char)
        if cls.PATTERNS["order_no"].match(text):
            return cls.mask_order_no(text, mask_char)
        if cls.PATTERNS["health_ins"].match(text):
            return cls.mask_health_insurance(text, mask_char)
        if cls.PATTERNS["military_no"].match(text):
            return cls.mask_military_no(text, mask_char)
        if cls.PATTERNS["pnu"].match(text):
            return cls.mask_pnu(text, mask_char)

        # 3. Check for inline PII within narrative sentences / multi-word strings
        full_masked = cls.mask_full_text(text, mask_char)
        if full_masked != text:
            return full_masked

        # Default smart generic masking if explicitly requested or very long
        return cls.mask_generic(text, mask_char)

    @classmethod
    def mask_series(cls, series: pd.Series, pii_type: Optional[str] = None, mask_char: str = "*") -> pd.Series:
        """Apply smart masking across an entire pandas Series."""
        return series.map(lambda v: cls.mask_value(v, pii_type=pii_type, mask_char=mask_char))
