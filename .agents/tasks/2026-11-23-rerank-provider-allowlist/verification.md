# Kiểm chứng: rerank-provider-allowlist

| ID | AC | Lệnh | Kết quả | Trạng thái |
| --- | --- | --- | --- | --- |
| V-01 | AC-01, AC-02 | `backend/.venv/Scripts/python -m pytest tests/test_llm_url_allowlist.py` (trong lần chạy toàn bộ) | đạt | `passed` |
| V-02 | AC-03 | `backend/.venv/Scripts/python -m pytest -q` (Postgres Docker đang chạy) | 1542 passed, 24 skipped | `passed` |
| V-03 | AC-03 | `npx vitest run` trong `frontend/` | 397 passed | `passed` |

Ghi chú: chạy riêng nhóm `test_llm_url_allowlist.py test_reranker.py test_model_profiles.py test_config_persistence.py`
có 3 test `test_config_persistence.py` lỗi; trên `dev` (`b496054`, không có thay đổi) cùng lệnh cũng lỗi đúng 3 test
đó, nên đây là lỗi phụ thuộc thứ tự có sẵn, không do task này. Chạy riêng file đó: 22 passed.
