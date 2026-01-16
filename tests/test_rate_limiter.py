from app.core.rate_limiter import TokenBucketRateLimiter


def test_token_bucket_allows_burst_then_denies() -> None:
    now = 1000.0

    def time_fn() -> float:
        return now

    limiter = TokenBucketRateLimiter(capacity=2, refill_rate_per_sec=1.0, time_fn=time_fn)

    assert limiter.allow("k")[0] is True
    assert limiter.allow("k")[0] is True

    allowed, retry_after = limiter.allow("k")
    assert allowed is False
    assert retry_after is not None
    assert retry_after > 0


def test_token_bucket_refills_over_time() -> None:
    now = 1000.0

    def time_fn() -> float:
        return now

    limiter = TokenBucketRateLimiter(capacity=1, refill_rate_per_sec=1.0, time_fn=time_fn)

    assert limiter.allow("k")[0] is True
    assert limiter.allow("k")[0] is False

    now += 1.0
    assert limiter.allow("k")[0] is True
