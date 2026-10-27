"""Parse PDF/DOCX with Docling and cache raw Markdown exports by file hash."""

from __future__ import annotations

import inspect
import logging
import re
from hashlib import sha256
from pathlib import Path
from threading import Event, Lock, Thread, get_ident
from typing import Any

from app.core.config import settings
from app.parsers.base import DocumentParseError, ProgressCallback

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

# Docling builds a ConversionResult internally and never yields it while running.
# The converter subclass records the current result for the worker thread so a
# monitor thread can report how many pages have been assembled. This is a
# best-effort read of Docling's page objects; parsing itself is unchanged.
_conversion_results: dict[int, Any] = {}
_conversion_results_lock = Lock()
_instrumented_pipelines: set[int] = set()


class DoclingParser:
    name = "docling"
    extensions = DOCLING_EXTENSIONS

    def parse(
        self,
        path: Path,
        *,
        convert: bool = True,
        on_progress: ProgressCallback | None = None,
    ) -> str | None:
        # Raw exports are post-processed on every read, including cached previews.
        cache_path = _cache_path(path)
        if cache_path.is_file():
            if on_progress is not None:
                on_progress(80, "Đã có bản parse trong cache")
            return _postprocess_markdown(cache_path.read_text(encoding="utf-8"))
        if not convert:
            return None

        exported = (
            convert_with_docling(path, on_progress=on_progress)
            if on_progress is not None
            else convert_with_docling(path)
        )
        if on_progress is not None:
            on_progress(94, "Đang xử lý Markdown")
        markdown = _postprocess_markdown(exported)
        if not markdown.strip():
            raise DocumentParseError(
                f"{path.name} không có nội dung văn bản (có thể là file scan, hãy bật DOCLING_OCR_ENABLED)."
            )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(exported, encoding="utf-8")
        return markdown


def convert_with_docling(path: Path, *, on_progress: ProgressCallback | None = None) -> str:
    """Return Docling's raw Markdown export for a PDF/DOCX file."""
    logger.info("Converting %s with Docling...", path.name)
    worker_id = get_ident()
    stop = Event()
    monitor: Thread | None = None
    try:
        converter = _get_converter()
        # Serialize runs: concurrent conversions on one converter compete for the same models.
        with _conversion_lock:
            try:
                if on_progress is None:
                    result = converter.convert(path)
                else:
                    on_progress(5, "Đang khởi động Docling")
                    if _supports_native_progress(converter):
                        result = converter.convert(
                            path, progress_callback=_native_progress_callback(on_progress)
                        )
                    else:
                        # Older Docling: read its ConversionResult while it runs.
                        monitor = Thread(
                            target=_monitor_conversion,
                            args=(worker_id, stop, on_progress),
                            name="docling-progress",
                            daemon=True,
                        )
                        monitor.start()
                        result = converter.convert(path)
            finally:
                stop.set()
                if monitor is not None:
                    monitor.join(timeout=1)
                with _conversion_results_lock:
                    _conversion_results.pop(worker_id, None)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Không thể chuyển đổi {path.name}: {exc}") from exc

    if on_progress is not None:
        on_progress(92, "Đang xuất Markdown")
    return result.document.export_to_markdown(image_placeholder="")


def _supports_native_progress(converter: Any) -> bool:
    """Docling >= 2.142 can report page progress without introspection."""
    try:
        return "progress_callback" in inspect.signature(converter.convert).parameters
    except (TypeError, ValueError):
        return False


def _native_progress_callback(on_progress: ProgressCallback):
    def callback(event: Any) -> None:
        kind = _event_value(getattr(event, "kind", ""))
        if kind == "document_started":
            on_progress(5, "Bắt đầu xử lý tài liệu")
        elif kind == "phase_started":
            phase = _event_value(getattr(event, "phase", ""))
            phases = {
                "initialize": (8, "Đang khởi tạo Docling"),
                "build": (10, "Đang phân tích trang"),
                "assemble": (85, "Đang hoàn thiện cấu trúc tài liệu"),
                "enrich": (88, "Đang xử lý bảng và nội dung"),
            }
            percent, message = phases.get(phase, (10, "Đang parse tài liệu"))
            on_progress(percent, message)
        elif kind == "page_completed":
            total = int(getattr(event, "total_pages", 0) or 0)
            done = int(getattr(event, "completed_pages", 0) or 0)
            if total > 0:
                on_progress(10 + round(70 * done / total), f"Đang parse {done}/{total} trang")
        elif kind == "enrichment_progress":
            total = int(getattr(event, "total_items", 0) or 0)
            done = int(getattr(event, "completed_items", 0) or 0)
            label = getattr(event, "label", "") or "nội dung"
            if total > 0:
                on_progress(88 + round(4 * done / total), f"Đang xử lý {label} ({done}/{total})")
        elif kind == "document_completed":
            on_progress(92, "Đã xử lý xong tài liệu")

    return callback


