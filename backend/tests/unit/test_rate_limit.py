import pytest

from app.core.rate_limit import MemoryRateLimiter, Rate, parse_rate


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10/minute", Rate(10, 60)),
        ("300/minutes", Rate(300, 60)),
        ("5/second", Rate(5, 1)),
        (" 100 / hour ", Rate(100, 3600)),
        ("1000/day", Rate(1000, 86400)),
    ],
)
def test_parse_rate(value: str, expected: Rate) -> None:
    assert parse_rate(value) == expected


@pytest.mark.parametrize("value", ["", "ten/minute", "10/week", "0/minute", "10"])
def test_parse_rate_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid rate limit"):
        parse_rate(value)


async def test_memory_limiter_blocks_after_limit_per_key() -> None:
    limiter = MemoryRateLimiter()
    rate = Rate(limit=3, period_seconds=3600)

    results = [await limiter.hit("login:1.2.3.4", rate) for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[0].remaining == 2
    assert results[3].retry_after >= 1
    assert (await limiter.hit("login:5.6.7.8", rate)).allowed
