from __future__ import annotations

import re
from pathlib import Path

from app.core.config import PROJECT_ROOT, settings
from app.ingestion.loaders import SUPPORTED_EXTENSIONS

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PREVIEW_CHAR_LIMIT = 2500


class DocumentUploadError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def sanitize_filename(filename: str) -> str:
    raw = str(filename or "").replace("\\", "/").split("/")[-1].strip()
    if not raw:
        raise DocumentUploadError("Thiếu tên file.")

    if "." in raw:
        stem, suffix = raw.rsplit(".", 1)
        suffix = f".{suffix.lower()}"
    else:
        stem, suffix = raw, ""

    cleaned_stem = re.sub(r"[^\w.\- ]+", "_", stem, flags=re.UNICODE).strip(" .")
    if not cleaned_stem:
        cleaned_stem = "tai-lieu"
    return f"{cleaned_stem}{suffix}"


def decode_document_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentUploadError("Tài liệu phải được mã hóa UTF-8.")


def prepare_upload(filename: str, content: bytes, documents_path: Path) -> Path:
    if not content:
        raise DocumentUploadError("File tải lên đang trống.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentUploadError(
            "File vượt quá dung lượng tối đa 10MB.",
            status_code=413,
        )

    safe_name = sanitize_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise DocumentUploadError(f"Chỉ hỗ trợ tài liệu {allowed}.")

    text = decode_document_text(content)
    if not text.strip():
        raise DocumentUploadError("Tài liệu không có nội dung.")

    documents_path.mkdir(parents=True, exist_ok=True)
    destination = documents_path / safe_name
    destination.write_text(text, encoding="utf-8")
    return destination


def resolve_source_path(source_path: str) -> Path | None:
    if not source_path:
        return None

    path = Path(source_path)
    documents_root = settings.documents_path.resolve()
    project_root = PROJECT_ROOT.resolve()

    # 1. Thử các đường dẫn trực tiếp (tuyệt đối, theo project_root, hoặc theo documents_root)
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.append(project_root / path)
        candidates.append(documents_root / path)

    for cand in candidates:
        try:
            resolved = cand.resolve()
            if resolved.is_file():
                resolved.relative_to(project_root)
                return resolved
        except (OSError, ValueError):
            continue

    # 2. Tìm kiếm theo tên file trong documents_path (bao gồm các thư mục con như processed/, raw/, ...)
    filename = path.name
    try:
        if documents_root.exists():
            for found in documents_root.rglob(filename):
                if found.is_file():
                    resolved = found.resolve()
                    resolved.relative_to(project_root)
                    return resolved
    except (OSError, ValueError):
        pass

    return None


def read_preview(source_path: str, limit: int = PREVIEW_CHAR_LIMIT) -> str | None:
    path = resolve_source_path(source_path)
    if path is None or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "…"
    except Exception:
        return None


def delete_source_file(source_path: str) -> None:
    path = resolve_source_path(source_path)
    if path is None or not path.is_file():
        return
    try:
        path.unlink()
    except OSError:
        return
