from app.cache.lru import TTLCacheL1


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_get_returns_none_for_missing_key():
    cache = TTLCacheL1(max_items=4, default_ttl=60, clock=FakeClock())
    assert cache.get("missing") is None


def test_set_then_get_returns_value():
    cache = TTLCacheL1(max_items=4, default_ttl=60, clock=FakeClock())
    cache.set("a", {"x": 1})
    assert cache.get("a") == {"x": 1}


def test_value_expires_after_default_ttl():
    clock = FakeClock()
    cache = TTLCacheL1(max_items=4, default_ttl=60, clock=clock)
    cache.set("a", "va")

    clock.advance(59.9)
    assert cache.get("a") == "va"

    clock.advance(0.2)
    assert cache.get("a") is None


def test_expired_entry_is_removed_from_cache():
    clock = FakeClock()
    cache = TTLCacheL1(max_items=4, default_ttl=10, clock=clock)
    cache.set("a", "va")
    clock.advance(11)

    assert cache.get("a") is None
    assert len(cache) == 0


def test_per_item_ttl_overrides_default():
    clock = FakeClock()
    cache = TTLCacheL1(max_items=4, default_ttl=60, clock=clock)
    cache.set("short", "s", ttl=5)
    cache.set("long", "l")

    clock.advance(6)
    assert cache.get("short") is None
    assert cache.get("long") == "l"


def test_lru_evicts_least_recently_used_when_full():
    cache = TTLCacheL1(max_items=2, default_ttl=60, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # evicts "a"

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_get_refreshes_recency():
    cache = TTLCacheL1(max_items=2, default_ttl=60, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1  # "a" becomes most recent
    cache.set("c", 3)  # evicts "b", not "a"

    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3


def test_set_existing_key_updates_value_and_does_not_evict():
    cache = TTLCacheL1(max_items=2, default_ttl=60, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)

    assert len(cache) == 2
    assert cache.get("a") == 10
    assert cache.get("b") == 2


def test_set_existing_key_resets_its_ttl():
    clock = FakeClock()
    cache = TTLCacheL1(max_items=4, default_ttl=10, clock=clock)
    cache.set("a", 1)
    clock.advance(8)
    cache.set("a", 2)
    clock.advance(8)

    assert cache.get("a") == 2


def test_max_items_is_respected_with_expired_entries_first():
    clock = FakeClock()
    cache = TTLCacheL1(max_items=2, default_ttl=10, clock=clock)
    cache.set("old", 1)
    clock.advance(11)
    cache.set("x", 2)
    cache.set("y", 3)

    assert len(cache) == 2
    assert cache.get("x") == 2
    assert cache.get("y") == 3
