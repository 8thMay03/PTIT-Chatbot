"""Load test thủ công cho BE-11: nhiều ``/api/chat/stream`` đồng thời với LLM chậm.

Chạy backend thật (uvicorn, cùng ``DATABASE_URL`` và pool ``DB_POOL_SIZE`` /
``DB_MAX_OVERFLOW`` / ``DB_POOL_TIMEOUT`` của ``.env``) ngay trong tiến trình này,
với retrieval và LLM được thay bằng bản giả: LLM phát một delta rồi ngủ ``--delay``
giây trước khi phát phần còn lại. Không cần cờ nào trong code production.

Trong lúc các stream chạy, script gọi ``GET /api/health`` mỗi giây. Đạt khi:

- mọi stream trả 200 và kết thúc bằng event ``done``;
- không có lỗi ``QueuePool limit``/timeout nào được log;
- mọi lần gọi ``/api/health`` đều trả 200 và nhanh hơn ``--health-timeout``;
- mọi hội thoại được tạo có đủ cặp tin nhắn user + assistant.

Hội thoại do script tạo được xóa khỏi DB khi kết thúc (trừ khi ``--keep``).

Chỉ chạy với DB dev: script ghi (rồi xóa) hội thoại thật vào DB mà ``.env`` trỏ tới.

Ví dụ (PostgreSQL docker compose dev, pool mặc định 10 + 20)::

    python -m scripts.load_chat_stream --streams 50 --delay 20
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import httpx
import uvicorn
from sqlalchemy import select

from app.api import routes
from app.core.config import settings
from app.db.models import Message
from app.db.repositories import delete_conversation
from app.db.session import SessionLocal, engine
from app.llm import CONTENT_DELTA, StreamDelta
from app.main import app

FAKE_RETRIEVAL = {
    "contexts": [
        {
            "source_name": "load-test.md",
            "heading": "Học phí",
            "section_path": "Học phí",
            "text": "Nội dung giả lập cho load test.",
        }
    ],
    "retrieval_debug": {"rewritten_query": "load test", "strong_context": True},
    "strong_context": True,
    "guardrail_allowed": True,
}


class _PoolErrorCollector(logging.Handler):
    """Gom log lỗi có dấu hiệu cạn pool (QueuePool limit, TimeoutError)."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if record.exc_info:
            message += " " + logging.Formatter().formatException(record.exc_info)
        if "QueuePool limit" in message or "TimeoutError" in message:
            self.records.append(message.splitlines()[0])


@dataclass
class StreamResult:
    index: int
    status_code: int | None = None
    conversation_id: str | None = None
    final_event: str | None = None
    error: str | None = None
    first_event_s: float | None = None
    elapsed_s: float = 0.0


@dataclass
class HealthProbe:
    latencies_s: list[float] = field(default_factory=list)
    # (giây kể từ lúc bắt đầu probe, độ trễ) để thấy lúc nào /api/health chậm.
    timeline: list[tuple[float, float]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def _install_fakes(delay_s: float) -> None:
    def fake_iter_retrieve(message, top_k, history=None, budget=None):
        yield {"step": "retrieve", "detail": {}, "elapsed_ms": 1}
        yield {"result": dict(FAKE_RETRIEVAL)}

    def slow_stream(question, contexts, history=None, provider=None, budget=None) -> Iterator[StreamDelta]:
        yield StreamDelta(kind=CONTENT_DELTA, text="Câu trả lời ")
        time.sleep(delay_s)
        yield StreamDelta(kind=CONTENT_DELTA, text="giả lập [1]")

    routes.rag_chain.iter_retrieve_context = fake_iter_retrieve
    routes.stream_answer_deltas_with_llm = slow_stream


def _start_server(port: int) -> tuple[uvicorn.Server, threading.Thread]:
    # lifespan="off": không nạp cấu hình/embedding đã lưu — retrieval đã được thay bằng bản giả.
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn không khởi động được trong 15s")
        time.sleep(0.05)
    return server, thread


async def _run_stream(client: httpx.AsyncClient, index: int) -> StreamResult:
    result = StreamResult(index=index)
    started = time.perf_counter()
    try:
        # Không gửi cookie: mỗi stream được cấp phiên ẩn danh mới như một trình duyệt riêng.
        client.cookies.clear()
        async with client.stream("POST", "/api/chat/stream", json={"message": f"Câu hỏi load test {index}?"}) as response:
            result.status_code = response.status_code
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if result.first_event_s is None:
                    result.first_event_s = time.perf_counter() - started
                if event["type"] == "start":
                    result.conversation_id = event["conversation_id"]
                elif event["type"] in {"done", "error"}:
                    result.final_event = event["type"]
                    if event["type"] == "error":
                        result.error = event.get("message")
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
    result.elapsed_s = time.perf_counter() - started
    return result


async def _probe_health(base_url: str, stop: asyncio.Event, probe: HealthProbe, timeout_s: float) -> None:
    probe_started = time.perf_counter()
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout_s) as client:
        while not stop.is_set():
            started = time.perf_counter()
            try:
                response = await client.get("/api/health")
                elapsed = time.perf_counter() - started
                probe.latencies_s.append(elapsed)
                probe.timeline.append((started - probe_started, elapsed))
                if response.status_code != 200:
                    probe.failures.append(f"HTTP {response.status_code}")
            except Exception as exc:
                probe.failures.append(f"{type(exc).__name__}: {exc}")
            try:
                await asyncio.wait_for(stop.wait(), timeout=1)
            except asyncio.TimeoutError:
                pass


