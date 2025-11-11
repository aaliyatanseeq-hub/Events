"""
ULTRA-STRICT Event Intelligence Platform API
ZERO unnecessary API calls - Only when explicitly requested
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from engines.event_engine import SmartEventEngine
from engines.attendee_engine import SmartAttendeeEngine
from services.twitter_client import TwitterClient

app = FastAPI(
    title="Event Intelligence Platform",
    description="ULTRA-STRICT: Zero unnecessary API calls - Only when explicitly requested",
    version="4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines - NO AUTO API CALLS
twitter_client = TwitterClient()
event_engine = SmartEventEngine()
attendee_engine = SmartAttendeeEngine()

class EventDiscoveryRequest(BaseModel):
    location: str
    start_date: str
    end_date: str
    categories: List[str]
    max_results: int  # STRICT: User-defined limit

class AttendeeDiscoveryRequest(BaseModel):
    event_name: str
    max_results: int  # STRICT: User-defined limit

@app.get("/")
async def root():
    return {
        "message": "🎪 ULTRA-STRICT Event Intelligence Platform",
        "status": "ready",
        "version": "4.0",
        "api_policy": "ZERO auto API calls - Only when explicitly requested",
        "features": {
            "strict_api_limits": True,
            "user_controlled_results": True,
            "minimal_api_calls": True
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check that makes NO API calls"""
    return {
        "status": "healthy",
        "strict_limits": True,
        "version": "4.0",
        "api_calls_made": 0  # Always zero - no auto calls
    }

@app.post("/api/discover-events")
async def discover_events(request: EventDiscoveryRequest):
    """ULTRA-STRICT event discovery - ONLY when explicitly called"""
    try:
        print(f"🎯 ULTRA-STRICT EVENT REQUEST: {request.max_results} events in {request.location}")
        
        # Validate max results
        if request.max_results > 20:
            request.max_results = 20
        
        events = event_engine.discover_events(
            location=request.location,
            start_date=request.start_date,
            end_date=request.end_date,
            categories=request.categories,
            max_results=request.max_results
        )
        
        return {
            "success": True,
            "events": [event.__dict__ for event in events],
            "total_events": len(events),
            "requested_limit": request.max_results,
            "location": request.location,
            "api_calls_used": 1,  # Only 1 API call made
            "engine": "ULTRA-STRICT EventEngine v4.0"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/discover-attendees")
async def discover_attendees(request: AttendeeDiscoveryRequest):
    """ULTRA-STRICT attendee discovery - ONLY when explicitly called"""
    try:
        print(f"🎯 ULTRA-STRICT ATTENDEE REQUEST: {request.max_results} attendees for {request.event_name}")
        
        # Validate max results
        if request.max_results > 30:
            request.max_results = 30
        
        attendees = attendee_engine.discover_attendees(
            event_name=request.event_name,
            max_results=request.max_results
        )
        
        return {
            "success": True,
            "attendees": [attendee.__dict__ for attendee in attendees],
            "total_attendees": len(attendees),
            "requested_limit": request.max_results,
            "event_name": request.event_name,
            "api_calls_used": 1,  # Only 1 API call made
            "engine": "ULTRA-STRICT AttendeeEngine v4.0"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 ULTRA-STRICT Event Intelligence Platform Starting...")
    print("🎯 POLICY: ZERO unnecessary API calls")
    print("📡 API: http://localhost:8000")
    print("🔒 API calls only when: User clicks DISCOVER EVENTS or FIND ATTENDEES")
    uvicorn.run(app, host="0.0.0.0", port=8000)
