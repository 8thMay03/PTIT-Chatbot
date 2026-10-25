"""Parse PDF/DOCX with LlamaParse (LlamaCloud) and cache raw Markdown exports by file hash.

An optional alternative to Docling that admins pick per document; it uploads the file to
LlamaCloud and spends credits, so it is registered only when explicitly enabled.
"""

from __future__ import annotations

import logging
import re
from hashlib import sha256
from pathlib import Path
from time import monotonic
from typing import Any

from app.core.config import settings
from app.parsers.base import DocumentParseError

logger = logging.getLogger(__name__)

LLAMAPARSE_EXTENSIONS = frozenset({".pdf", ".docx"})

# Bump when request options change so stale cache entries are ignored. Post-processing
# runs on read and does not need a bump.
_CONVERTER_VERSION = "llamaparse-v1"

_CLIENT_NAME = "ptit-chatbot"


def llamaparse_available() -> bool:
    return settings.llamaparse_enabled and bool((settings.llama_cloud_api_key or "").strip())


class LlamaParseParser:
    name = "llamaparse"
    extensions = LLAMAPARSE_EXTENSIONS

    def parse(self, path: Path, *, convert: bool = True) -> str | None:
        # Raw exports are post-processed on every read, including cached previews.
        cache_path = _cache_path(path)
        if cache_path.is_file():
            return _postprocess_markdown(cache_path.read_text(encoding="utf-8"))
        if not convert:
            return None

        exported = convert_with_llamaparse(path)
        markdown = _postprocess_markdown(exported)
        if not markdown.strip():
            raise DocumentParseError(f"LlamaParse không trích được nội dung văn bản từ {path.name}.")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(exported, encoding="utf-8")
        return markdown


def convert_with_llamaparse(path: Path) -> str:
    """Return LlamaParse's raw Markdown for a PDF/DOCX file, pages joined in order."""
    if not llamaparse_available():
        raise DocumentParseError(
            "LlamaParse chưa được cấu hình: cần LLAMAPARSE_ENABLED=true và LLAMA_CLOUD_API_KEY."
        )
    logger.info("Parsing %s with LlamaParse (tier %s)...", path.name, settings.llamaparse_tier)
    started = monotonic()
    result = _parse_remote(path)
    markdown, page_count = _markdown_from_result(result, path.name)
    usage = getattr(getattr(result, "job", None), "usage", None)
    logger.info(
        "LlamaParse parsed %s: %d pages, %s credits, %.1fs",
        path.name,
        page_count,
        getattr(usage, "credits", None),
        monotonic() - started,
    )
    return markdown


def _parse_remote(path: Path) -> Any:
    """Upload one file, wait for the parse job and return the SDK result."""
    try:
        import llama_cloud
    except ImportError as exc:
        raise DocumentParseError(
            "Chưa cài LlamaParse SDK. Chạy: pip install -e \".[llamaparse]\""
        ) from exc

    timeout = settings.llamaparse_timeout_seconds
    try:
        with llama_cloud.LlamaCloud(
            api_key=settings.llama_cloud_api_key,
            base_url=settings.llamaparse_base_url or None,
            max_retries=settings.llamaparse_max_retries,
            # The SDK's 60 s request default is too short to upload large handbooks.
            timeout=timeout,
        ) as client, path.open("rb") as handle:
            return client.parsing.parse(
                tier=settings.llamaparse_tier,
                version=settings.llamaparse_version,
                upload_file=(path.name, handle),
                expand=["markdown"],
                processing_options={"ocr_parameters": {"languages": [settings.llamaparse_language]}},
                # Pipe tables like Docling, so chunking treats both parsers' tables alike.
                output_options={
                    "markdown": {
                        "tables": {"output_tables_as_markdown": True, "compact_markdown_tables": True}
                    }
                },
                client_name=_CLIENT_NAME,
                timeout=timeout,
            )
    except llama_cloud.PollingTimeoutError as exc:
        raise DocumentParseError(
            f"LlamaParse quá thời gian chờ {timeout:.0f} giây khi parse {path.name}; "
            "tăng LLAMAPARSE_TIMEOUT_SECONDS hoặc thử lại sau."
        ) from exc
    except llama_cloud.PollingError as exc:
        raise DocumentParseError(f"LlamaParse không parse được {path.name}: {exc}") from exc
    except llama_cloud.APIStatusError as exc:
        # The SDK already retried 408/409/429/5xx; the response body is not echoed.
        raise DocumentParseError(_status_message(exc.status_code, path.name)) from exc
    except llama_cloud.APIConnectionError as exc:
        raise DocumentParseError(f"Không kết nối được LlamaCloud khi parse {path.name}.") from exc


def _status_message(status_code: int, file_name: str) -> str:
    if status_code == 401:
        return "LLAMA_CLOUD_API_KEY không hợp lệ hoặc đã bị thu hồi."
    if status_code == 402:
        return f"Tài khoản LlamaCloud đã hết credit, không parse được {file_name}."
    if status_code == 429:
        return f"LlamaCloud đang giới hạn tần suất gọi, thử parse {file_name} lại sau."
    return f"LlamaCloud trả lỗi HTTP {status_code} khi parse {file_name}."


def _markdown_from_result(result: Any, file_name: str) -> tuple[str, int]:
    pages = list(getattr(getattr(result, "markdown", None), "pages", None) or [])
    pages.sort(key=lambda page: getattr(page, "page_number", 0))
    # Running headers/footers come back in separate fields and are intentionally dropped.
    texts = [page.markdown.strip() for page in pages if getattr(page, "success", False) and page.markdown]
    failed = [page.page_number for page in pages if not getattr(page, "success", False)]
    if failed:
        if not texts:
            raise DocumentParseError(f"LlamaParse không parse được trang nào của {file_name}.")
        logger.warning(
            "LlamaParse bỏ qua %d trang lỗi của %s: %s", len(failed), file_name, failed[:20]
        )
    return "\n\n".join(text for text in texts if text), len(pages)


def _postprocess_markdown(markdown: str) -> str:
    # LlamaParse-specific cleanup only; headings and NFC run for every parser in
    # app.parsers.normalize. Images are not stored, so their references are noise.
    markdown = _IMAGE.sub("", markdown)
    return re.sub(r"\n{3,}", "\n\n", markdown).strip() + "\n"


_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def _cache_path(path: Path) -> Path:
    digest = sha256()
    for part in (
        _CONVERTER_VERSION,
        settings.llamaparse_tier,
        settings.llamaparse_version,
        settings.llamaparse_language,
    ):
        digest.update(part.encode())
        digest.update(b"\0")
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return settings.converted_documents_path / "llamaparse" / f"{digest.hexdigest()}.md"
