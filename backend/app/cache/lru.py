"""Cache L1 em memória: LRU com TTL por item (REQ-542)."""

import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any


class TTLCacheL1:
    """LRU de tamanho limitado em que cada item expira no seu próprio prazo.

    `clock` é injetável para testes; o padrão é `time.monotonic`.
    """

    def __init__(
        self,
        max_items: int,
        default_ttl: float,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if max_items < 1:
            raise ValueError("max_items must be >= 1")
        if default_ttl <= 0:
            raise ValueError("default_ttl must be > 0")
        if clock is None:
            clock = time.monotonic
        self._max_items = max_items
        self._default_ttl = default_ttl
        self._clock = clock
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: Any) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: Any, value: Any, ttl: float | None = None) -> None:
        effective_ttl = self._default_ttl if ttl is None else ttl
        if effective_ttl <= 0:
            raise ValueError("ttl must be > 0")
        self._data[key] = (self._clock() + effective_ttl, value)
        self._data.move_to_end(key)
        self._evict()

    def _evict(self) -> None:
        if len(self._data) <= self._max_items:
            return
        now = self._clock()
        expired = [k for k, (exp, _) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        while len(self._data) > self._max_items:
            self._data.popitem(last=False)