def _event_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _monitor_conversion(worker_id: int, stop: Event, on_progress: ProgressCallback) -> None:
    """Fallback for Docling versions without progress_callback."""
    while not stop.wait(0.5):
        with _conversion_results_lock:
            conv_res = _conversion_results.get(worker_id)
        if conv_res is None:
            continue
        update = _docling_progress(conv_res)
        if update is not None:
            on_progress(*update)


def _docling_progress(conv_res: Any) -> tuple[int, str] | None:
    """Map Docling's assembled pages to a 5–90% progress range."""
    pages = list(getattr(conv_res, "pages", ()) or ())
    total = len(pages)
    if total <= 0:
        total = int(getattr(getattr(conv_res, "input", None), "page_count", 0) or 0)
    if total <= 0:
        return None

    done = sum(1 for page in pages if getattr(page, "assembled", None) is not None)
    if done >= total:
        return 90, "Đang hoàn thiện cấu trúc tài liệu"
    percent = 5 + round(85 * done / total)
    return percent, f"Đang parse {done}/{total} trang"


def _instrument_pipeline(pipeline: Any) -> None:
    """Wrap one Docling pipeline so its ConversionResult is visible while it runs."""
    key = id(pipeline)
    with _conversion_results_lock:
        if key in _instrumented_pipelines:
            return
        original = getattr(pipeline, "_build_document", None)
        if original is None:
            return

        def build_with_progress(conv_res: Any) -> Any:
            with _conversion_results_lock:
                _conversion_results[get_ident()] = conv_res
            return original(conv_res)

        pipeline._build_document = build_with_progress
        _instrumented_pipelines.add(key)


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
            raise DocumentParseError(
                "Chưa cài Docling. Chạy: pip install -e \".[docling]\""
            ) from exc

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

        class _ProgressDocumentConverter(DocumentConverter):
            """Expose the running pipeline so progress can read assembled pages."""

            def _execute_pipeline(self, in_doc: Any, raises_on_error: bool, **kwargs: Any) -> Any:
                try:
                    pipeline = self._get_pipeline(in_doc.format)
                    if pipeline is not None:
                        _instrument_pipeline(pipeline)
                except Exception:
                    # Progress is best-effort; conversion must still work.
                    logger.debug("Cannot instrument Docling pipeline for progress", exc_info=True)
                return super()._execute_pipeline(
                    in_doc, raises_on_error=raises_on_error, **kwargs
                )

        _converter = _ProgressDocumentConverter(
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
    # Docling-specific cleanup only. NFC, unescaping and heading levels (including bold
    # paragraphs used as headings in the school's Word files) run for every parser in
    # app.parsers.normalize.
    markdown = re.sub(r"<!--\s*image\s*-->", "", markdown)
    markdown = _TABLE_LINE.sub(_compact_table_line, markdown)
    return re.sub(r"\n{3,}", "\n\n", markdown).strip() + "\n"


# Docling pads every table cell to the widest one for alignment; the padding can be
# ~140 spaces per cell and would dominate character-based chunk sizes.
_TABLE_LINE = re.compile(r"^\|.*\|[ \t]*$", re.MULTILINE)


def _compact_table_line(match: re.Match[str]) -> str:
    line = match.group(0).rstrip()
    if re.fullmatch(r"\|(?:\s*:?-+:?\s*\|)+", line):
        return re.sub(r"-{3,}", "---", line.replace(" ", ""))
    # Equal values can be independent cells; Markdown alone cannot identify spans.
    return re.sub(r"[ \t]{2,}", " ", line)


def _cache_path(path: Path) -> Path:
    digest = sha256()
    digest.update(_CONVERTER_VERSION.encode())
    digest.update(b"ocr" if settings.docling_ocr_enabled else b"no-ocr")
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return settings.converted_documents_path / f"{digest.hexdigest()}.md"
