from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OcrBox:
    text: str
    confidence: float
    bbox: tuple[float, float, float, float]


class OcrEngine(Protocol):
    def extract_text_with_boxes(
        self, content: bytes, languages: list[str]
    ) -> list[OcrBox]:
        """Extract text, confidence, and coordinates from a document."""


class MockOcr:
    """Deterministic OCR adapter used offline and by unit tests."""

    def __init__(self, boxes: list[OcrBox] | None = None) -> None:
        self.boxes = boxes

    def extract_text_with_boxes(
        self, content: bytes, languages: list[str]
    ) -> list[OcrBox]:
        if self.boxes is not None:
            return self.boxes
        text = content.decode("utf-8", errors="ignore").strip()
        return [
            OcrBox(line, 0.99, (0.0, float(index), 1.0, float(index + 1)))
            for index, line in enumerate(text.splitlines())
            if line.strip()
        ]


class PaddleOcrEngine:
    def extract_text_with_boxes(
        self, content: bytes, languages: list[str]
    ) -> list[OcrBox]:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("PaddleOCR is not installed") from error
        from io import BytesIO

        import numpy as np  # type: ignore[import-not-found]
        from PIL import Image

        image = np.asarray(Image.open(BytesIO(content)).convert("RGB"))
        ocr = PaddleOCR(
            lang=languages[0] if languages else "en", use_doc_orientation_classify=False
        )
        result = ocr.predict(image)
        boxes: list[OcrBox] = []
        for page in result:
            texts = page.get("rec_texts", [])
            scores = page.get("rec_scores", [])
            polygons = page.get("dt_polys", [])
            for text, score, polygon in zip(texts, scores, polygons):
                points = [point for point in polygon]
                xs = [float(point[0]) for point in points]
                ys = [float(point[1]) for point in points]
                boxes.append(
                    OcrBox(
                        str(text), float(score), (min(xs), min(ys), max(xs), max(ys))
                    )
                )
        return boxes


class DocTrOcrEngine:
    def extract_text_with_boxes(
        self, content: bytes, languages: list[str]
    ) -> list[OcrBox]:
        try:
            from doctr.io import DocumentFile  # type: ignore[import-not-found]
            from doctr.models import ocr_predictor  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("DocTR is not installed") from error
        document = DocumentFile.from_pdf(content)
        result = ocr_predictor(pretrained=True)(document)
        boxes: list[OcrBox] = []
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        x1, y1, x2, y2 = word.geometry[0] + word.geometry[1]
                        boxes.append(
                            OcrBox(
                                word.value,
                                float(word.confidence),
                                (float(x1), float(y1), float(x2), float(y2)),
                            )
                        )
        return boxes


def build_ocr_engine(name: str) -> OcrEngine:
    normalized = name.lower()
    if normalized == "paddleocr":
        return PaddleOcrEngine()
    if normalized == "doctr":
        return DocTrOcrEngine()
    if normalized == "mock":
        return MockOcr()
    raise ValueError(f"Unsupported OCR engine: {name}")
