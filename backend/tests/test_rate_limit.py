"""Unit test cho limiter của chat (BE-10): token bucket nhiều cửa sổ và khóa lượt chat."""

from __future__ import annotations

import threading

from app.core.rate_limit import ActiveSlotRegistry, TokenBucketLimiter


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _limiter(windows, clock, max_keys=1000) -> TokenBucketLimiter:
    return TokenBucketLimiter(lambda: windows, max_keys=lambda: max_keys, clock=clock)


# ==========================================
# TokenBucketLimiter
# ==========================================
def test_owner_minute_bucket_blocks_with_retry_after_and_refills() -> None:
    clock = FakeClock()
    limiter = _limiter(((3, 60.0),), clock)

    assert [limiter.check_and_consume("a").allowed for _ in range(3)] == [True, True, True]
    blocked = limiter.check_and_consume("a")
    assert not blocked.allowed
    # Một token nạp lại sau 60 / 3 = 20 giây.
    assert blocked.retry_after == 20

    clock.advance(19)
    assert not limiter.check_and_consume("a").allowed
    clock.advance(1)
    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed


def test_retry_after_is_rounded_up_to_whole_seconds() -> None:
    clock = FakeClock()
    limiter = _limiter(((3, 60.0),), clock)
    for _ in range(3):
        limiter.check_and_consume("a")
    clock.advance(0.5)

    decision = limiter.check_and_consume("a")

    assert (decision.allowed, decision.retry_after) == (False, 20)


def test_owner_day_bucket_blocks_after_minute_bucket_refills() -> None:
    clock = FakeClock()
    limiter = _limiter(((2, 60.0), (3, 86400.0)), clock)

    assert limiter.check_and_consume("a").allowed
    assert limiter.check_and_consume("a").allowed
    clock.advance(60)
    assert limiter.check_and_consume("a").allowed
    clock.advance(60)
    # Phút còn đủ token nhưng ngày đã hết: chờ theo bucket ngày (86400 / 3 trừ phần đã nạp).
    decision = limiter.check_and_consume("a")
    assert not decision.allowed
    assert abs(decision.retry_after - (86400 // 3 - 120)) <= 1

    clock.advance(decision.retry_after)
    assert limiter.check_and_consume("a").allowed


def test_blocked_request_does_not_drain_other_buckets() -> None:
    clock = FakeClock()
    limiter = _limiter(((1, 60.0), (5, 86400.0)), clock)

    assert limiter.check_and_consume("a").allowed
    # Bị chặn theo phút nhiều lần: bucket ngày không bị trừ.
    for _ in range(10):
        assert not limiter.check_and_consume("a").allowed
    for _ in range(4):
        clock.advance(60)
        assert limiter.check_and_consume("a").allowed
    clock.advance(60)
    assert not limiter.check_and_consume("a").allowed


def test_keys_are_independent() -> None:
    limiter = _limiter(((1, 60.0),), FakeClock())

    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed
    assert limiter.check_and_consume("b").allowed


def test_non_positive_limit_disables_only_that_window() -> None:
    clock = FakeClock()
    limiter = _limiter(((0, 60.0), (2, 86400.0)), clock)

    assert limiter.check_and_consume("a").allowed
    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed

    unlimited = _limiter(((0, 60.0), (-1, 86400.0)), clock)
    assert all(unlimited.check_and_consume("a").allowed for _ in range(100))
    assert unlimited.tracked_keys() == 0


def test_limit_change_takes_effect_immediately() -> None:
    windows = [(1, 60.0)]
    limiter = TokenBucketLimiter(lambda: windows, max_keys=lambda: 100, clock=FakeClock())

    assert limiter.check_and_consume("a").allowed
    assert not limiter.check_and_consume("a").allowed
    windows[0] = (5, 60.0)
    assert limiter.check_and_consume("a").allowed


def test_tracked_keys_are_bounded_and_least_recent_evicted() -> None:
    limiter = _limiter(((1, 60.0),), FakeClock(), max_keys=3)

    for key in ("a", "b", "c"):
        assert limiter.check_and_consume(key).allowed
    # Dùng lại "a" để nó thành khóa mới nhất; thêm "d" bỏ "b" (ít dùng nhất).
    assert not limiter.check_and_consume("a").allowed
    assert limiter.check_and_consume("d").allowed

    assert limiter.tracked_keys() == 3
    assert not limiter.check_and_consume("a").allowed
    assert limiter.check_and_consume("b").allowed  # "b" đã bị bỏ: bắt đầu lại với bucket đầy


def test_full_buckets_are_pruned_periodically() -> None:
    clock = FakeClock()
    limiter = _limiter(((2, 60.0),), clock)
    for key in ("a", "b", "c"):
        limiter.check_and_consume(key)
    assert limiter.tracked_keys() == 3

    clock.advance(120)
    limiter.check_and_consume("d")

    assert limiter.tracked_keys() == 1


def test_concurrent_consumers_never_exceed_limit() -> None:
    limiter = _limiter(((50, 60.0),), FakeClock())
    allowed: list[bool] = []
    lock = threading.Lock()
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        for _ in range(25):
            result = limiter.check_and_consume("shared").allowed
            with lock:
                allowed.append(result)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(allowed) == 200
    assert sum(allowed) == 50


def test_reset_clears_counters() -> None:
    limiter = _limiter(((1, 60.0),), FakeClock())
    limiter.check_and_consume("a")

    limiter.reset()

    assert limiter.check_and_consume("a").allowed


# ==========================================
# ActiveSlotRegistry
# ==========================================
def test_slot_is_exclusive_per_key_until_released() -> None:
    registry = ActiveSlotRegistry(lambda: 600.0, clock=FakeClock())

    slot = registry.acquire("owner")
    assert slot is not None
    assert registry.acquire("owner") is None
    assert registry.acquire("other") is not None

    slot.release()
    assert not registry.is_active("owner")
    assert registry.acquire("owner") is not None


def test_slot_release_is_idempotent() -> None:
    registry = ActiveSlotRegistry(lambda: 600.0, clock=FakeClock())
    slot = registry.acquire("owner")

    slot.release()
    slot.release()
    replacement = registry.acquire("owner")
    slot.release()

    assert replacement is not None
    assert registry.is_active("owner")


def test_slot_expires_after_ttl() -> None:
    clock = FakeClock()
    registry = ActiveSlotRegistry(lambda: 600.0, clock=clock)
    assert registry.acquire("owner") is not None

    clock.advance(599)
    assert registry.acquire("owner") is None
    clock.advance(1)
    assert registry.acquire("owner") is not None


def test_expired_slot_does_not_release_its_replacement() -> None:
    clock = FakeClock()
    registry = ActiveSlotRegistry(lambda: 10.0, clock=clock)
    stale = registry.acquire("owner")
    clock.advance(10)
    fresh = registry.acquire("owner")
    assert fresh is not None

    stale.release()

    assert registry.is_active("owner")
    assert registry.acquire("owner") is None
    fresh.release()
    assert not registry.is_active("owner")


def test_concurrent_acquire_grants_one_slot() -> None:
    registry = ActiveSlotRegistry(lambda: 600.0)
    granted: list[object] = []
    lock = threading.Lock()
    barrier = threading.Barrier(16)

    def worker() -> None:
        barrier.wait()
        slot = registry.acquire("owner")
        if slot is not None:
            with lock:
                granted.append(slot)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(granted) == 1


def test_reset_clears_slots() -> None:
    registry = ActiveSlotRegistry(lambda: 600.0, clock=FakeClock())
    registry.acquire("owner")

    registry.reset()

    assert registry.acquire("owner") is not None
