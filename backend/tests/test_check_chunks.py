"""Test cho script kiểm tra chunk RAG-06 (mã lỗi gắn với AC-01…AC-04)."""

from __future__ import annotations

from pathlib import Path

from scripts.check_chunks import (
    ChunkView,
    check_chunks,
    check_mid_word_start,
    check_noise_chunk,
    check_parent_spans_articles,
    check_search_text,
    check_short_chunk,
    views_from_data,
)


def _view(**overrides) -> ChunkView:
    defaults = dict(
        ref="doc::parent-0::child-0",
        document_title="Sổ tay D26",
        text="##### Điều 33. Cảnh báo kết quả học tập\n\nSinh viên bị cảnh báo khi chưa đạt điều kiện.",
        search_text="Sổ tay D26 > Quy chế > Điều 33. Cảnh báo kết quả học tập\nSinh viên bị cảnh báo khi chưa đạt điều kiện.",
        section_path="Quy chế > Điều 33. Cảnh báo kết quả học tập",
        parent_ref="doc::parent-0",
        parent_text="##### Điều 33. Cảnh báo kết quả học tập\n\nSinh viên bị cảnh báo khi chưa đạt điều kiện.",
    )
    defaults.update(overrides)
    return ChunkView(**defaults)


def test_clean_view_produces_no_findings() -> None:
    assert check_chunks([_view()]) == []


def test_parent_with_two_article_headings_is_flagged() -> None:
    finding = check_parent_spans_articles(
        "doc::parent-0",
        "##### Điều 1. Học phí\n\nNội dung.\n\n##### Điều 2. BHYT\n\nNội dung khác.",
    )

    assert finding is not None
    assert finding.code == "parent_spans_articles"


def test_chunk_starting_with_lowercase_is_flagged() -> None:
    assert check_mid_word_start("c", "ụng ......40") is not None
    assert check_mid_word_start("c", "Sinh viên nộp hồ sơ.") is None


def test_short_chunk_allowed_when_parent_body_is_short() -> None:
    text = "##### Điều 4. Tham chiếu\n\nTheo quy định của Học viện."

    assert check_short_chunk("c", text, text, min_chars=120) is None


def test_short_chunk_in_long_parent_is_flagged() -> None:
    parent = "##### Điều 33. Cảnh báo\n\n" + "Nội dung rất dài. " * 60

    finding = check_short_chunk("c", "chunk ngắn", parent, min_chars=120)

    assert finding is not None
    assert finding.code == "chunk_too_short"


def test_noise_patterns_are_flagged() -> None:
    for text in (
        "# MỤC LỤC\n\nHọc phí .............. 12",
        "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "TRƯỞNG PHÒNG\n\n(đã ký)\n\nNguyễn Chí Thành",
        "- 3 -",
    ):
        assert check_noise_chunk("c", text) is not None, text

    assert check_noise_chunk("c", "Sinh viên nộp học phí đúng hạn.") is None


def test_search_text_missing_document_title_is_flagged() -> None:
    finding = check_search_text(
        "c",
        search_text="Quy chế > Điều 33\nnội dung",
        document_title="Sổ tay D26",
        section_path="Quy chế > Điều 33",
    )

    assert finding is not None
    assert finding.code == "search_text_missing_context"


def test_views_from_data_dry_run_builds_clean_views(tmp_path: Path) -> None:
    source = tmp_path / "huong-dan-bhyt.md"
    source.write_text(
        "# Quy trình BHYT\n\n"
        "Sinh viên khai báo thông tin bảo hiểm y tế bắt buộc trong tháng đầu khóa học "
        "thông qua hệ thống một cửa của Học viện.",
        encoding="utf-8",
    )

    views, stats = views_from_data(tmp_path)

    assert stats["documents"] == 1
    assert stats["chunks"] == len(views) == 1
    assert views[0].search_text.startswith("huong-dan-bhyt > Quy trình BHYT\n")
    assert check_chunks(views) == []
