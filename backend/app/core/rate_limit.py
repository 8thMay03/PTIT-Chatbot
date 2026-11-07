"""Hạn mức cho route chat (BE-10): token bucket theo khóa và khóa "một lượt đang chạy".

- ``TokenBucketLimiter``: mỗi khóa có một bucket cho từng cửa sổ (ví dụ phút, ngày).
  Dung lượng bucket = ngưỡng của cửa sổ, nạp lại đều trong cả cửa sổ. Request chỉ
  được trừ token khi mọi bucket còn đủ, nên request bị chặn không làm hao bucket khác.
- ``ActiveSlotRegistry``: mỗi khóa (owner) giữ tối đa một ``ChatSlot``. Slot hết hạn sau
  TTL để owner không bị kẹt khi response không bao giờ chạy tới bước nhả.

Trạng thái nằm trong bộ nhớ process, an toàn khi nhiều thread (route sync và bước stream
chạy trong threadpool). Chỉ đúng khi chạy một worker uvicorn (cấu hình hiện tại); chạy
nhiều worker thì mỗi worker đếm riêng — BE-16 sẽ thay phần lưu trữ, giữ nguyên giao diện.

Ngưỡng đọc qua callable (giống ``auth.FailureLimiter``) để settings đổi lúc chạy và
monkeypatch trong test có hiệu lực ngay.
"""

from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.core.config import settings

MINUTE_SECONDS = 60.0
DAY_SECONDS = 86400.0
# Chu kỳ dọn khóa không còn cần theo dõi (bucket đã đầy lại / slot đã hết hạn).
PRUNE_INTERVAL_SECONDS = 60.0
# Sai số khi so token: nạp lại theo nhiều bước nhỏ có thể thiếu 1e-16 so với 1 token.
_TOKEN_EPSILON = 1e-9

# (ngưỡng, cửa sổ giây); ngưỡng <= 0 = tắt riêng cửa sổ đó.
RateWindow = tuple[int, float]


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    # Số giây (nguyên, >= 1) nên chờ trước khi gửi lại; 0 khi được phép.
    retry_after: int = 0


@dataclass
class _BucketState:
    windows: tuple[RateWindow, ...]
    tokens: list[float]
    updated: float


