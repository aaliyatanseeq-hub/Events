"""
ULTRA-STRICT Event Discovery Engine WITH SMART CACHING
Fixed SerpAPI queries and response handling
"""

import re
import requests
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ResearchEvent:
    event_name: str
    exact_date: str
    exact_venue: str
    location: str
    category: str
    confidence_score: float
    source_tweet: str
    posted_by: str

class SmartEventEngine:
    def __init__(self):
        self.serp_api_key = os.getenv('SERP_API_KEY')
        self.event_cache = {}
        
    def discover_events(self, location: str, start_date: str, end_date: str, categories: List[str], max_results: int) -> List[ResearchEvent]:
        """Smart event discovery with caching and mixed results"""
        try:
            print(f"🔍 SMART CACHE: Finding {max_results} events in {location} ({start_date} to {end_date})")
            
            # Check cache for matching date ranges
            cached_events = self._get_cached_events(location, start_date, end_date)
            print(f"📦 Found {len(cached_events)} cached events")
            
            # Calculate how many new events we need
            needed_new_events = max(0, max_results - len(cached_events))
            
            new_events = []
            if needed_new_events > 0:
                print(f"🔄 Need {needed_new_events} new events")
                new_events = self._get_new_events_serpapi(
                    location=location,
                    start_date=start_date,
                    end_date=end_date,
                    category=categories[0] if categories else "all",
                    max_results=needed_new_events
                )
                
                # Cache the new events only if we found some
                if new_events:
                    self._cache_events(location, start_date, end_date, new_events)
            
            # Combine cached + new events
            all_events = cached_events + new_events
            
            # Remove duplicates and limit to max_results
            final_events = self._remove_duplicates(all_events)[:max_results]
            
            print(f"✅ SMART RESULTS: {len(cached_events)} cached + {len(new_events)} new = {len(final_events)} total")
            
            return final_events
            
        except Exception as e:
            print(f"❌ Smart event discovery error: {e}")
            return []
    
    def _get_cached_events(self, location: str, start_date: str, end_date: str) -> List[ResearchEvent]:
        """Get events from cache that match the date range"""
        cached_events = []
        
        if location not in self.event_cache:
            return []
        
        search_start = datetime.strptime(start_date, '%Y-%m-%d')
        search_end = datetime.strptime(end_date, '%Y-%m-%d')
        
        for cached_range, events in self.event_cache[location].items():
            cache_start_str, cache_end_str = cached_range.split('_')
            cache_start = datetime.strptime(cache_start_str, '%Y-%m-%d')
            cache_end = datetime.strptime(cache_end_str, '%Y-%m-%d')
            
            # Check if search range overlaps with cached range
            if self._ranges_overlap(search_start, search_end, cache_start, cache_end):
                # Filter events that fall within search range
                for event in events:
                    try:
                        event_date = datetime.strptime(event.exact_date, '%Y-%m-%d')
                        if search_start <= event_date <= search_end:
                            cached_events.append(event)
                    except:
                        continue
        
        return cached_events
    
    def _ranges_overlap(self, start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        """Check if two date ranges overlap"""
        return not (end1 < start2 or start1 > end2)
    
    def _cache_events(self, location: str, start_date: str, end_date: str, events: List[ResearchEvent]):
        """Cache events for future searches"""
        if location not in self.event_cache:
            self.event_cache[location] = {}
        
        cache_key = f"{start_date}_{end_date}"
        self.event_cache[location][cache_key] = events
        
        print(f"💾 Cached {len(events)} events for {location} ({start_date} to {end_date})")
        
        # Limit cache size per location (keep last 5 ranges)
        if len(self.event_cache[location]) > 5:
            # Remove oldest cache entry
            oldest_key = next(iter(self.event_cache[location]))
            del self.event_cache[location][oldest_key]
            print(f"🗑️  Removed oldest cache: {oldest_key}")
    
    def _get_new_events_serpapi(self, location: str, start_date: str, end_date: str, category: str, max_results: int) -> List[ResearchEvent]:
        """Get new events from SerpAPI with better queries"""
        try:
            print(f"🔄 SERPAPI: Getting {max_results} new events for {location}")
            
            queries = self._build_optimized_queries(location, start_date, end_date, category)
            all_events = []
            
            for i, query in enumerate(queries[:max_results]):
                try:
                    print(f"📡 SerpAPI Call {i+1}: '{query}'")
                    
                    params = {
                        "q": query, 
                        "location": location, 
                        "hl": "en", 
                        "api_key": self.serp_api_key,
                        "engine": "google_events"
                    }
                    
                    response = requests.get("https://serpapi.com/search", params=params, timeout=15)
                    
                    if response.status_code != 200:
                        print(f"❌ HTTP {response.status_code} for: {query}")
                        continue
                        
                    data = response.json()
                    
                    # DEBUG: Print what we got from SerpAPI
                    self._debug_serpapi_response(data, query)
                    
                    # Extract events from API response
                    extracted_events = self._extract_events_from_serpapi(data, location, start_date, end_date)
                    
                    if extracted_events:
                        all_events.extend(extracted_events)
                        print(f"✅ Found {len(extracted_events)} events from: {query}")
                    else:
                        print(f"ℹ️ No events extracted from: {query}")
                        
                    # Stop if we have enough events
                    if len(all_events) >= max_results * 2:
                        break
                        
                except Exception as e:
                    print(f"❌ SerpAPI call {i+1} failed: {e}")
                    continue
            
            # Convert to ResearchEvent format
            research_events = self._convert_to_research_events(all_events, location)
            final_events = research_events[:max_results]
            
            print(f"🔄 SERPAPI FINAL: Got {len(final_events)} events from {len(queries)} queries")
            return final_events
            
        except Exception as e:
            print(f"❌ SerpAPI new events error: {e}")
            return []
    
    def _build_optimized_queries(self, location: str, start_date: str, end_date: str, category: str) -> List[str]:
        """Build BETTER SerpAPI queries that actually work"""
        
        # Convert dates to readable format
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Get month names for better queries
        start_month = start_dt.strftime('%B %Y')
        end_month = end_dt.strftime('%B %Y')
        
        base_queries = [
            # Natural language queries that work better
            f"events in {location}",
            f"upcoming events {location}",
            f"things to do in {location}",
            f"{location} events {start_month}",
            f"concerts in {location}",
            f"festivals {location}",
            f"shows in {location}",
            f"entertainment {location}",
            f"nightlife {location}",
            f"cultural events {location}",
        ]
        
        # Add category-specific queries
        if category == "music" or category == "all":
            base_queries.extend([
                f"concerts {location} {start_month}",
                f"music events {location}",
                f"live music {location}",
            ])
        
        if category == "sports" or category == "all":
            base_queries.extend([
                f"sports events {location}",
                f"games {location} {start_month}",
            ])
            
        if category == "food" or category == "all":
            base_queries.extend([
                f"food festivals {location}",
                f"culinary events {location}",
            ])
        
        return base_queries
    
    def _debug_serpapi_response(self, data: Dict, query: str):
        """Debug what SerpAPI returned"""
        print(f"🔍 DEBUG for '{query}':")
        
        if 'error' in data:
            print(f"   ❌ SerpAPI Error: {data['error']}")
            return
            
        if 'events_results' in data:
            events_count = len(data['events_results'])
            print(f"   ✅ events_results: {events_count} events")
            
            # Show first few event titles if available
            for i, event in enumerate(data['events_results'][:3]):
                title = event.get('title', 'No title')
                date = event.get('date', 'No date')
                print(f"   📅 Event {i+1}: '{title}' - {date}")
        else:
            print(f"   ℹ️ No 'events_results' in response")
            
        # Check for other result types
        if 'organic_results' in data:
            print(f"   🔍 organic_results: {len(data['organic_results'])} results")
        
        print("")  # Empty line for readability
    
    def _extract_events_from_serpapi(self, data: Dict, location: str, start_date: str, end_date: str) -> List[Dict]:
        """Extract events from SerpAPI response with better parsing"""
        events = []
        
        if 'events_results' not in data or not data['events_results']:
            return events
        
        for event in data['events_results']:
            try:
                title = event.get('title', '').strip()
                if not title or title == 'Unknown':
                    continue
                
                # Parse event date
                event_date_str = event.get('date', '')
                event_date = self._parse_event_date(event_date_str)
                
                # If we can't parse the date, try to extract from description
                if not event_date:
                    event_date = self._extract_date_from_description(event.get('description', ''))
                
                # Use today's date as fallback
                if not event_date:
                    event_date = datetime.now()
                
                # Format date for storage
                formatted_date = event_date.strftime('%Y-%m-%d')
                
                # Check if event is within our date range
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                
                if start_dt <= event_date <= end_dt:
                    events.append({
                        'name': title,
                        'date': formatted_date,
                        'venue': event.get('address', location),
                        'description': event.get('description', ''),
                        'link': event.get('link', ''),
                        'category': self._classify_event_type(title)
                    })
                    
            except Exception as e:
                print(f"   ⚠️ Failed to parse event: {e}")
                continue
        
        return events
    
    def _parse_event_date(self, date_str: str) -> Optional[datetime]:
        """Parse event date string to datetime object"""
        if not date_str:
            return None
            
        try:
            # Clean the date string
            date_str = date_str.strip()
            
            # Handle date ranges (take the start date)
            if ' to ' in date_str:
                date_str = date_str.split(' to ')[0].strip()
            elif ' - ' in date_str:
                date_str = date_str.split(' - ')[0].strip()
            
            # Try different date formats
            date_formats = [
                '%Y-%m-%d',
                '%b %d, %Y',
                '%B %d, %Y', 
                '%d %b %Y',
                '%d %B %Y',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _extract_date_from_description(self, description: str) -> Optional[datetime]:
        """Try to extract date from event description"""
        if not description:
            return None
            
        try:
            # Look for common date patterns in description
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, description)
                if match:
                    return self._parse_event_date(match.group(1))
                    
            return None
        except:
            return None
    
    def _classify_event_type(self, text: str) -> str:
        """Classify event type based on content"""
        if not text:
            return 'other'
            
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['concert', 'music', 'dj', 'band', 'live music']): 
            return 'music'
        if any(word in text_lower for word in ['conference', 'summit', 'workshop', 'business', 'tech']): 
            return 'conference'
        if any(word in text_lower for word in ['festival', 'cultural', 'celebration']): 
            return 'festival'
        if any(word in text_lower for word in ['sports', 'game', 'match', 'tournament', 'race']): 
            return 'sports'
        if any(word in text_lower for word in ['art', 'theater', 'exhibition', 'gallery', 'museum']): 
            return 'arts'
        if any(word in text_lower for word in ['food', 'drink', 'culinary', 'wine', 'beer']): 
            return 'food'
        if any(word in text_lower for word in ['family', 'kids', 'children']): 
            return 'family'
        if any(word in text_lower for word in ['comedy', 'standup', 'improv']): 
            return 'comedy'
        
        return 'other'
    
    def _remove_duplicates(self, events: List[ResearchEvent]) -> List[ResearchEvent]:
        """Remove duplicate events based on name and date"""
        seen = set()
        unique = []
        
        for event in events:
            identifier = (event.event_name.lower().strip(), event.exact_date)
            if identifier not in seen:
                seen.add(identifier)
                unique.append(event)
        
        return unique
    
    def _convert_to_research_events(self, serp_events: List[Dict], location: str) -> List[ResearchEvent]:
        """Convert SerpAPI events to ResearchEvent format"""
        research_events = []
        
        for event in serp_events:
            research_event = ResearchEvent(
                event_name=event['name'],
                exact_date=event['date'],
                exact_venue=event['venue'],
                location=location,
                category=event['category'],
                confidence_score=0.85,
                source_tweet=event['link'],
                posted_by="Google Events"
            )
            research_events.append(research_event)
        
        return research_events
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for debugging"""
        stats = {
            'total_locations': len(self.event_cache),
            'locations': {}
        }
        
        for location, ranges in self.event_cache.items():
            stats['locations'][location] = {
                'cached_ranges': len(ranges),
                'total_events': sum(len(events) for events in ranges.values())
            }
        
        return stats