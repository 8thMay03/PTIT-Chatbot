from app.db.repositories import limit_history


def test_limit_history_keeps_newest_messages_within_both_limits() -> None:
    messages = [
        {"role": "user", "content": "old question"},
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "new answer"},
    ]

    history = limit_history(messages, max_messages=3, max_chars=22)

    assert history == [
        {"role": "user", "content": "new question"},
        {"role": "assistant", "content": "new answer"},
    ]


def test_limit_history_can_be_disabled_with_zero_budget() -> None:
    assert limit_history([{"role": "user", "content": "question"}], 0, 100) == []
