"""Deadline dùng chung cho mọi lời gọi LLM trong một lượt chat (BE-12).

Một lượt chat gọi LLM tới 3 lần nối tiếp (viết lại câu hỏi, sinh đa truy vấn, sinh câu
trả lời). ``LLMBudget`` giữ thời điểm hết hạn theo ``time.monotonic``; mỗi lần thử và
mỗi lần chờ backoff trong ``BaseLLMProvider._execute_with_retry`` bị cắt theo thời gian
còn lại. Budget được truyền tường minh (không dùng ``contextvars``): generator stream
chạy từng bước ``next()`` trong threadpool nên biến context đặt trong generator bị mất
ở bước sau.

Budget con (:meth:`LLMBudget.child`) dành cho bước tùy chọn: hết hạn sớm hơn cha để
dành thời gian cho bước sinh câu trả lời; cờ ``degraded`` đặt trên con lan lên cha.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable


class LLMBudget:
    """Thời gian còn lại cho phần LLM của một lượt chat."""

    def __init__(
        self,
        seconds: float | None,
        *,
        clock: Callable[[], float] = time.monotonic,
        _parent: LLMBudget | None = None,
        _deadline: float | None = None,
    ) -> None:
        self._clock = clock
        self._parent = _parent
        if _deadline is not None:
            self.deadline: float | None = _deadline
        else:
            self.deadline = None if seconds is None else clock() + max(0.0, seconds)
        self._degraded = False

    @classmethod
    def unlimited(cls) -> LLMBudget:
        """Budget không giới hạn cho lời gọi ngoài lượt chat (thử kết nối, script eval)."""
        return cls(None)

    def remaining(self) -> float:
        if self.deadline is None:
            return math.inf
        return max(0.0, self.deadline - self._clock())

    def expired(self) -> bool:
        return self.remaining() <= 0.0

    @property
    def degraded(self) -> bool:
        """True khi một lời gọi LLM trong lượt đã thất bại hết retry vì lỗi tạm thời."""
        return self._degraded or (self._parent is not None and self._parent.degraded)

    @degraded.setter
    def degraded(self, value: bool) -> None:
        self._degraded = value
        if value and self._parent is not None:
            self._parent.degraded = True

    def child(self, max_seconds: float) -> LLMBudget:
        """Budget hết hạn sau ``max_seconds`` nhưng không muộn hơn budget này."""
        deadline = self._clock() + max(0.0, max_seconds)
        if self.deadline is not None:
            deadline = min(deadline, self.deadline)
        return LLMBudget(None, clock=self._clock, _parent=self, _deadline=deadline)

    def optional_step(self, attempt_timeout: float) -> LLMBudget | None:
        """Budget cho bước tùy chọn (rewrite, multi-query), hoặc None nếu nên bỏ qua LLM.

        Bỏ qua khi LLM đã thất bại trong lượt (``degraded``) hoặc thời gian còn lại
        dưới 1/3 ``attempt_timeout``. Không bỏ qua thì bước chỉ được dùng tối đa một
        nửa thời gian còn lại, phần còn lại dành cho bước sinh câu trả lời.
        """
        if self.degraded:
            return None
        remaining = self.remaining()
        if remaining < attempt_timeout / 3:
            return None
        if math.isinf(remaining):
            return self
        return self.child(remaining * OPTIONAL_STEP_SHARE)


# Phần thời gian còn lại mà một bước tùy chọn được dùng.
OPTIONAL_STEP_SHARE = 0.5
