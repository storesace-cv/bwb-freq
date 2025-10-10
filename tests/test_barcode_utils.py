from app.utils.barcodes import (
    classify_gs1_barcode,
    is_valid_ean13,
    is_valid_ean8,
    is_valid_gtin14,
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


def test_classify_gs1_extended_formats():
    gs1_databar = "(01)09501101530008(15)991231"
    gs1_128 = "]C1012345678901234"
    other = "ABC1234"

    assert classify_gs1_barcode(gs1_databar) == "GS1DataBar"
    assert classify_gs1_barcode(gs1_128) == "GS1-128"
    assert classify_gs1_barcode(other) == "Code128"
    assert classify_gs1_barcode("") == "Code128"
