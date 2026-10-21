"""Parse PDF/DOCX with Docling and cache raw Markdown exports by file hash."""

from __future__ import annotations

import logging
import re
import unicodedata
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings
from app.parsers.base import DocumentParseError

logger = logging.getLogger(__name__)

DOCLING_EXTENSIONS = frozenset({".pdf", ".docx"})

# Bump when conversion options change so stale cache entries are ignored. Post-processing
# runs on read and does not need a bump.
_CONVERTER_VERSION = "docling-v2"

_GPU_BATCH_SIZE = 32

_converter: Any | None = None
_converter_options: tuple[bool, str] | None = None
_converter_lock = Lock()
_conversion_lock = Lock()


class DoclingParser:
    name = "docling"
    extensions = DOCLING_EXTENSIONS

    def parse(self, path: Path, *, convert: bool = True) -> str | None:
        # Raw exports are post-processed on every read, including cached previews.
        cache_path = _cache_path(path)
        if cache_path.is_file():
            return _postprocess_markdown(cache_path.read_text(encoding="utf-8"))
        if not convert:
            return None

        exported = convert_with_docling(path)
        markdown = _postprocess_markdown(exported)
        if not markdown.strip():
            raise DocumentParseError(
                f"{path.name} không có nội dung văn bản (có thể là file scan, hãy bật DOCLING_OCR_ENABLED)."
            )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(exported, encoding="utf-8")
        return markdown


def convert_with_docling(path: Path) -> str:
    """Return Docling's raw Markdown export for a PDF/DOCX file."""
    logger.info("Converting %s with Docling...", path.name)
    try:
        converter = _get_converter()
        # Serialize runs: concurrent conversions on one converter compete for the same models.
        with _conversion_lock:
            result = converter.convert(path)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Không thể chuyển đổi {path.name}: {exc}") from exc

    return result.document.export_to_markdown(image_placeholder="")


def _get_converter() -> Any:
    """Build one shared DocumentConverter; its layout/table models are expensive to load."""
    global _converter, _converter_options
    options = (settings.docling_ocr_enabled, settings.docling_device)
    with _converter_lock:
        if _converter is not None and _converter_options == options:
            return _converter

        try:
            from docling.datamodel.accelerator_options import AcceleratorOptions
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError as exc:
            raise DocumentParseError('Chưa cài Docling. Chạy: pip install -e ".[docling]"') from exc

        use_gpu = _resolve_cuda(settings.docling_device)
        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = settings.docling_ocr_enabled
        pdf_options.do_table_structure = True
        pdf_options.accelerator_options = AcceleratorOptions(device=settings.docling_device)
        if use_gpu:
            # Defaults (4 pages per batch) are tuned for CPU and leave a GPU mostly idle.
            pdf_options.ocr_batch_size = _GPU_BATCH_SIZE
            pdf_options.layout_batch_size = _GPU_BATCH_SIZE
            pdf_options.table_batch_size = _GPU_BATCH_SIZE
        logger.info("Docling device: %s", "cuda" if use_gpu else "cpu")

        _converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF, InputFormat.DOCX],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)},
        )
        _converter_options = options
        return _converter


def _resolve_cuda(device: str) -> bool:
    """Return whether Docling will run on CUDA, warning when a requested GPU is unusable."""
    if device != "auto" and not device.startswith("cuda"):
        return False
    try:
        import torch
    except ImportError:
        return False
    if torch.cuda.is_available():
        return True
    if device.startswith("cuda"):
        # Docling silently falls back to CPU, which is ~10x slower on large handbooks.
        logger.warning(
            "DOCLING_DEVICE=%s nhưng torch %s không có CUDA; Docling sẽ chạy trên CPU. "
            "Cài torch bản CUDA: pip install torch torchvision --index-url "
            "https://download.pytorch.org/whl/cu13  0",
            device,
            torch.__version__,
        )
    return False


def _postprocess_markdown(markdown: str) -> str:
    # PDF text layers often carry decomposed Vietnamese diacritics; NFC keeps BM25 and
    # embeddings consistent with user queries.
    markdown = unicodedata.normalize("NFC", markdown)
    markdown = re.sub(r"<!--\s*image\s*-->", "", markdown)
    # Docling escapes "&" in text ("CT&amp;CTSV"); "<"/">" stay escaped so they never look like HTML.
    markdown = markdown.replace("&amp;", "&")
    markdown = _BOLD_LINE.sub(_promote_bold_line, markdown)
    markdown = _TABLE_LINE.sub(_compact_table_line, markdown)
    return re.sub(r"\n{3,}", "\n\n", markdown).strip() + "\n"


# Word files from the school mark headings with bold paragraphs instead of Heading styles.
# Promote a line that is entirely bold so the chunker can build section paths.
_BOLD_LINE = re.compile(r"^\*\*([^*\n]{2,150}?)\*\*[ \t]*$", re.MULTILINE)


# Docling pads every table cell to the widest one for alignment; the padding can be
# ~140 spaces per cell and would dominate character-based chunk sizes.
_TABLE_LINE = re.compile(r"^\|.*\|[ \t]*$", re.MULTILINE)


def _compact_table_line(match: re.Match[str]) -> str:
    line = match.group(0).rstrip()
    if re.fullmatch(r"\|(?:\s*:?-+:?\s*\|)+", line):
        return re.sub(r"-{3,}", "---", line.replace(" ", ""))
    # Equal values can be independent cells; Markdown alone cannot identify spans.
    return re.sub(r"[ \t]{2,}", " ", line)


def _promote_bold_line(match: re.Match[str]) -> str:
    title = match.group(1).strip().rstrip(":").strip()
    level = "#" if title == title.upper() and any(char.isalpha() for char in title) else "##"
    return f"{level} {title}"


def _cache_path(path: Path) -> Path:
    digest = sha256()
    digest.update(_CONVERTER_VERSION.encode())
    digest.update(b"ocr" if settings.docling_ocr_enabled else b"no-ocr")
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return settings.converted_documents_path / f"{digest.hexdigest()}.md"
