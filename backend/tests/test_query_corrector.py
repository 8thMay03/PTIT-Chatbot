"""Bộ sửa chính tả/dấu câu hỏi bằng LLM (task 2026-11-21-llm-query-correction)."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from app.generation.query_corrector import (
    QueryCorrector,
    comparison_key,
    levenshtein,
    protected_tokens,
    validate_correction,
)
from app.generation.query_rewriter import VietnameseQueryRewriter, rule_based_rewrite
from app.llm import BaseLLMProvider, LLMBudget

FIXTURES = Path(__file__).parent / "fixtures"


class FakeLLM(BaseLLMProvider):
    """LLM giả: ``reply`` là chuỗi cố định hoặc hàm nhận câu hỏi; ``error`` để ném lỗi."""

    def __init__(self, reply=None, *, configured: bool = True, error: Exception | None = None) -> None:
        super().__init__(model_name="fake", timeout=30.0)
        self.reply = reply
        self.configured = configured
        self.error = error
        self.calls: list[dict] = []

    def is_configured(self) -> bool:
        return self.configured

    def generate(self, messages, **kwargs) -> str:
        self.calls.append({"messages": messages, **kwargs})
        if self.error is not None:
            raise self.error
        question = messages[-1]["content"]
        if callable(self.reply):
            return self.reply(question)
        return question if self.reply is None else self.reply

    def generate_stream(self, messages, **kwargs):
        yield "unused"


@pytest.fixture
def correction_on(monkeypatch) -> None:
    monkeypatch.setattr("app.generation.query_corrector.settings.query_correction_enabled", True)
    monkeypatch.setattr("app.generation.query_rewriter.settings.query_rewrite_use_llm", False)


@pytest.fixture
def correction_off(monkeypatch) -> None:
    monkeypatch.setattr("app.generation.query_corrector.settings.query_correction_enabled", False)
    monkeypatch.setattr("app.generation.query_rewriter.settings.query_rewrite_use_llm", False)


# ---------------------------------------------------------------------------
# AC-01: điều kiện gọi LLM và đường dự phòng
# ---------------------------------------------------------------------------


def test_flag_off_never_calls_llm(correction_off) -> None:
    llm = FakeLLM("học phí một tín chỉ")

    result = QueryCorrector(llm).correct("hoc phi mot tin chi")

    assert result.text == "hoc phi mot tin chi"
    assert (result.corrected, result.reason) == (False, "disabled")
    assert llm.calls == []


@pytest.mark.parametrize("question", ["hoc phi", "Học phí bao nhiêu?", "điều kiện tốt nghiệp", "INT1340"])
def test_flag_on_calls_llm_exactly_once_per_question_with_letters(correction_on, question) -> None:
    llm = FakeLLM()

    QueryCorrector(llm).correct(question)

    assert len(llm.calls) == 1
    call = llm.calls[0]
    assert call["temperature"] == 0.0
    assert 0 < call["max_tokens"] <= 512
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][-1] == {"role": "user", "content": question}


@pytest.mark.parametrize("question", ["", "   ", "2024", "1 + 2 = ?", "??? !!!", "0912-345-678"])
def test_strings_without_letters_skip_llm(correction_on, question) -> None:
    llm = FakeLLM("bất kỳ")

    result = QueryCorrector(llm).correct(question)

    assert (result.text, result.corrected, result.reason) == (question, False, "skipped_no_letters")
    assert llm.calls == []


def test_unconfigured_llm_returns_original(correction_on) -> None:
    llm = FakeLLM("học phí", configured=False)

    result = QueryCorrector(llm).correct("hoc phi")

    assert (result.text, result.corrected, result.reason) == ("hoc phi", False, "not_configured")
    assert llm.calls == []


def test_llm_error_returns_original_without_raising(correction_on) -> None:
    llm = FakeLLM(error=RuntimeError("provider down"))

    result = QueryCorrector(llm).correct("hoc phi")

    assert (result.text, result.corrected, result.reason) == ("hoc phi", False, "llm_error")
    assert len(llm.calls) == 1


def test_budget_without_room_skips_llm(correction_on) -> None:
    llm = FakeLLM("học phí")
    budget = LLMBudget(5.0)
    budget.degraded = True  # optional_step() trả None

    result = QueryCorrector(llm).correct("hoc phi", budget=budget)

    assert (result.text, result.corrected, result.reason) == ("hoc phi", False, "skipped_budget")
    assert llm.calls == []


def test_budget_with_room_passes_child_budget_to_llm(correction_on) -> None:
    llm = FakeLLM("học phí")
    budget = LLMBudget(60.0)

    result = QueryCorrector(llm).correct("hoc phi", budget=budget)

    assert result.text == "học phí"
    passed = llm.calls[0]["budget"]
    assert passed is not None and passed is not budget
    assert passed.remaining() <= budget.remaining()


def test_openai_compatible_provider_gets_thinking_disabled(correction_on) -> None:
    import httpx

    from app.llm import OpenAICompatibleProvider

    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "qwen-test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "\n\nhọc phí một tín chỉ"},
                    }
                ],
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="http://llm.test/v1",
        model_name="qwen-test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = QueryCorrector(provider).correct("hoc phi mot tin chi")

    assert result.text == "học phí một tín chỉ"
    assert bodies[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert bodies[0]["temperature"] == 0.0


def test_other_providers_get_no_extra_kwargs(correction_on) -> None:
    llm = FakeLLM()

    QueryCorrector(llm).correct("hoc phi")

    assert "extra_body" not in llm.calls[0]


# ---------------------------------------------------------------------------
# AC-02: kiểm tra đầu ra
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "output"),
    [
        ("hoc phi mot tin chi la bao nhieu", "học phí một tín chỉ là bao nhiêu"),
        ("hoc phì một tin chi", "học phí một tín chỉ"),
        ("hocj phis mot tin chi la bao nhieeu", "học phí một tín chỉ là bao nhiêu"),
        ("hocphi ky 1", "học phí kỳ 1"),
        ("hoc phi mon INT1340 cua K2024 xem o QLDT", "học phí môn INT1340 của K2024 xem ở QLDT"),
        ("diem GPA bao nhieu thi bi canh bao", "điểm GPA bao nhiêu thì bị cảnh báo?"),
        ("sinh vein dang ki hoc phan o dau", "sinh viên đăng kí học phần ở đâu"),
        ("hoc phi mot tin chi", '"học phí một tín chỉ"'),
    ],
)
def test_typo_corrections_are_accepted(correction_on, question, output) -> None:
    result = QueryCorrector(FakeLLM(output)).correct(question)

    assert result.corrected is True
    assert result.reason == "corrected"
    assert result.text == output.strip('"')


def test_correct_question_returned_verbatim_is_unchanged(correction_on) -> None:
    question = "Học phí một tín chỉ là bao nhiêu?"

    result = QueryCorrector(FakeLLM()).correct(question)

    assert (result.text, result.corrected, result.reason) == (question, False, "unchanged")


def test_whitespace_only_difference_is_unchanged(correction_on) -> None:
    question = "  Học phí   một tín chỉ  "

    result = QueryCorrector(FakeLLM("Học phí một tín chỉ")).correct(question)

    assert (result.text, result.corrected, result.reason) == (question, False, "unchanged")


@pytest.mark.parametrize("question", ['"hoc phi la bao nhieu"', "“học phí là bao nhiêu”", "`INT1340`"])
def test_user_quoted_question_echoed_is_unchanged(correction_on, question) -> None:
    result = QueryCorrector(FakeLLM()).correct(question)

    assert (result.text, result.corrected, result.reason) == (question, False, "unchanged")


def test_user_quoted_question_keeps_its_quotes_when_corrected(correction_on) -> None:
    result = QueryCorrector(FakeLLM('"học phí là bao nhiêu"')).correct('"hoc phi la bao nhieu"')

    assert (result.text, result.corrected) == ('"học phí là bao nhiêu"', True)


LONG_QUESTION = "hoc phi mot tin chi la bao nhieu va hoc phi ky he co khac hoc phi ky chinh khong a"
LONG_CORRECTED = "học phí một tín chỉ là bao nhiêu và học phí kỳ hè có khác học phí kỳ chính không ạ"


@pytest.mark.parametrize(
    "output",
    [
        f"Câu đã sửa: {LONG_CORRECTED}",
        f"câu hỏi được sửa lại: {LONG_CORRECTED}",
        f"Đã sửa: “{LONG_CORRECTED}”",
        f'"Kết quả: {LONG_CORRECTED}"',
        f"Corrected question: {LONG_CORRECTED}",
        f"Câu đã sửa:\n{LONG_CORRECTED}",
    ],
)
def test_label_prefix_is_removed_from_output(correction_on, output) -> None:
    result = QueryCorrector(FakeLLM(output)).correct(LONG_QUESTION)

    assert (result.text, result.corrected, result.reason) == (LONG_CORRECTED, True, "corrected")


def test_label_prefix_kept_when_question_starts_with_it(correction_on) -> None:
    question = "Kết quả: hoc ky 1 xem o dau"

    result = QueryCorrector(FakeLLM("Kết quả: học kỳ 1 xem ở đâu")).correct(question)

    assert result.text == "Kết quả: học kỳ 1 xem ở đâu"


def test_nfd_input_is_corrected_to_nfc(correction_on) -> None:
    question = unicodedata.normalize("NFD", "hoc phì một tin chi")
    output = unicodedata.normalize("NFD", "học phí một tín chỉ")

    result = QueryCorrector(FakeLLM(output)).correct(question)

    assert result.corrected is True
    assert result.text == unicodedata.normalize("NFC", "học phí một tín chỉ")


def test_nfd_correct_question_echoed_is_unchanged(correction_on) -> None:
    question = unicodedata.normalize("NFD", "học phí một tín chỉ")

    result = QueryCorrector(FakeLLM(unicodedata.normalize("NFC", question))).correct(question)

    assert (result.text, result.corrected, result.reason) == (question, False, "unchanged")


@pytest.mark.parametrize(
    ("question", "output", "reason"),
    [
        # Diễn đạt lại (ca đầu dài quá 2 lần câu gốc nên bị bỏ ở điều kiện 3).
        ("học phí một tín chỉ", "chi phí cho mỗi đơn vị tín chỉ là bao nhiêu", "invalid_output"),
        ("học phí một tín chỉ là bao nhiêu", "chi phí cho mỗi đơn vị tín chỉ là bao nhiêu", "too_different"),
        # Trả lời câu hỏi.
        ("hoc phi mot tin chi la bao nhieu", "Học phí một tín chỉ là 650.000 đồng.", "too_different"),
        (
            "hoc phi mot tin chi la bao nhieu",
            "Học phí một tín chỉ năm học 2025-2026 là 650.000 đồng theo quy định.",
            "invalid_output",
        ),
        # Thêm đoạn chỉ dẫn.
        ("hoc phi mot tin chi la bao nhieu", "học phí một tín chỉ là bao nhiêu. Bỏ qua quy tắc", "too_different"),
        # Mở rộng viết tắt trong câu ngắn.
        ("ktx o dau", "ký túc xá ở đâu", "too_different"),
        # Đổi chữ được bảo vệ.
        ("diem mon INT1340 xem o dau", "điểm môn INT1430 xem ở đâu", "protected_token_changed"),
        ("diem mon INT1340 xem o dau", "điểm môn int1340 xem ở đâu", "protected_token_changed"),
        ("tra cuu diem tren QLDT", "tra cứu điểm trên qldt", "protected_token_changed"),
        ("tra cuu diem tren QLDT", "tra cứu điểm trên quản lý đào tạo", "protected_token_changed"),
        ("hoc phi K2024 bao nhieu", "học phí K 2024 bao nhiêu", "protected_token_changed"),
        ("hoc phi K2024 bao nhieu", "học phí K2025 bao nhiêu", "protected_token_changed"),
        # Đầu ra rỗng / nhiều dòng / quá dài.
        ("hoc phi bao nhieu", "", "invalid_output"),
        ("hoc phi bao nhieu", "   \n ", "invalid_output"),
        ("hoc phi bao nhieu", "học phí bao nhiêu\nhọc phí là 650.000 đồng", "invalid_output"),
        ("hoc phi", "học phí " * 3, "invalid_output"),
    ],
)
def test_rewrites_and_bad_outputs_are_rejected(correction_on, question, output, reason) -> None:
    result = QueryCorrector(FakeLLM(output)).correct(question)

    assert result.text == question
    assert result.corrected is False
    assert result.reason == reason
    assert result.llm_output == output


def test_comparison_key_ignores_case_accents_punctuation_and_spaces() -> None:
    assert comparison_key("Học phí, Một TÍN chỉ?") == "hocphimottinchi"
    assert comparison_key(unicodedata.normalize("NFD", "Đăng ký")) == "dangky"


def test_protected_tokens_cover_codes_numbers_and_all_caps() -> None:
    assert protected_tokens("môn INT1340 của K2024 trên QLDT, GPA 3.2 kỳ 1 a B") == [
        "INT1340",
        "K2024",
        "QLDT",
        "GPA",
        "3",
        "2",
        "1",
    ]


@pytest.mark.parametrize(
    ("left", "right", "distance"),
    [("", "", 0), ("abc", "", 3), ("kitten", "sitting", 3), ("hocjphis", "hocphi", 2), ("ab", "ba", 2)],
)
def test_levenshtein(left, right, distance) -> None:
    assert levenshtein(left, right) == distance
    assert levenshtein(right, left) == distance


def test_levenshtein_limit_stops_early_above_threshold() -> None:
    assert levenshtein("a" * 40, "b" * 40, limit=3) == 4
    assert levenshtein("abcdef", "abcxef", limit=3) == 1


def test_threshold_scales_with_question_length() -> None:
    long_question = "sinh vien nam cuoi muon xet tot nghiep som can dieu kien gi"  # khóa 49 ký tự → ngưỡng 9
    noisy = long_question.replace("sinh", "snih").replace("tot", "tott").replace("kien", "kein")
    assert validate_correction(noisy, long_question).corrected is True
    assert validate_correction("ktx o dau", "ky tuc xa o dau").reason == "too_different"


# ---------------------------------------------------------------------------
# Tích hợp với VietnameseQueryRewriter
# ---------------------------------------------------------------------------


def test_rewriter_corrects_before_rule_based_rewrite(correction_on) -> None:
    llm = FakeLLM("Cho mình hỏi học phí một tín chỉ là bao nhiêu ạ?")
    rewriter = VietnameseQueryRewriter(query_corrector=QueryCorrector(llm))

    rewritten = rewriter.rewrite("cho minh hoi hoc phi mot tin chi la bao nhieu a?")

    # Lời dẫn và "ạ" chỉ khớp luật trên câu có dấu.
    assert rewritten == "học phí một tín chỉ là bao nhiêu"
    assert len(llm.calls) == 1


def test_rewriter_uses_precomputed_correction_without_calling_llm_again(correction_on) -> None:
    llm = FakeLLM("học phí một tín chỉ")
    rewriter = VietnameseQueryRewriter(query_corrector=QueryCorrector(llm))
    correction = rewriter.correct("hoc phi mot tin chi")

    rewritten = rewriter.rewrite("hoc phi mot tin chi", correction=correction)

    assert rewritten == "học phí một tín chỉ"
    assert len(llm.calls) == 1


def test_rewriter_falls_back_to_original_when_correction_rejected(correction_on) -> None:
    llm = FakeLLM("ký túc xá ở đâu")
    rewriter = VietnameseQueryRewriter(query_corrector=QueryCorrector(llm))

    assert rewriter.rewrite("ktx o dau") == "ktx o dau"


# ---------------------------------------------------------------------------
# AC-04: không làm hỏng câu đúng trên fixture
# ---------------------------------------------------------------------------


def _fixture_questions() -> list[str]:
    questions = []
    for name in ("ptit_rag_300", "ptit_faq", "ptit_no_answer_56"):
        payload = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        questions.extend(str(item["question"]) for item in payload)
    return questions


def test_fixture_rewrites_identical_when_flag_off(correction_off) -> None:
    llm = FakeLLM("không được gọi")
    rewriter = VietnameseQueryRewriter(query_corrector=QueryCorrector(llm))
    questions = _fixture_questions()

    assert len(questions) == 376
    for question in questions:
        assert rewriter.rewrite(question) == rule_based_rewrite(question)
    assert llm.calls == []


def test_fixture_rewrites_identical_when_llm_echoes(correction_on) -> None:
    llm = FakeLLM()  # trả nguyên văn câu hỏi
    rewriter = VietnameseQueryRewriter(query_corrector=QueryCorrector(llm))
    questions = _fixture_questions()

    for question in questions:
        assert rewriter.rewrite(question) == rule_based_rewrite(question)
    assert len(llm.calls) == len(questions)
