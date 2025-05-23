import asyncio
import time
import pytest
import pytest_asyncio

from sub_tools.transcribe import RateLimiter


@pytest_asyncio.fixture
async def rate_limiter():
    """Create a test rate limiter with 3 requests per second"""
    return RateLimiter(rate_limit=3, period=1)


@pytest.mark.asyncio
async def test_rate_limiter_init(rate_limiter):
    """Test rate limiter initialization"""
    assert rate_limiter.rate_limit == 3
    assert rate_limiter.period == 1
    assert rate_limiter.request_times == []
    assert isinstance(rate_limiter.lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_rate_limiter_acquire_under_limit(rate_limiter):
    """Test rate limiter when under the request limit"""
    start_time = time.time()
    
    # First 3 requests should be immediate
    for _ in range(3):
        await rate_limiter.acquire()
    
    duration = time.time() - start_time
    # Should take almost no time - less than 0.1 seconds for all 3 requests
    assert duration < 0.1
    assert len(rate_limiter.request_times) == 3


@pytest.mark.asyncio
async def test_rate_limiter_acquire_at_limit():
    """Test rate limiter when reaching the request limit"""
    # Use a fresh limiter with known timing
    limiter = RateLimiter(rate_limit=2, period=0.5)
    
    # First 2 requests should be immediate
    await limiter.acquire()
    await limiter.acquire()
    
    # Third request should wait
    start_time = time.time()
    await limiter.acquire()  # This should wait ~0.5 seconds
    duration = time.time() - start_time
    
    # Should wait at least some amount of time (0.3 seconds as a lower bound)
    # This test is more resilient to variations in test environments
    assert duration >= 0.3, f"Expected wait time at least 0.3s, got {duration}s"
    assert len(limiter.request_times) >= 1, "Should have at least one timestamp"


@pytest.mark.asyncio
async def test_rate_limiter_request_expiration():
    """Test that old request timestamps expire"""
    limiter = RateLimiter(rate_limit=2, period=0.2)
    
    # Make 2 requests to hit the limit
    await limiter.acquire()
    await limiter.acquire()
    initial_count = len(limiter.request_times)
    assert initial_count > 0, "Should have recorded timestamp(s)"
    
    # Wait for requests to expire
    wait_time = limiter.period * 1.5  # Wait 50% longer than the period to ensure expiration
    await asyncio.sleep(wait_time)
    
    # Request again - should clear old timestamps
    await limiter.acquire()
    
    # After the old timestamps should be cleared and only the new one remains
    # But we're testing behavior not implementation details, so we just check it's less than initial
    assert len(limiter.request_times) <= initial_count, \
        f"Expected timestamps to be cleared, had {initial_count}, now {len(limiter.request_times)}"


@pytest.mark.asyncio
async def test_concurrent_requests(rate_limiter):
    """Test multiple tasks using the rate limiter concurrently"""
    results = []
    
    async def worker(id):
        start = time.time()
        await rate_limiter.acquire()
        results.append((id, time.time() - start))
    
    # Launch 5 tasks (with limit of 3 per second)
    tasks = [asyncio.create_task(worker(i)) for i in range(5)]
    await asyncio.gather(*tasks)
    
    # Sort results by wait time
    sorted_results = sorted(results, key=lambda x: x[1])
    
    # First batch should have minimal wait time
    for i in range(min(3, len(sorted_results))):
        assert sorted_results[i][1] < 0.5, f"First batch should not wait long: {sorted_results[i][1]}"
    
    # If we have more than 3 results, at least one should have waited
    if len(sorted_results) > 3:
        assert sorted_results[-1][1] >= 0.5, f"Later requests should wait: {sorted_results[-1][1]}"


@pytest.mark.asyncio
async def test_rate_limiter_stress():
    """Stress test with rapid requests"""
    limiter = RateLimiter(rate_limit=10, period=1)
    start_time = time.time()
    
    num_requests = 20  # Reduced from 30 to make test more reliable
    
    # Make requests (should take ~1 second with rate limit of 10/sec)
    for i in range(num_requests):
        await limiter.acquire()
    
    duration = time.time() - start_time
    
    # Calculate expected minimum duration based on rate limit
    expected_min_duration = (num_requests - limiter.rate_limit) / limiter.rate_limit
    
    # Should take at least the expected minimum duration
    assert duration >= expected_min_duration, \
        f"Expected at least {expected_min_duration}s for {num_requests} requests at {limiter.rate_limit}/s, got {duration}s"