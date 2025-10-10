"""Utilities for identifying and validating GS1 retail barcodes."""

from __future__ import annotations

import re
from typing import Iterable, Optional


_GROUP_SEPARATOR = "\x1d"


def _calculate_gs1_mod10_check_digit(digits: str) -> int:
    """Return the GS1 modulo 10 check digit for the provided numeric body."""

    total = 0
    for index, char in enumerate(reversed(digits)):
        factor = 3 if index % 2 == 0 else 1
        total += int(char) * factor
    return (10 - (total % 10)) % 10


def _is_valid_numeric(code: str, length: int) -> bool:
    return len(code) == length and code.isdigit()


def _normalize_group_separators(value: str) -> str:
    """Replace common human encodings of the GS1 FNC1 separator by ``\x1d``."""

    normalized = value
    for token in ("[GS]", "<GS>", "{GS}", "|GS|"):
        normalized = normalized.replace(token, _GROUP_SEPARATOR)
    normalized = normalized.replace("\\x1d", _GROUP_SEPARATOR)
    normalized = normalized.replace("\\u001d", _GROUP_SEPARATOR)
    normalized = normalized.replace("\u001d", _GROUP_SEPARATOR)
    normalized = normalized.replace("\u241d", _GROUP_SEPARATOR)  # visual symbol ␝
    normalized = normalized.replace(chr(29), _GROUP_SEPARATOR)
    normalized = re.sub(r"(?<=\d)T(?=\d)", _GROUP_SEPARATOR, normalized)
    return normalized


def _iter_digit_groups(value: str) -> Iterable[str]:
    """Yield groups of consecutive digits within ``value``."""

    for match in re.finditer(r"\d+", value):
        yield match.group(0)


def _longest_digit_group(value: str) -> str:
    return max(_iter_digit_groups(value), default="", key=len)


def _looks_like_gs1_ai_stream(normalized: str, digits: str) -> bool:
    """Return ``True`` when ``value`` looks like a GS1 AI encoded data string."""

    if "(" in normalized and ")" in normalized:
        return True
    if _GROUP_SEPARATOR in normalized:
        return True

    if len(digits) < 16 or not digits.startswith(("01", "02", "00")):
        return False

    if digits.startswith("00") and len(digits) == 18:
        # SSCC encodes AI 00 but does not include additional elements.
        return False

    ai_markers = (
        "10",
        "11",
        "13",
        "15",
        "17",
        "20",
        "21",
        "23",
        "24",
        "25",
        "30",
        "37",
        "310",
        "311",
        "312",
        "313",
        "314",
        "315",
        "316",
        "320",
        "330",
        "392",
        "393",
    )
    if len(digits) > 16:
        for marker in ai_markers:
            if marker in digits[2:]:
                return True
        return True
    return False


def is_valid_ean13(code: str) -> bool:
    if not _is_valid_numeric(code, 13):
        return False
    return _calculate_gs1_mod10_check_digit(code[:-1]) == int(code[-1])


def is_valid_gtin14(code: str) -> bool:
    if not _is_valid_numeric(code, 14):
        return False
    return _calculate_gs1_mod10_check_digit(code[:-1]) == int(code[-1])


def is_valid_upca(code: str) -> bool:
    if not _is_valid_numeric(code, 12):
        return False
    return _calculate_gs1_mod10_check_digit(code[:-1]) == int(code[-1])


def is_valid_ean8(code: str) -> bool:
    if not _is_valid_numeric(code, 8):
        return False
    return _calculate_gs1_mod10_check_digit(code[:-1]) == int(code[-1])


def _expand_upce_to_upca(code: str) -> Optional[str]:
    """Expand a UPC-E code (8 digits) to its UPC-A (12 digits) equivalent."""

    if not _is_valid_numeric(code, 8):
        return None

    number_system = code[0]
    check_digit = code[-1]
    if number_system not in {"0", "1"}:
        return None

    body = code[1:-1]
    manufacturer = body[:5]
    last = body[-1]

    if last in {"0", "1", "2"}:
        upca_body = (
            number_system
            + manufacturer[:2]
            + last
            + "0000"
            + manufacturer[2:5]
        )
    elif last == "3":
        upca_body = number_system + manufacturer[:3] + "00000" + manufacturer[3:5]
    elif last == "4":
        upca_body = number_system + manufacturer[:4] + "00000" + manufacturer[4]
    else:
        upca_body = number_system + manufacturer + last + "0000"

    if len(upca_body) != 11:
        return None

    if _calculate_gs1_mod10_check_digit(upca_body) != int(check_digit):
        return None

    return upca_body + check_digit


def is_valid_upce(code: str) -> bool:
    return _expand_upce_to_upca(code) is not None


def is_valid_sscc(code: str) -> bool:
    """Return ``True`` when ``code`` is a valid Serial Shipping Container Code."""

    if not _is_valid_numeric(code, 18):
        return False
    return _calculate_gs1_mod10_check_digit(code[:-1]) == int(code[-1])


def classify_gs1_barcode(code: Optional[str]) -> str:
    """Return the most likely GS1 barcode type for the provided value."""

    if not code:
        return "Code128"

    value = code.strip()
    if not value:
        return "Code128"

    normalized = _normalize_group_separators(value)
    digit_group = _longest_digit_group(normalized)
    digits_only = digit_group if digit_group else ""

    if normalized.startswith("]C1"):
        return "GS1-128"

    joined_digits = "".join(ch for ch in normalized if ch.isdigit())
    if _looks_like_gs1_ai_stream(normalized, joined_digits):
        return "GS1DataBar"

    if digits_only:
        length = len(digits_only)
        if length == 18 and digits_only.startswith("00"):
            if is_valid_sscc(digits_only):
                return "SSCC"
            return "Code128"
        if length == 14:
            return "GTIN14"
        if length == 13:
            return "EAN13"
        if length == 12:
            return "UPCA"
        if length == 11:
            padded = "0" + digits_only
            if is_valid_upca(padded):
                return "UPCA"
        if length == 8:
            if is_valid_upce(digits_only):
                return "UPCE"
            return "EAN8"

    return "Code128"


__all__ = [
    "classify_gs1_barcode",
    "is_valid_ean8",
    "is_valid_ean13",
    "is_valid_gtin14",
    "is_valid_upca",
    "is_valid_upce",
    "is_valid_sscc",
]