async def _run_load(base_url: str, streams: int, delay_s: float, health_timeout_s: float):
    probe = HealthProbe()
    stop = asyncio.Event()
    health_task = asyncio.create_task(_probe_health(base_url, stop, probe, health_timeout_s))
    started = time.perf_counter()
    # Một client dùng chung: tạo mỗi stream một AsyncClient (mỗi cái dựng SSL context
    # ~0.1s) chặn event loop của script vài giây và làm sai số đo /api/health.
    limits = httpx.Limits(max_connections=streams + 5, max_keepalive_connections=streams + 5)
    async with httpx.AsyncClient(base_url=base_url, timeout=delay_s + 60, limits=limits) as client:
        results = await asyncio.gather(*(_run_stream(client, i) for i in range(streams)))
    stop.set()
    await health_task
    return results, probe, time.perf_counter() - started


def _check_pairs(conversation_ids: list[str]) -> list[str]:
    problems = []
    with SessionLocal() as session:
        for conversation_id in conversation_ids:
            roles = list(
                session.scalars(
                    select(Message.role)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                )
            )
            if roles != ["user", "assistant"]:
                problems.append(f"{conversation_id}: {roles}")
    return problems


def _cleanup(conversation_ids: list[str]) -> None:
    with SessionLocal() as session:
        for conversation_id in conversation_ids:
            delete_conversation(session, conversation_id)
        session.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Chỉ chạy với DB dev: script ghi (rồi xóa) hội thoại thật vào DB mà .env trỏ tới.",
    )
    parser.add_argument("--streams", type=int, default=50, help="Số stream đồng thời (mặc định 50).")
    parser.add_argument("--delay", type=float, default=20.0, help="LLM giả ngủ bao nhiêu giây giữa hai delta.")
    parser.add_argument("--port", type=int, default=8899, help="Cổng uvicorn tạm (mặc định 8899).")
    parser.add_argument("--health-timeout", type=float, default=5.0, help="Ngưỡng thời gian cho mỗi /api/health.")
    parser.add_argument("--keep", action="store_true", help="Giữ lại hội thoại đã tạo trong DB.")
    args = parser.parse_args(argv)

    collector = _PoolErrorCollector()
    logging.getLogger().addHandler(collector)

    pool = engine.pool
    # In DB đích (không kèm mật khẩu) để người chạy thấy rõ đang ghi vào đâu.
    print(f"DB đích: {engine.url.render_as_string(hide_password=True)}")
    print(
        f"DB dialect={engine.dialect.name} pool={type(pool).__name__} "
        f"size={settings.db_pool_size} max_overflow={settings.db_max_overflow} timeout={settings.db_pool_timeout}s"
    )
    print(f"Chạy {args.streams} stream đồng thời, LLM giả chậm {args.delay}s ...")

    _install_fakes(args.delay)
    server, thread = _start_server(args.port)
    try:
        results, probe, total_s = asyncio.run(
            _run_load(f"http://127.0.0.1:{args.port}", args.streams, args.delay, args.health_timeout)
        )
    finally:
        server.should_exit = True
        thread.join(timeout=15)

    conversation_ids = [r.conversation_id for r in results if r.conversation_id]
    bad_streams = [r for r in results if r.status_code != 200 or r.final_event != "done" or r.error]
    pair_problems = _check_pairs(conversation_ids)
    slow_health = [latency for latency in probe.latencies_s if latency >= args.health_timeout]

    elapsed = sorted(r.elapsed_s for r in results)
    print(f"Tổng thời gian: {total_s:.1f}s; stream nhanh nhất {elapsed[0]:.1f}s, chậm nhất {elapsed[-1]:.1f}s")
    first_events = sorted(r.first_event_s for r in results if r.first_event_s is not None)
    if first_events:
        print(f"Thời gian tới event đầu: nhanh nhất {first_events[0]:.2f}s, chậm nhất {first_events[-1]:.2f}s")
    print(f"Stream lỗi: {len(bad_streams)}/{len(results)}")
    for result in bad_streams[:10]:
        print(f"  #{result.index}: status={result.status_code} final={result.final_event} error={result.error}")
    if probe.latencies_s:
        print(
            f"/api/health: {len(probe.latencies_s)} lần, lỗi {len(probe.failures)}, "
            f"max {max(probe.latencies_s) * 1000:.0f}ms, trung bình "
            f"{sum(probe.latencies_s) / len(probe.latencies_s) * 1000:.0f}ms"
        )
    else:
        print("/api/health: không có lần gọi nào thành công")
    print("  độ trễ theo thời gian:", ", ".join(f"t={t:.0f}s:{lat * 1000:.0f}ms" for t, lat in probe.timeline))
    for failure in probe.failures[:10]:
        print(f"  health lỗi: {failure}")
    print(f"Log cạn pool (QueuePool/TimeoutError): {len(collector.records)}")
    for record in collector.records[:10]:
        print(f"  {record}")
    print(f"Hội thoại thiếu cặp user + assistant: {len(pair_problems)}/{len(conversation_ids)}")
    for problem in pair_problems[:10]:
        print(f"  {problem}")

    if args.keep:
        print(f"Giữ lại {len(conversation_ids)} hội thoại trong DB.")
    else:
        _cleanup(conversation_ids)
        print(f"Đã xóa {len(conversation_ids)} hội thoại do load test tạo.")

    passed = (
        not bad_streams
        and not collector.records
        and not probe.failures
        and not slow_health
        and bool(probe.latencies_s)
        and not pair_problems
        and len(conversation_ids) == args.streams
    )
    print("KẾT QUẢ:", "PASSED" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
