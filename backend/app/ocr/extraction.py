import re
from dataclasses import dataclass

from app.ocr.base import OcrBox


@dataclass(frozen=True)
class ExtractedValue:
    field: str
    value: str
    confidence: float
    bbox: dict[str, float]


def classify_document(boxes: list[OcrBox], requested_type: str) -> str:
    text = " ".join(box.text.lower() for box in boxes)
    hints = {
        "st_certificate": ("caste", "scheduled tribe", "अनुसूचित जनजाति", "tribe"),
        "income_certificate": ("income", "वार्षिक आय", "annual income"),
        "marksheet": ("marks", "प्राप्तांक", "percentage", "marksheet"),
        "bank_passbook": ("passbook", "account number", "ifsc", "बैंक"),
        "admission_letter": ("admission", "प्रवेश", "enrollment", "institute"),
        "aadhaar": ("aadhaar", "आधार", "unique identification"),
    }
    scores = {
        name: sum(word in text for word in words) for name, words in hints.items()
    }
    best = max(scores, key=lambda name: scores[name])
    return best if scores[best] else requested_type


def extract_fields(boxes: list[OcrBox], doc_type: str) -> list[ExtractedValue]:
    text = "\n".join(box.text for box in boxes)
    average = sum(box.confidence for box in boxes) / len(boxes) if boxes else 0.0
    fields: list[ExtractedValue] = []

    def add(field: str, match: re.Match[str], confidence: float = average) -> None:
        box = boxes[0].bbox if boxes else (0.0, 0.0, 0.0, 0.0)
        fields.append(
            ExtractedValue(
                field,
                match.group(1).strip(),
                min(confidence, 1.0),
                {"x1": box[0], "y1": box[1], "x2": box[2], "y2": box[3]},
            )
        )

    patterns = {
        "st_certificate": {
            "certificate_number": r"(?:certificate\s*(?:no|number)|प्रमाण पत्र)\s*[:#-]?\s*([A-Za-z0-9/-]+)",
            "tribe_name": r"(?:tribe|जाति)\s*(?:name)?\s*[:\-]\s*([^\n]+)",
        },
        "income_certificate": {
            "annual_income": r"(?:annual\s+income|वार्षिक आय)\s*[:\-₹\s]*([0-9,]+)",
        },
        "marksheet": {
            "percentage": r"(?:percentage|प्रतिशत)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%?",
            "roll_number": r"(?:roll\s*(?:no|number)|अनुक्रमांक)\s*[:#-]?\s*([A-Za-z0-9/-]+)",
        },
        "bank_passbook": {
            "account_number": r"(?:account\s*(?:no|number))\s*[:#-]?\s*([0-9]{6,})",
            "ifsc": r"\b([A-Z]{4}0[A-Z0-9]{6})\b",
        },
        "admission_letter": {
            "institution": r"(?:institution|college|विश्वविद्यालय)\s*[:\-]\s*([^\n]+)",
            "course": r"(?:course|program|पाठ्यक्रम)\s*[:\-]\s*([^\n]+)",
        },
        "aadhaar": {
            "aadhaar_last4": r"(?:aadhaar|आधार)[^\n]*?([0-9]{4})\s*$",
        },
    }
    for field, pattern in patterns.get(doc_type, {}).items():
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1)
            if field == "aadhaar_last4":
                value = value[-4:]
            add(field, re.match(r"(.*)", value) or match)
    return fields
