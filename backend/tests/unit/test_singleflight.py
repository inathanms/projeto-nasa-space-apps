import asyncio

import pytest

from app.cache.singleflight import SingleFlight


async def test_single_call_returns_factory_result():
    sf = SingleFlight()

    async def factory():
        return 42

    assert await sf.do("k", factory) == 42


async def test_concurrent_calls_run_factory_once_and_share_result():
    sf = SingleFlight()
    calls = 0
    gate = asyncio.Event()

    async def factory():
        nonlocal calls
        calls += 1
        await gate.wait()
        return {"value": calls}

    tasks = [asyncio.create_task(sf.do("k", factory)) for _ in range(10)]
    await asyncio.sleep(0)  # let every caller register
    gate.set()
    results = await asyncio.gather(*tasks)

    assert calls == 1
    assert len(results) == 10
    assert all(r is results[0] for r in results)


async def test_different_keys_do_not_share_work():
    sf = SingleFlight()
    calls: list[str] = []

    async def make(name: str):
        calls.append(name)
        await asyncio.sleep(0)
        return name

    a, b = await asyncio.gather(
        sf.do("a", lambda: make("a")),
        sf.do("b", lambda: make("b")),
    )

    assert (a, b) == ("a", "b")
    assert sorted(calls) == ["a", "b"]


async def test_error_propagates_to_all_waiters():
    sf = SingleFlight()
    calls = 0
    gate = asyncio.Event()

    async def factory():
        nonlocal calls
        calls += 1
        await gate.wait()
        raise RuntimeError("boom")

    tasks = [asyncio.create_task(sf.do("k", factory)) for _ in range(10)]
    await asyncio.sleep(0)
    gate.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert calls == 1
    assert all(isinstance(r, RuntimeError) and str(r) == "boom" for r in results)


async def test_key_is_released_after_error_so_next_call_retries():
    sf = SingleFlight()
    attempts = 0

    async def factory():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError("first fails")
        return "ok"

    with pytest.raises(ValueError):
        await sf.do("k", factory)

    assert await sf.do("k", factory) == "ok"
    assert attempts == 2


async def test_key_is_released_after_success_so_next_call_reruns():
    sf = SingleFlight()
    attempts = 0

    async def factory():
        nonlocal attempts
        attempts += 1
        return attempts

    assert await sf.do("k", factory) == 1
    assert await sf.do("k", factory) == 2


async def test_cancelling_first_caller_does_not_cancel_work():
    sf = SingleFlight()
    started = asyncio.Event()
    finished = asyncio.Event()
    calls = 0

    async def factory():
        nonlocal calls
        calls += 1
        started.set()
        await asyncio.sleep(0.05)
        finished.set()
        return "result"

    first = asyncio.create_task(sf.do("k", factory))
    await started.wait()
    second = asyncio.create_task(sf.do("k", factory))
    await asyncio.sleep(0)

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first

    assert await second == "result"
    assert finished.is_set()
    assert calls == 1


async def test_cancelling_all_callers_still_completes_work_in_background():
    sf = SingleFlight()
    finished = asyncio.Event()

    async def factory():
        await asyncio.sleep(0.02)
        finished.set()
        return "x"

    task = asyncio.create_task(sf.do("k", factory))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await asyncio.wait_for(finished.wait(), timeout=1)


async def test_key_is_released_after_cancellation_completes():
    sf = SingleFlight()

    async def slow():
        await asyncio.sleep(0.02)
        return "slow"

    task = asyncio.create_task(sf.do("k", slow))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.05)

    async def fresh():
        return "fresh"

    assert await sf.do("k", fresh) == "fresh"
