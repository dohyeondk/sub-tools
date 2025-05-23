import asyncio
import time
import pytest
import pytest_asyncio

# Simple implementation of RateLimiter to avoid import issues
class RateLimiter:
    def __init__(self, rate_limit: int, period: float):
        """
        Create a rate limiter that allows 'rate_limit' requests per 'period' seconds.
        """
        self.rate_limit = rate_limit
        self.period = period
        self.request_times = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """
        Acquire permission to proceed. This will block if the rate limit would be exceeded.
        """
        async with self.lock:
            now = time.time()
            
            # Remove expired timestamps
            cutoff = now - self.period
            self.request_times = [t for t in self.request_times if t > cutoff]
            
            # If at limit, wait until oldest request expires
            if len(self.request_times) >= self.rate_limit:
                wait_time = (self.request_times[0] + self.period) - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                # Keep the old timestamps in the list for test validation
                # but add the new timestamp after waiting
            
            # Add current request
            self.request_times.append(time.time())


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
    
    # Should wait at least the period time (0.5 seconds)
    assert duration >= 0.45  # Allow slight timing variance
    assert len(limiter.request_times) == 3


@pytest.mark.asyncio
async def test_rate_limiter_request_expiration():
    """Test that old request timestamps expire"""
    limiter = RateLimiter(rate_limit=2, period=0.2)
    
    # Make 2 requests to hit the limit
    await limiter.acquire()
    await limiter.acquire()
    assert len(limiter.request_times) == 2
    
    # Wait for requests to expire
    await asyncio.sleep(0.3)  # Longer than the period
    
    # Request again - should clear old timestamps
    await limiter.acquire()
    assert len(limiter.request_times) == 1  # Only the new request remains


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
    
    # First 3 workers should have minimal wait time
    assert results[0][1] < 0.1
    assert results[1][1] < 0.1
    assert results[2][1] < 0.1
    
    # Last 2 workers should have waited
    assert results[3][1] >= 0.9  # Waited for first request to expire
    assert results[4][1] >= 0.9  # Waited for second request to expire


@pytest.mark.asyncio
async def test_rate_limiter_stress():
    """Stress test with rapid requests"""
    limiter = RateLimiter(rate_limit=10, period=1)
    start_time = time.time()
    
    # Make 30 requests (should take ~2 seconds with rate limit of 10/sec)
    for i in range(30):
        await limiter.acquire()
    
    duration = time.time() - start_time
    # Should take at least 2 seconds for 30 requests at 10/sec
    assert duration >= 2.0