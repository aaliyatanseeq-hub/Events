"""
Twitter Client with Proper Rate Limiting and Error Handling
"""

import os
import tweepy
import time
import random
from dotenv import load_dotenv
from services.rate_limiter import TwitterRateLimiter, APICache

load_dotenv()

class TwitterClient:
    def __init__(self):
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_secret = os.getenv('TWITTER_ACCESS_SECRET')
        self.client = None
        self.rate_limiter = TwitterRateLimiter()
        self.cache = APICache(ttl_minutes=30)
        self.setup_client()
    
    def setup_client(self):
        """Setup Twitter API client"""
        try:
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret,
                wait_on_rate_limit=False  # We handle rate limiting ourselves
            )
            print("✅ Twitter API client initialized")
            return True
        except Exception as e:
            print(f"❌ Twitter client setup failed: {e}")
            return False
    
    def make_request_with_retry(self, endpoint: str, request_func, *args, **kwargs):
        """
        Make API request with rate limiting and SHORT backoff
        """
        max_retries = 1  # Only 1 retry to avoid long waits
        base_delay = 2   # Short base delay
        
        for attempt in range(max_retries + 1):  # +1 for the initial attempt
            # Check rate limit
            if not self.rate_limiter.check_rate_limit(endpoint):
                wait_time = self.rate_limiter.get_wait_time(endpoint)
                print(f"⏳ Rate limit hit for {endpoint}. Waiting {wait_time:.1f} seconds...")
                
                # MAX WAIT: 15 seconds instead of 60
                wait_time = min(wait_time, 15)
                time.sleep(wait_time + random.uniform(0.1, 0.5))
            
            try:
                # Check cache first for identical requests
                cache_key = None
                if endpoint == 'search_recent':
                    query = kwargs.get('query') or (args[0] if args else None)
                    if query:
                        cache_key = f"search_{hash(query)}"
                        cached = self.cache.get(cache_key)
                        if cached:
                            print(f"📦 Using cached results for: {query}")
                            return cached
                
                # Make API request
                print(f"🔍 Making API request to {endpoint} (attempt {attempt + 1})")
                response = request_func(*args, **kwargs)
                
                # Update rate limits from response
                if hasattr(response, 'headers'):
                    self.rate_limiter.update_from_headers(endpoint, response.headers)
                
                # Cache successful responses
                if cache_key and response:
                    self.cache.set(cache_key, response)
                
                return response
                
            except tweepy.TooManyRequests as e:
                print(f"⚠️ Rate limit exceeded (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries:
                    # SHORT backoff: max 10 seconds
                    max_wait = 10
                    sleep_time = min(base_delay * (2 ** attempt), max_wait) + random.uniform(0.1, 1.0)
                    
                    print(f"⏳ Waiting {sleep_time:.1f} seconds before retry...")
                    time.sleep(sleep_time)
                else:
                    print("❌ Max retries reached for rate limit")
                    return None
                
            except tweepy.BadRequest as e:
                print(f"❌ Bad request error (attempt {attempt + 1}): {e}")
                return None  # Don't retry bad requests
                
            except Exception as e:
                print(f"❌ API request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    sleep_time = base_delay * (2 ** attempt) + random.uniform(0.1, 1.0)
                    print(f"⏳ Waiting {sleep_time:.1f} seconds before retry...")
                    time.sleep(sleep_time)
                else:
                    return None
        
        return None
    
    def search_recent_tweets_safe(self, query: str, max_results: int = 10, **kwargs):
        """Safe search with proper max_results handling"""
        try:
            # FIX: Twitter API requires min 10, max 100 for max_results
            twitter_max_results = max(10, min(max_results, 100))
            
            return self.make_request_with_retry(
                'search_recent',
                self.client.search_recent_tweets,
                query=query,
                max_results=twitter_max_results,
                **kwargs
            )
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return None
    
    def get_rate_limit_status(self):
        """Get current rate limit status"""
        return self.rate_limiter.get_status()
    
    def clear_cache(self):
        """Clear API cache"""
        self.cache.clear_expired()
    
    def is_operational(self):
        """Check if client is operational"""
        return self.client is not None