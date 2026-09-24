from app.ocr.base import MockOcr, OcrBox, build_ocr_engine
from app.ocr.extraction import classify_document, extract_fields


def test_mock_ocr_extracts_multilingual_lines() -> None:
    boxes = MockOcr().extract_text_with_boxes(
        "जाति प्रमाण पत्र\nTribe: Gond\nCertificate No: ST/42".encode(),
        ["en", "hi"],
    )
    assert [box.text for box in boxes] == [
        "जाति प्रमाण पत्र",
        "Tribe: Gond",
        "Certificate No: ST/42",
    ]


def test_st_certificate_fields_include_confidence_and_bbox() -> None:
    boxes = [
        OcrBox("Scheduled Tribe Certificate", 0.95, (1, 2, 3, 4)),
        OcrBox("Tribe: Gond", 0.9, (5, 6, 7, 8)),
        OcrBox("Certificate No: ST/42", 0.9, (9, 10, 11, 12)),
    ]
    doc_type = classify_document(boxes, "st_certificate")
    fields = extract_fields(boxes, doc_type)
    values = {field.field: field for field in fields}
    assert values["tribe_name"].value == "Gond"
    assert values["certificate_number"].value == "ST/42"
    assert 0 < values["tribe_name"].confidence <= 1
    assert values["tribe_name"].bbox == {"x1": 1, "y1": 2, "x2": 3, "y2": 4}


def test_aadhaar_is_reduced_to_last_four_digits() -> None:
    fields = extract_fields(
        [OcrBox("Aadhaar: 1234 5678 9012", 0.9, (0, 0, 1, 1))], "aadhaar"
    )
    assert fields[0].field == "aadhaar_last4"
    assert fields[0].value == "9012"


def test_engine_factory_supports_offline_mock() -> None:
    assert isinstance(build_ocr_engine("mock"), MockOcr)
