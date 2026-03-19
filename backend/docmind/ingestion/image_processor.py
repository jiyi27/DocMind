"""Image processing strategies for ingestion pipeline.

Supports two backends, selected via IMAGE_PROCESSOR env var:
  - "multimodal": fetch image → base64 → vision-capable LLM → text summary
  - "ocr":        fetch image → pytesseract → extracted text
  - "none":       skip all image processing (default when unset)

Only HTTP/HTTPS image URLs are processed. Local paths are rejected.
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from docmind.core import logger


class ImageFetchError(Exception):
    """Raised when the image URL cannot be fetched (dead link, timeout, HTTP error, etc.)."""


class ImageProcessor(ABC):
    @abstractmethod
    def process(self, image_url: str) -> str:
        """Fetch the image at *image_url* and return a text description/extraction."""


class MultimodalProcessor(ImageProcessor):
    """Generates a natural-language description of an image via a vision LLM."""

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        # Import lazily to avoid hard dependency when multimodal is not used.
        from openai import OpenAI  # langchain-openai bundles openai

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def process(self, image_url: str) -> str:
        image_data = _fetch_image_bytes(image_url)
        b64 = base64.standard_b64encode(image_data).decode()
        # Infer MIME type from URL suffix; default to jpeg.
        suffix = image_url.rsplit(".", 1)[-1].lower() if "." in image_url else "jpeg"
        mime = _MIME_MAP.get(suffix, "image/jpeg")
        data_url = f"data:{mime};base64,{b64}"

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Describe this image concisely and accurately. "
                                "Focus on key information, text visible in the image, "
                                "and any diagrams or data. "
                                "Reply in the same language as the text in the image "
                                "(Chinese if Chinese text is present, otherwise English)."
                            ),
                        },
                    ],
                }
            ],
            max_tokens=512,
        )
        return response.choices[0].message.content or ""


class OCRProcessor(ImageProcessor):
    """Extracts text from an image using pytesseract (English + Simplified Chinese)."""

    # Tesseract language string for English + Simplified Chinese.
    _LANG = "eng+chi_sim"

    def process(self, image_url: str) -> str:
        try:
            import pytesseract
            from PIL import Image
            import io
        except ImportError as exc:
            raise RuntimeError(
                "OCR requires 'pytesseract' and 'Pillow'. "
                "Install them and ensure Tesseract is available on PATH."
            ) from exc

        image_data = _fetch_image_bytes(image_url)
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image, lang=self._LANG)
        return text.strip()


class NullProcessor(ImageProcessor):
    """No-op processor — returns an empty string without fetching the image."""

    def process(self, image_url: str) -> str:
        return ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MIME_MAP: dict[str, str] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}

_FETCH_TIMEOUT = 15  # seconds


def _fetch_image_bytes(url: str) -> bytes:
    """Download image bytes from an HTTP/HTTPS URL.

    Raises
    ------
    ImageFetchError
        If the URL is unreachable, returns an HTTP error status, or times out.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Only HTTP/HTTPS URLs are supported, got: {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": "DocMind-ImageProcessor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:  # noqa: S310
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise ImageFetchError(f"HTTP {exc.code} fetching image: {url}") from exc
    except urllib.error.URLError as exc:
        raise ImageFetchError(f"Failed to reach image URL: {url} — {exc.reason}") from exc
    except TimeoutError as exc:
        raise ImageFetchError(f"Timed out fetching image: {url}") from exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_image_processor() -> ImageProcessor:
    """Instantiate the ImageProcessor selected by IMAGE_PROCESSOR.

    Config validation (missing vars, invalid mode) is enforced at startup via
    lifespan.py, so by the time this is called the settings are guaranteed valid.
    """
    from docmind.core.config import settings

    mode = settings.ingestion.image_processor
    if mode == "multimodal":
        vision = settings.ingestion.image_vision
        logger.debug("image_processor_init", {"mode": "multimodal", "model": vision.model})
        return MultimodalProcessor(
            api_key=vision.api_key,
            model=vision.model,
            base_url=vision.base_url,
        )
    if mode == "ocr":
        logger.debug("image_processor_init", {"mode": "ocr"})
        return OCRProcessor()

    logger.debug("image_processor_init", {"mode": "none"})
    return NullProcessor()
