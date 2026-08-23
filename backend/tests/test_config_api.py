from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app

client = TestClient(app)


def test_get_config_returns_full_structure() -> None:
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()

    assert "llm" in data
    assert "retrieval" in data
    assert "reranker" in data
    assert "guardrails" in data
    assert "available_providers" in data

    assert data["llm"]["provider"] == settings.llm_provider
    assert "openai" in data["available_providers"]["llm"]
    assert "gemini" in data["available_providers"]["llm"]
    assert "heuristic" in data["available_providers"]["reranker"]
    assert "cross-encoder" in data["available_providers"]["reranker"]


def test_update_config_llm_and_toggles() -> None:
    payload = {
        "llm": {
            "provider": "gemini",
            "gemini_model": "gemini-1.5-pro",
            "temperature": 0.35,
        },
        "retrieval": {
            "multi_query_enabled": False,
            "top_k": 6,
            "hybrid_vector_weight": 0.8,
        },
        "reranker": {
            "enabled": False,
            "provider": "cross-encoder",
            "candidate_multiplier": 5,
        },
        "guardrails": {
            "scope_enabled": False,
            "min_vector_score": 0.25,
        },
    }

    response = client.put("/api/config", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["llm"]["provider"] == "gemini"
    assert data["llm"]["gemini_model"] == "gemini-1.5-pro"
    assert data["llm"]["temperature"] == 0.35
    assert data["retrieval"]["multi_query_enabled"] is False
    assert data["retrieval"]["top_k"] == 6
    assert data["retrieval"]["hybrid_vector_weight"] == 0.8
    assert data["reranker"]["enabled"] is False
    assert data["reranker"]["provider"] == "cross-encoder"
    assert data["guardrails"]["scope_enabled"] is False
    assert data["guardrails"]["min_vector_score"] == 0.25

    # Verify global settings updated
    assert settings.llm_provider == "gemini"
    assert settings.multi_query_enabled is False
    assert settings.reranker_enabled is False
    assert settings.guardrail_scope_enabled is False


def test_reset_config_restores_defaults() -> None:
    expected_default_temp = Settings().llm_temperature

    # Change something
    client.put("/api/config", json={"llm": {"temperature": 1.75}, "retrieval": {"top_k": 9}})
    assert settings.llm_temperature == 1.75
    assert settings.retrieval_default_top_k == 9

    # Reset
    response = client.post("/api/config/reset")
    assert response.status_code == 200
    data = response.json()

    assert data["llm"]["temperature"] == expected_default_temp
    assert settings.llm_temperature == expected_default_temp
    assert settings.retrieval_default_top_k == Settings().retrieval_default_top_k


def test_test_llm_endpoint_success() -> None:
    with patch("app.llm.providers.openai_provider.OpenAIProvider.generate", return_value="OK PTIT"):
        with patch("app.llm.providers.openai_provider.OpenAIProvider.is_configured", return_value=True):
            payload = {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "api_key": "sk-testkey1234567890",
            }
            response = client.post("/api/config/test-llm", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "OK PTIT" in data["sample_output"]
            assert data["latency_ms"] is not None


def test_test_llm_endpoint_unconfigured() -> None:
    payload = {
        "provider": "gemini",
        "api_key": "",
    }
    with patch("app.core.config.settings.gemini_api_key", None):
        response = client.post("/api/config/test-llm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "chưa được cấu hình" in data["message"]
