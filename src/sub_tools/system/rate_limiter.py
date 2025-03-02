
import asyncio
import time


class RateLimiter:
    def __init__(self, rate_limit: float, period: float):
        """
        Initialize a rate limiter.

        Args:
            rate_limit: Maximum number of requests in the time
            period: Time period in seconds
        """
        self.rate_limit = rate_limit
        self.period = period
        self.request_times = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request, waiting if necessary."""
        async with self.lock:
            current_time = time.time()

            # Remove timestamps older than the period
            cutoff = current_time - self.period
            self.request_times = [t for t in self.request_times if t > cutoff]

            # If we've reached the limit, wait until the oldest request expires
            if len(self.request_times) >= self.rate_limit:
                wait_time = self.request_times[0] + self.period - current_time

                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                    # Recalculate current time after waiting
                    current_time = time.time()

            # Add the current request timestamp
            self.request_times.append(current_time)
