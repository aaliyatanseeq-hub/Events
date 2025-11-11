"""
Advanced Rate Limiter for Twitter API
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading

class TwitterRateLimiter:
    def __init__(self):
        self.rate_limits = {}
        self.lock = threading.Lock()
        self.setup_default_limits()
    
    def setup_default_limits(self):
        """Setup default rate limits for Twitter API v2"""
        self.rate_limits['search_recent'] = {
            'limit': 450,
            'remaining': 450,
            'reset_time': None,
            'window_minutes': 15
        }
        
        self.rate_limits['users'] = {
            'limit': 300,
            'remaining': 300,
            'reset_time': None,
            'window_minutes': 15
        }
    
    def check_rate_limit(self, endpoint: str) -> bool:
        """Check if we can make a request to the endpoint"""
        with self.lock:
            if endpoint not in self.rate_limits:
                return True
            
            limit_info = self.rate_limits[endpoint]
            
            if limit_info['reset_time'] and datetime.now() > limit_info['reset_time']:
                limit_info['remaining'] = limit_info['limit']
                limit_info['reset_time'] = None
            
            if limit_info['remaining'] > 0:
                limit_info['remaining'] -= 1
                return True
            else:
                if not limit_info['reset_time']:
                    limit_info['reset_time'] = datetime.now() + timedelta(minutes=limit_info['window_minutes'])
                return False
    
    def update_from_headers(self, endpoint: str, headers: Dict):
        """Update rate limits from API response headers"""
        with self.lock:
            if endpoint not in self.rate_limits:
                return
            
            limit_info = self.rate_limits[endpoint]
            
            if 'x-rate-limit-limit' in headers:
                limit_info['limit'] = int(headers['x-rate-limit-limit'])
            
            if 'x-rate-limit-remaining' in headers:
                limit_info['remaining'] = int(headers['x-rate-limit-remaining'])
            
            if 'x-rate-limit-reset' in headers:
                reset_timestamp = int(headers['x-rate-limit-reset'])
                limit_info['reset_time'] = datetime.fromtimestamp(reset_timestamp)
    
    def get_wait_time(self, endpoint: str) -> float:
        """Get recommended wait time if rate limited"""
        with self.lock:
            if endpoint not in self.rate_limits:
                return 0
            
            limit_info = self.rate_limits[endpoint]
            
            if limit_info['reset_time']:
                wait_seconds = (limit_info['reset_time'] - datetime.now()).total_seconds()
                return max(wait_seconds, 0)
            
            return 60
    
    def get_status(self) -> Dict:
        """Get current rate limit status"""
        status = {}
        for endpoint, info in self.rate_limits.items():
            status[endpoint] = {
                'remaining': info['remaining'],
                'limit': info['limit'],
                'reset_time': info['reset_time'].isoformat() if info['reset_time'] else None
            }
        return status

class APICache:
    def __init__(self, ttl_minutes: int = 30):
        self.cache = {}
        self.ttl = ttl_minutes * 60
        self.lock = threading.Lock()
    
    def get(self, key: str):
        """Get cached value"""
        with self.lock:
            if key in self.cache:
                data, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return data
                else:
                    del self.cache[key]
            return None
    
    def set(self, key: str, value):
        """Set cached value"""
        with self.lock:
            self.cache[key] = (value, time.time())
    
    def clear_expired(self):
        """Clear expired cache entries"""
        with self.lock:
            current_time = time.time()
            expired_keys = [k for k, (_, ts) in self.cache.items() if current_time - ts >= self.ttl]
            for key in expired_keys:
                del self.cache[key]