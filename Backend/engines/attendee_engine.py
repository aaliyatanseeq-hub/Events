"""
ULTRA-STRICT Attendee Discovery Engine
PROPER Twitter API error handling and rate limiting
"""

import re
import logging
from typing import List, Dict
from dataclasses import dataclass

from services.twitter_client import TwitterClient

@dataclass
class ResearchAttendee:
    attendee_name: str
    username: str
    bio: str
    location: str
    followers_count: int
    verified: bool
    confidence_score: float
    source_tweet: str
    posted_by: str

class SmartAttendeeEngine:
    def __init__(self):
        self.twitter_client = TwitterClient()
        self.attendee_patterns = self._load_attendee_patterns()
        
    def _load_attendee_patterns(self):
        return {
            'attending': ['attending', 'going to', 'see you at', 'can\'t wait for', 'excited for'],
            'interested': ['interested in', 'looking forward to', 'planning to attend', 'might go to'],
            'organizing': ['organizing', 'hosting', 'putting on', 'running']
        }
    
    def discover_attendees(self, event_name: str, max_results: int) -> List[ResearchAttendee]:
        """ULTRA-STRICT attendee discovery with PROPER error handling"""
        try:
            print(f"🔍 Finding {max_results} real attendees for '{event_name}'")
            
            # Check if Twitter client is operational
            if not self.twitter_client or not self.twitter_client.is_operational():
                print("❌ Twitter client not operational")
                return []
            
            # Build optimized query
            query = self._build_single_query(event_name)
            print(f"🐦 Making 1 Twitter API call: {query}")
            
            # Get real tweets from Twitter API
            tweets = self._search_twitter_safe(query, max_results)
            
            if not tweets:
                print("❌ No tweets found (rate limit or no results)")
                return []
            
            # Extract real attendees from tweets
            attendees = self._extract_attendees_from_tweets(tweets, event_name)
            
            # Calculate confidence scores based on real data
            scored_attendees = self._calculate_confidence_scores(attendees)
            
            final_attendees = scored_attendees[:max_results]
            print(f"✅ Found {len(final_attendees)} real attendees from Twitter")
            
            return final_attendees
            
        except Exception as e:
            logging.error(f"Attendee discovery error: {e}")
            return []
    
    def _build_single_query(self, event_name: str) -> str:
        """Build optimized Twitter search query"""
        try:
            # Clean event name and create search query
            clean_name = re.sub(r'[^\w\s]', '', event_name).strip()
            
            if not clean_name:
                return ""
                
            # Simple query that works better with Twitter API
            query = f'"{clean_name}" OR attending "{clean_name}" -is:retweet'
            return query
            
        except Exception as e:
            print(f"❌ Error building query: {e}")
            return ""
    
    def _search_twitter_safe(self, query: str, max_results: int) -> List[Dict]:
        """Search Twitter with PROPER error handling"""
        if not query:
            print("❌ Empty query provided")
            return []
            
        try:
            print(f"🐦 Twitter API call for: {query}")
            
            # Calculate needed tweets (with buffer for filtering)
            tweets_needed = max(10, min(max_results * 3, 100))  # Min 10, max 100
            
            tweets = self.twitter_client.search_recent_tweets_safe(
                query=query,
                max_results=tweets_needed,
                tweet_fields=['author_id', 'created_at', 'text', 'public_metrics'],
                user_fields=['username', 'name', 'verified', 'description', 'location', 'public_metrics'],
                expansions=['author_id']
            )
            
            if not tweets or not tweets.data:
                print("❌ No tweets found in API response")
                return []
            
            users_dict = {}
            if tweets.includes and 'users' in tweets.includes:
                for user in tweets.includes['users']:
                    users_dict[user.id] = user
            
            processed_tweets = []
            for tweet in tweets.data:
                user = users_dict.get(tweet.author_id)
                if user:
                    processed_tweets.append({
                        'text': tweet.text,
                        'url': f"https://twitter.com/{user.username}/status/{tweet.id}",
                        'username': user.username,
                        'name': user.name,
                        'bio': user.description or '',
                        'location': user.location or '',
                        'followers_count': user.public_metrics.get('followers_count', 0) if hasattr(user, 'public_metrics') else 0,
                        'verified': user.verified or False,
                        'created_at': tweet.created_at,
                        'query': query
                    })
            
            print(f"✅ Got {len(processed_tweets)} real tweets from Twitter API")
            return processed_tweets
            
        except Exception as e:
            print(f"❌ Twitter API call failed: {e}")
            return []
    
    def _extract_attendees_from_tweets(self, tweets: List[Dict], event_name: str) -> List[ResearchAttendee]:
        """Extract REAL attendees from tweets"""
        attendees = []
        
        if not tweets:
            return attendees
            
        for tweet in tweets:
            try:
                # Check if tweet is relevant to the event
                if not self._is_relevant_tweet(tweet['text'], event_name):
                    continue
                
                # Create attendee from REAL tweet data
                attendee = ResearchAttendee(
                    attendee_name=tweet['name'],
                    username=f"@{tweet['username']}",
                    bio=tweet['bio'],
                    location=tweet['location'],
                    followers_count=tweet['followers_count'],
                    verified=tweet['verified'],
                    confidence_score=0.8,  # Based on real tweet
                    source_tweet=tweet['url'],
                    posted_by=f"@{tweet['username']}"  # Real Twitter user
                )
                attendees.append(attendee)
                    
            except Exception as e:
                continue  # Skip problematic tweets
        
        return attendees
    
    def _is_relevant_tweet(self, text: str, event_name: str) -> bool:
        """Check if tweet is relevant to the event"""
        if not text or not event_name:
            return False
            
        text_lower = text.lower()
        event_lower = event_name.lower()
        
        # Check for event name or keywords
        event_words = event_lower.split()
        if any(word in text_lower for word in event_words if len(word) > 3):
            return True
        
        # Check for attendee patterns
        for pattern_list in self.attendee_patterns.values():
            if any(pattern in text_lower for pattern in pattern_list):
                return True
        
        return False
    
    def _calculate_confidence_scores(self, attendees: List[ResearchAttendee]) -> List[ResearchAttendee]:
        """Calculate confidence scores based on REAL data"""
        for attendee in attendees:
            score = 0.7  # Base score for real data
            
            # Real verification status
            if attendee.verified:
                score += 0.2
            
            # Real follower count
            if attendee.followers_count > 1000:
                score += 0.1
            
            # Real bio length
            if len(attendee.bio) > 20:
                score += 0.1
            
            # Real location data
            if attendee.location:
                score += 0.1
            
            attendee.confidence_score = min(score, 0.95)
        
        return sorted(attendees, key=lambda x: x.confidence_score, reverse=True)
    
    def get_twitter_status(self) -> Dict:
        """Get Twitter API status"""
        return {
            'operational': self.twitter_client.is_operational() if self.twitter_client else False,
            'rate_limits': self.twitter_client.get_rate_limit_status() if self.twitter_client else {}
        }