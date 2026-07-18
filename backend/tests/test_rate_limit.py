import pytest
import services.rate_limit as rl


@pytest.fixture(autouse=True)
def _clear_state():
    rl._buckets.clear()
    yield


@pytest.mark.asyncio
async def test_bucket_allows_up_to_capacity_then_denies():
    for _ in range(3):
        assert await rl.check("ip:1.2.3.4:analyze", capacity=3, refill_per_sec=0.0) is True
    assert await rl.check("ip:1.2.3.4:analyze", capacity=3, refill_per_sec=0.0) is False


@pytest.mark.asyncio
async def test_bucket_refills_over_time(monkeypatch):
    now = {"t": 0.0}
    monkeypatch.setattr(rl.time, "monotonic", lambda: now["t"])
    key = "ip:5.6.7.8:analyze"

    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is True
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is True
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is False

    now["t"] = 1.0
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is True
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is False


@pytest.mark.asyncio
async def test_buckets_are_isolated_per_key():
    assert await rl.check("a", capacity=1, refill_per_sec=0.0) is True
    assert await rl.check("a", capacity=1, refill_per_sec=0.0) is False
    assert await rl.check("b", capacity=1, refill_per_sec=0.0) is True
