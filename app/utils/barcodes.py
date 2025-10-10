"""Utilities for identifying and validating GS1 retail barcodes."""

from __future__ import annotations

from typing import Optional


def _calculate_gs1_mod10_check_digit(digits: str) -> int:
    """Return the GS1 modulo 10 check digit for the provided numeric body."""

    total = 0
    for index, char in enumerate(reversed(digits)):
        factor = 3 if index % 2 == 0 else 1
        total += int(char) * factor
    return (10 - (total % 10)) % 10


def _is_valid_numeric(code: str, length: int) -> bool:
    return len(code) == length and code.isdigit()


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


def classify_gs1_barcode(code: Optional[str]) -> str:
    """Return the most likely GS1 barcode type for the provided value."""

    if not code:
        return "Code128"

    value = code.strip()
    if not value:
        return "Code128"

    if value.startswith("]C1"):
        return "GS1-128"

    if "\x1d" in value or ("(" in value and ")" in value):
        return "GS1DataBar"

    if value.isdigit():
        length = len(value)
        if length == 14:
            return "GTIN14"
        if length == 13:
            return "EAN13"
        if length == 12:
            return "UPCA"
        if length == 8:
            if is_valid_upce(value):
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
]