class TokenBucketLimiter:
    """Token bucket nhiều cửa sổ theo khóa, giới hạn số khóa theo dõi."""

    def __init__(
        self,
        windows: Callable[[], Sequence[RateWindow]],
        *,
        max_keys: Callable[[], int],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._windows = windows
        self._max_keys = max_keys
        self.clock = clock
        self._lock = threading.Lock()
        self._states: OrderedDict[str, _BucketState] = OrderedDict()
        self._last_prune: float | None = None

    def _active_windows(self) -> tuple[RateWindow, ...]:
        return tuple((int(limit), float(window)) for limit, window in self._windows() if limit > 0 and window > 0)

    @staticmethod
    def _refill(state: _BucketState, now: float) -> None:
        elapsed = max(0.0, now - state.updated)
        state.tokens = [
            min(float(limit), tokens + elapsed * limit / window)
            for (limit, window), tokens in zip(state.windows, state.tokens)
        ]
        state.updated = now

    @staticmethod
    def _is_full(state: _BucketState) -> bool:
        return all(tokens >= limit - _TOKEN_EPSILON for (limit, _), tokens in zip(state.windows, state.tokens))

    def _prune(self, now: float) -> None:
        if self._last_prune is not None and now - self._last_prune < PRUNE_INTERVAL_SECONDS:
            return
        self._last_prune = now
        for key in list(self._states):
            state = self._states[key]
            self._refill(state, now)
            if self._is_full(state):
                del self._states[key]

    def check_and_consume(self, key: str) -> RateDecision:
        windows = self._active_windows()
        if not windows:
            return RateDecision(allowed=True)
        with self._lock:
            now = self.clock()
            self._prune(now)
            state = self._states.get(key)
            if state is None or state.windows != windows:
                # Khóa mới hoặc ngưỡng vừa đổi: bắt đầu với bucket đầy.
                state = _BucketState(windows=windows, tokens=[float(limit) for limit, _ in windows], updated=now)
                self._states[key] = state
            else:
                self._refill(state, now)
            self._states.move_to_end(key)

            waits = [
                (1.0 - tokens) * window / limit
                for (limit, window), tokens in zip(windows, state.tokens)
                if tokens < 1.0 - _TOKEN_EPSILON
            ]
            if waits:
                decision = RateDecision(allowed=False, retry_after=max(1, math.ceil(max(waits))))
            else:
                state.tokens = [max(0.0, tokens - 1.0) for tokens in state.tokens]
                decision = RateDecision(allowed=True)

            # Xoay khóa liên tục (ví dụ đổi cookie) không làm phình bộ nhớ: bỏ khóa ít dùng nhất.
            max_keys = max(1, self._max_keys())
            while len(self._states) > max_keys:
                self._states.popitem(last=False)
            return decision

    def tracked_keys(self) -> int:
        with self._lock:
            return len(self._states)

    def reset(self) -> None:
        with self._lock:
            self._states.clear()
            self._last_prune = None


class ChatSlot:
    """Quyền chạy một lượt chat của một owner; ``release()`` gọi nhiều lần vẫn an toàn."""

    def __init__(self, registry: ActiveSlotRegistry, key: str) -> None:
        self._registry = registry
        self.key = key
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._registry._release(self)


class ActiveSlotRegistry:
    """Mỗi khóa tối đa một slot đang giữ; slot quá TTL coi như đã nhả."""

    def __init__(
        self,
        ttl_seconds: Callable[[], float],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self.clock = clock
        self._lock = threading.Lock()
        self._slots: dict[str, tuple[ChatSlot, float]] = {}
        self._last_prune: float | None = None

    def _prune(self, now: float) -> None:
        if self._last_prune is not None and now - self._last_prune < PRUNE_INTERVAL_SECONDS:
            return
        self._last_prune = now
        for key in [key for key, (_, expires_at) in self._slots.items() if expires_at <= now]:
            del self._slots[key]

    def acquire(self, key: str) -> ChatSlot | None:
        """Trả slot mới, hoặc None khi khóa đang giữ một slot chưa hết hạn."""
        with self._lock:
            now = self.clock()
            self._prune(now)
            current = self._slots.get(key)
            if current is not None and current[1] > now:
                return None
            slot = ChatSlot(self, key)
            self._slots[key] = (slot, now + float(self._ttl_seconds()))
            return slot

    def _release(self, slot: ChatSlot) -> None:
        with self._lock:
            current = self._slots.get(slot.key)
            # Chỉ nhả đúng slot của mình: slot cũ đã hết TTL không nhả nhầm slot mới cấp lại.
            if current is not None and current[0] is slot:
                del self._slots[slot.key]

    def is_active(self, key: str) -> bool:
        with self._lock:
            current = self._slots.get(key)
            return current is not None and current[1] > self.clock()

    def reset(self) -> None:
        with self._lock:
            self._slots.clear()
            self._last_prune = None


chat_owner_limiter = TokenBucketLimiter(
    lambda: (
        (settings.chat_rate_owner_per_minute, MINUTE_SECONDS),
        (settings.chat_rate_owner_per_day, DAY_SECONDS),
    ),
    max_keys=lambda: settings.chat_rate_limit_max_keys,
)
# Theo IP: chặn người xoay cookie ptit_sid; ngưỡng cao hơn owner vì nhiều sinh viên có
# thể chung một IP public (wifi trường, NAT).
chat_ip_limiter = TokenBucketLimiter(
    lambda: (
        (settings.chat_rate_ip_per_minute, MINUTE_SECONDS),
        (settings.chat_rate_ip_per_day, DAY_SECONDS),
    ),
    max_keys=lambda: settings.chat_rate_limit_max_keys,
)
chat_active_slots = ActiveSlotRegistry(lambda: settings.chat_active_slot_ttl_seconds)


def reset_chat_limits() -> None:
    """Xoá mọi bộ đếm và slot chat (cách ly test)."""
    chat_owner_limiter.reset()
    chat_ip_limiter.reset()
    chat_active_slots.reset()
