from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageStat


@dataclass(frozen=True)
class QualityFeedback:
    passed: bool
    messages: list[str]
    width: int | None = None
    height: int | None = None
    blur_score: float | None = None
    skew_score: float | None = None


def check_image_quality(content: bytes, mime: str) -> QualityFeedback:
    if mime == "application/pdf":
        return QualityFeedback(True, [])
    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            messages: list[str] = []
            if width < 1000 or height < 700:
                messages.append("Image resolution is too low; upload a clearer scan.")
            grayscale = image.convert("L").resize((min(width, 256), min(height, 256)))
            blur_score = float(ImageStat.Stat(grayscale).var[0])
            if blur_score < 80:
                messages.append("Image appears blurry; retake the document in focus.")
            return QualityFeedback(
                not messages, messages, width, height, blur_score, 0.0
            )
    except (OSError, ValueError):
        return QualityFeedback(False, ["Image could not be decoded safely."])
