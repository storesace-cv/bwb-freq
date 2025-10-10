from app.utils.barcodes import (
    classify_gs1_barcode,
    is_valid_ean13,
    is_valid_ean8,
    is_valid_gtin14,
    is_valid_sscc,
    is_valid_upca,
    is_valid_upce,
)


def test_classify_common_numeric_codes():
    ean13 = "5601234567892"
    upca = "036000291452"
    upce = "04252614"
    ean8 = "55123457"
    gtin14 = "01234567890128"

    assert is_valid_ean13(ean13)
    assert is_valid_upca(upca)
    assert is_valid_upce(upce)
    assert is_valid_ean8(ean8)
    assert is_valid_gtin14(gtin14)

    assert classify_gs1_barcode(ean13) == "EAN13"
    assert classify_gs1_barcode(upca) == "UPCA"
    assert classify_gs1_barcode(upce) == "UPCE"
    assert classify_gs1_barcode(ean8) == "EAN8"
    assert classify_gs1_barcode(gtin14) == "GTIN14"


def test_classify_handles_truncated_or_embedded_digits():
    upca_without_leading_zero = "19962943430"
    ean_with_prefix_text = "ALTANO 5601007001325"

    assert classify_gs1_barcode(upca_without_leading_zero) == "UPCA"
    assert classify_gs1_barcode(ean_with_prefix_text) == "EAN13"


def test_classify_gs1_extended_formats():
    gs1_databar = "(01)09501101530008(15)991231"
    gs1_databar_digits = "010560912927020915250902102449023"
    gs1_128 = "]C1012345678901234"
    other = "https://example.com/L003"

    assert classify_gs1_barcode(gs1_databar) == "GS1DataBar"
    assert classify_gs1_barcode(gs1_databar_digits) == "GS1DataBar"
    assert classify_gs1_barcode(gs1_128) == "GS1-128"
    assert classify_gs1_barcode(other) == "Code128"
    assert classify_gs1_barcode("") == "Code128"


def test_validate_sscc():
    sscc = "003123456789012344"
    assert is_valid_sscc(sscc)
    assert classify_gs1_barcode(sscc) == "SSCC"
