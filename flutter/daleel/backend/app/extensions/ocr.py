"""Local Arabic and English image OCR using PaddleOCR's multilingual Arabic model."""
from __future__ import annotations

import io
import logging
import unicodedata
from functools import lru_cache

from fastapi import HTTPException

from ..integrations.contracts import ModuleNotConfigured, OcrRequest

log = logging.getLogger(__name__)
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _reverse_arabic_words(text: str) -> str:
    output = []
    run = []

    def flush_run() -> None:
        if run:
            has_arabic_letter = any(
                character.isalpha()
                and unicodedata.name(character, "").startswith("ARABIC ")
                for character in run
            )
            if not has_arabic_letter:
                output.extend(run)
                run.clear()
                return

            clusters = []
            for character in run:
                if unicodedata.combining(character) and clusters:
                    clusters[-1] += character
                elif character.isdecimal() and clusters and clusters[-1].isdecimal():
                    clusters[-1] += character
                else:
                    clusters.append(character)
            output.extend(reversed(clusters))
            run.clear()

    for character in text:
        is_arabic_letter = (
            character.isalpha()
            and unicodedata.name(character, "").startswith("ARABIC ")
        )
        if is_arabic_letter or character.isdecimal() or (
            run and unicodedata.combining(character)
        ):
            run.append(character)
        else:
            flush_run()
            output.append(character)
    flush_run()
    return "".join(output)


@lru_cache(maxsize=1)
def _ocr_engine():
    try:
        from paddleocr import PaddleOCR
    except ImportError as error:
        log.exception("PaddleOCR is not installed")
        raise ModuleNotConfigured(
            "Install the PaddleOCR and PaddlePaddle dependencies, then restart the backend."
        ) from error

    try:
        return PaddleOCR(use_angle_cls=True, lang="ar", show_log=False)
    except Exception as error:
        log.exception("Could not initialize the Arabic and English PaddleOCR model")
        raise ModuleNotConfigured(
            "The Arabic and English PaddleOCR model could not be initialized. "
            "Check the backend logs and model download access."
        ) from error


def extract_image_text(request: OcrRequest) -> dict:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as error:
        log.exception("Pillow is not installed")
        raise ModuleNotConfigured(
            "Install the PaddleOCR and PaddlePaddle dependencies, then restart the backend."
        ) from error

    try:
        with Image.open(io.BytesIO(request.image_bytes)) as image:
            image_format = image.format
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail="The image dimensions exceed the 25 megapixel limit.",
                )
            image.verify()
        if IMAGE_FORMATS.get(image_format) != request.content_type:
            raise HTTPException(status_code=415, detail="The image content does not match its file type.")
        with Image.open(io.BytesIO(request.image_bytes)) as image:
            image_array = image.convert("RGB")
    except HTTPException:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
    ) as error:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from error

    try:
        import numpy as np

        result = _ocr_engine().ocr(np.asarray(image_array), cls=True)
    except ModuleNotConfigured:
        raise
    except Exception as error:
        log.exception("PaddleOCR image extraction failed")
        raise HTTPException(
            status_code=502,
            detail="The OCR model could not process this image. Please try another image.",
        ) from error

    recognized_lines = []
    confidences = []
    for page in result or []:
        for line in page or []:
            if not line or len(line) < 2 or not line[1]:
                continue
            text, confidence = line[1]
            if isinstance(text, str) and text.strip():
                recognized_lines.append(_reverse_arabic_words(text.strip()))
                if isinstance(confidence, (int, float)):
                    confidences.append(float(confidence))

    return {
        "status": "integrated",
        "text": "\n".join(recognized_lines),
        "fields": {},
        "confidence": sum(confidences) / len(confidences) if confidences else None,
    }
