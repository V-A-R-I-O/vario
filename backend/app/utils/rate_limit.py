import time
from collections import defaultdict
from typing import Tuple

class InMemoryRateLimiter:
    def __init__(self):
        # key: (group, identifier) -> list of timestamps
        self.requests = defaultdict(list)
    
    def is_allowed(self, group: str, identifier: str, limit: int, window: int) -> Tuple[bool, int, int, int]:
        """
        Returns (allowed, limit, remaining, reset_time_in_seconds)
        """
        now = time.time()
        key = (group, identifier)
        
        # Clean up old requests
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        
        if len(self.requests[key]) >= limit:
            # Rate limited
            reset_time = int(self.requests[key][0] + window - now)
            return False, limit, 0, reset_time
        
        self.requests[key].append(now)
        remaining = limit - len(self.requests[key])
        reset_time = int(self.requests[key][0] + window - now)
        return True, limit, remaining, reset_time

limiter = InMemoryRateLimiter()
