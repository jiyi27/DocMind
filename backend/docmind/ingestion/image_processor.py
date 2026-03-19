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

from langchain_core.messages import HumanMessage

from docmind.core import logger
from docmind.core.llm import get_image_llm
from docmind.ingestion.prompts import image_summarization_prompt


class ImageFetchError(Exception):
    """Raised when the image URL cannot be fetched (dead link, timeout, HTTP error, etc.)."""


class ImageProcessor(ABC):
    @abstractmethod
    def process(self, image_url: str) -> str:
        """Fetch the image at *image_url* and return a text description/extraction."""


class MultimodalProcessor(ImageProcessor):
    """Generates a natural-language description of an image via a vision LLM."""

    def process(self, image_url: str) -> str:
        image_data = _fetch_image_bytes(image_url)
        b64 = base64.standard_b64encode(image_data).decode()
        # Infer MIME type from URL suffix; default to jpeg.
        suffix = image_url.rsplit(".", 1)[-1].lower() if "." in image_url else "jpeg"
        mime = _MIME_MAP.get(suffix, "image/jpeg")
        data_url = f"data:{mime};base64,{b64}"
        llm = get_image_llm()

        response = llm.invoke(
            [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": image_summarization_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ]
                )
            ]
        )
        return _message_content_to_text(response.content)


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


def _message_content_to_text(content: str | list[object]) -> str:
    """Normalize LangChain message content into plain text."""
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(part.strip() for part in parts if part.strip()).strip()


def _fetch_image_bytes(url: str) -> bytes:
    """Download image bytes from an HTTP/HTTPS URL.

    Raises
    ------
    ImageFetchError
        If the URL is unreachable, returns an HTTP error status, or times out.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Only HTTP/HTTPS URLs are supported, got: {url!r}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "DocMind-ImageProcessor/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:  # noqa: S310
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise ImageFetchError(f"HTTP {exc.code} fetching image: {url}") from exc
    except urllib.error.URLError as exc:
        raise ImageFetchError(
            f"Failed to reach image URL: {url} — {exc.reason}"
        ) from exc
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
        logger.debug(
            "image_processor_init", {"mode": "multimodal", "model": vision.model}
        )
        return MultimodalProcessor()
    if mode == "ocr":
        logger.debug("image_processor_init", {"mode": "ocr"})
        return OCRProcessor()

    logger.debug("image_processor_init", {"mode": "none"})
    return NullProcessor()
