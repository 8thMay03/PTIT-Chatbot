"""Test allowlist base_url/endpoint LLM (FE-06, AC-02).

PUT /api/config và POST /api/config/test-llm không được phép trỏ URL LLM sang
host ngoài allowlist — kể cả khi là admin: request trả 422 và KHÔNG setting nào
được đổi (kiểm toàn payload trước khi ghi).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api import routes
from app.core import config as config_module
from app.core.config import ConfigValidationError, settings, validate_llm_url


ALLOWLIST = "https://api.openai.com,https://*.openai.azure.com,http://localhost:11434"


@pytest.fixture
def llm_allowlist(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url_allowlist", ALLOWLIST)


@pytest.fixture
def llm_provider_recorder(monkeypatch):
    calls = []

    def record(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(is_configured=lambda: False, generate=lambda *a, **kw: "")

    monkeypatch.setattr(routes, "create_llm_provider_from_config", record)
    return calls


# ==========================================
# Unit: validate_llm_url
# ==========================================
@pytest.mark.parametrize(
    ("value", "allowed"),
    [
        ("https://api.openai.com/v1", True),
        ("https://api.openai.com", True),
        ("", True),  # rỗng: về mặc định SDK
        (None, True),
        ("https://foo.openai.azure.com/", True),
        ("https://foo.bar.openai.azure.com/v1", True),  # wildcard khớp mọi độ sâu
        ("http://localhost:11434/v1", True),
        ("https://api.openai.com:443/v1", True),  # cổng mặc định được chuẩn hoá
        ("https://evil.example.com/v1", False),
        ("https://api.openai.com.evil.com/v1", False),  # đuôi host giả mạo
        ("https://evilopenai.azure.com/v1", False),  # thiếu dấu chấm trước wildcard
        ("https://api.openai.com:8443/v1", False),  # origin khác cổng không khớp
        ("http://localhost:8000/v1", False),
        ("ftp://api.openai.com", False),  # scheme lạ
        ("https://user:pass@api.openai.com/v1", False),  # userinfo
        ("https://api.openai.com/@evil", True),  # @ trong path, không phải userinfo
    ],
)
def test_validate_llm_url_matrix(value, allowed, llm_allowlist) -> None:
    if allowed:
        validate_llm_url(value)  # không raise
    else:
        with pytest.raises(ConfigValidationError):
            validate_llm_url(value)


def test_out_of_allowlist_message_contains_origin(llm_allowlist) -> None:
    with pytest.raises(ConfigValidationError) as excinfo:
        validate_llm_url("https://evil.example.com/v1")
    assert "Host 'https://evil.example.com' không nằm trong LLM_BASE_URL_ALLOWLIST" in str(
        excinfo.value
    )


def test_default_allowlist_comes_from_startup_env(monkeypatch) -> None:
    """Allowlist rỗng suy ra từ env lúc khởi động (không phải settings runtime)."""
    monkeypatch.setattr(settings, "llm_base_url_allowlist", "")
    monkeypatch.setattr(
        config_module,
        "_INITIAL_SETTINGS",
        {
            "openai_base_url": "https://startup.openai.example/v1",
            "openai_compatible_base_url": "http://127.0.0.1:9000/v1",
            "azure_openai_endpoint": None,
        },
    )

    entries = config_module.llm_url_allowlist()

    assert entries == [
        "https://api.openai.com",
        "https://startup.openai.example",
        "http://127.0.0.1:9000",
    ]
    validate_llm_url("https://startup.openai.example/v1")  # hợp lệ
    with pytest.raises(ConfigValidationError):
        validate_llm_url("https://runtime-mutated.example/v1")


# ==========================================
# PUT /api/config
# ==========================================
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("openai_base_url", "https://evil.example.com/v1"),
        ("openai_compatible_base_url", "https://evil.example.com/v1"),
        ("azure_openai_endpoint", "https://not-allowed.openai.azure.com.evil.io/"),
        ("base_url", "https://evil.example.com/v1"),
    ],
)
def test_put_config_blocks_url_outside_allowlist(
    field, value, admin_client, llm_allowlist, monkeypatch
) -> None:
    # Trạng thái ban đầu đã set qua monkeypatch để chắc chắn 422 không ghi đè.
    monkeypatch.setattr(settings, "openai_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(settings, "openai_compatible_base_url", "http://localhost:11434/v1")
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://ok.openai.azure.com/")

    response = admin_client.put(
        "/api/config",
        json={"llm": {field: value, "temperature": 0.9}},
    )

    assert response.status_code == 422, response.text
    assert "không nằm trong LLM_BASE_URL_ALLOWLIST" in response.json()["detail"]
    # Cấu hình không đổi: kể cả trường khác trong cùng payload cũng chưa được ghi.
    assert settings.openai_base_url == "https://api.openai.com/v1"
    assert settings.openai_compatible_base_url == "http://localhost:11434/v1"
    assert settings.azure_openai_endpoint == "https://ok.openai.azure.com/"
    assert settings.llm_temperature != 0.9


def test_put_config_blocks_generic_base_url_even_for_unrelated_provider(
    admin_client, llm_allowlist
) -> None:
    """Trường base_url bị kiểm kể cả khi provider hiện tại không dùng nó."""
    response = admin_client.put(
        "/api/config",
        json={"llm": {"provider": "gemini", "base_url": "https://evil.example.com/v1"}},
    )
    assert response.status_code == 422


def test_put_config_blocks_bad_scheme_and_userinfo(admin_client, llm_allowlist) -> None:
    response = admin_client.put(
        "/api/config", json={"llm": {"openai_base_url": "ftp://api.openai.com"}}
    )
    assert response.status_code == 422
    assert "http hoặc https" in response.json()["detail"]

    response = admin_client.put(
        "/api/config",
        json={"llm": {"openai_base_url": "https://key:secret@api.openai.com/v1"}},
    )
    assert response.status_code == 422
    assert "thông tin đăng nhập" in response.json()["detail"]


@pytest.mark.parametrize(
    ("field", "value", "expected_attr"),
    [
        ("openai_base_url", "https://foo.openai.azure.com/v1", "openai_base_url"),
        ("openai_compatible_base_url", "http://localhost:11434/v1", "openai_compatible_base_url"),
        ("base_url", "https://api.openai.com/v1", "openai_base_url"),
        ("azure_openai_endpoint", "https://foo.openai.azure.com/", "azure_openai_endpoint"),
    ],
)
def test_put_config_accepts_allowlisted_url(
    field, value, expected_attr, admin_client, llm_allowlist, monkeypatch
) -> None:
    # Ghim provider để trường base_url tổng quát map về openai_base_url.
    monkeypatch.setattr(settings, "llm_provider", "openai")
    response = admin_client.put("/api/config", json={"llm": {field: value}})
    assert response.status_code == 200, response.text
    assert getattr(settings, expected_attr) == value


def test_put_config_allows_empty_base_url(admin_client, llm_allowlist) -> None:
    """Giá trị rỗng cho openai_base_url được phép (về mặc định SDK)."""
    response = admin_client.put("/api/config", json={"llm": {"openai_base_url": ""}})
    assert response.status_code == 200, response.text
    assert settings.openai_base_url is None


# ==========================================
# POST /api/config/test-llm
# ==========================================
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("base_url", "https://evil.example.com/v1"),
        ("endpoint", "https://not-allowed.openai.azure.com.evil.io/"),
    ],
)
def test_test_llm_blocks_url_outside_allowlist(
    field, value, admin_client, llm_allowlist, llm_provider_recorder
) -> None:
    response = admin_client.post(
        "/api/config/test-llm",
        json={"provider": "openai", "api_key": "sk-test", field: value},
    )

    assert response.status_code == 422, response.text
    assert "không nằm trong LLM_BASE_URL_ALLOWLIST" in response.json()["detail"]
    # Provider không được tạo: key đang lưu không bao giờ gửi tới host lạ.
    assert llm_provider_recorder == []


def test_test_llm_accepts_allowlisted_url(
    admin_client, llm_allowlist, llm_provider_recorder
) -> None:
    response = admin_client.post(
        "/api/config/test-llm",
        json={
            "provider": "openai_compatible",
            "base_url": "http://localhost:11434/v1",
        },
    )

    assert response.status_code == 200, response.text
    assert len(llm_provider_recorder) == 1
    assert llm_provider_recorder[0]["base_url"] == "http://localhost:11434/v1"
