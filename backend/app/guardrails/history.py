from app.guardrails.security import contains_prompt_injection


def filter_safe_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Remove prior user injection attempts before history reaches an LLM."""

    safe: list[dict[str, str]] = []
    for message in history or []:
        content = str(message.get("content", ""))
        if message.get("role") == "user" and contains_prompt_injection(content):
            continue
        safe.append(message)
    return safe
