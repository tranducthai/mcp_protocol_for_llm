from typing import Any, List, Dict
import httpx
import json
import os
from mcp.server.fastmcp import FastMCP
import sys
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("openstreetmap")

print("OpenStreetMap server initialized", file=sys.stderr)

# Constants
NOMINATIM_API_BASE = "https://nominatim.openstreetmap.org"
OVERPASS_API_BASE = "https://overpass-api.de/api/interpreter"
OSRM_API_BASE = "https://router.project-osrm.org"
USER_AGENT = "osm-mcp-server/1.0"

async def make_nominatim_request(url: str, params: dict) -> dict[str, Any] | None:
    """Make a request to Nominatim API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Nominatim API error: {e}", file=sys.stderr)
            return None

async def make_overpass_request(query: str) -> dict[str, Any] | None:
    """Make a request to Overpass API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                OVERPASS_API_BASE, 
                data={"data": query}, 
                headers=headers, 
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Overpass API error: {e}", file=sys.stderr)
            return None

async def make_osrm_request(url: str) -> dict[str, Any] | None:
    """Make a request to OSRM API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"OSRM API error: {e}", file=sys.stderr)
            return None

def format_location_result(location: dict) -> dict:
    """Format location search result."""
    return {
        "display_name": location.get("display_name", "Unknown"),
        "name": location.get("name", "Unknown"),
        "type": location.get("type", "Unknown"),
        "coordinates": {
            "latitude": float(location.get("lat", 0)),
            "longitude": float(location.get("lon", 0))
        },
        "address": location.get("address", {}),
        "importance": location.get("importance", 0),
        "place_id": location.get("place_id", "Unknown")
    }

def format_service_result(element: dict) -> dict:
    """Format service search result from Overpass API."""
    tags = element.get("tags", {})
    
    # Get coordinates based on element type
    if element.get("type") == "node":
        coords = {
            "latitude": element.get("lat", 0),
            "longitude": element.get("lon", 0)
        }
    elif element.get("type") == "way":
        # For ways, use center point if available
        center = element.get("center", {})
        coords = {
            "latitude": center.get("lat", 0),
            "longitude": center.get("lon", 0)
        }
    else:
        coords = {"latitude": 0, "longitude": 0}
    
    return {
        "id": element.get("id", "Unknown"),
        "type": element.get("type", "Unknown"),
        "name": tags.get("name", "Unnamed"),
        "coordinates": coords,
        "amenity": tags.get("amenity", "Unknown"),
        "shop": tags.get("shop", ""),
        "cuisine": tags.get("cuisine", ""),
        "opening_hours": tags.get("opening_hours", "Unknown"),
        "phone": tags.get("phone", ""),
        "website": tags.get("website", ""),
        "address": {
            "street": tags.get("addr:street", ""),
            "house_number": tags.get("addr:housenumber", ""),
            "city": tags.get("addr:city", ""),
            "postcode": tags.get("addr:postcode", "")
        },
        "tags": tags
    }

def format_route_result(route_data: dict) -> dict:
    """Format routing result from OSRM API."""
    if not route_data.get("routes"):
        return {"error": "No routes found"}
    
    route = route_data["routes"][0]
    
    return {
        "distance": f"{route.get('distance', 0) / 1000:.2f} km",
        "duration": f"{route.get('duration', 0) / 60:.1f} minutes",
        "geometry": route.get("geometry", ""),
        "legs": [
            {
                "distance": f"{leg.get('distance', 0) / 1000:.2f} km",
                "duration": f"{leg.get('duration', 0) / 60:.1f} minutes",
                "steps": [
                    {
                        "instruction": step.get("maneuver", {}).get("instruction", "Continue"),
                        "distance": f"{step.get('distance', 0)} m",
                        "duration": f"{step.get('duration', 0)} s",
                        "name": step.get("name", ""),
                        "type": step.get("maneuver", {}).get("type", "")
                    }
                    for step in leg.get("steps", [])
                ]
            }
            for leg in route.get("legs", [])
        ]
    }

@mcp.tool()
async def search_location(query: str, limit: int = 5) -> str:
    """Search for locations using OpenStreetMap Nominatim API.
    
    Args:
        query: Search query (e.g. 'Hanoi', 'Times Square New York', 'Phố Hàng Bài')
        limit: Maximum number of results to return (default: 5)
    """
    print(f"search_location called with query: {query}, limit: {limit}", file=sys.stderr)
    
    url = f"{NOMINATIM_API_BASE}/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": min(limit, 50)  # Cap at 50 to avoid overload
    }
    
    data = await make_nominatim_request(url, params)
    
    if not data:
        return "Unable to fetch location data."
    
    if not data:
        return "No locations found for the given query."
    
    results = [format_location_result(location) for location in data]
    
    return json.dumps({
        "query": query,
        "results_count": len(results),
        "locations": results
    }, indent=2, ensure_ascii=False)

@mcp.tool()
async def search_services(service_type: str, latitude: float, longitude: float, radius: int = 1000) -> str:
    """Search for services near a location using Overpass API.
    
    Args:
        service_type: Type of service to search for (e.g. 'restaurant', 'hospital', 'atm', 'fuel', 'cafe')
        latitude: Latitude of the search center
        longitude: Longitude of the search center
        radius: Search radius in meters (default: 1000)
    """
    print(f"search_services called with service_type: {service_type}, lat: {latitude}, lon: {longitude}, radius: {radius}", file=sys.stderr)
    
    # Build Overpass QL query
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="{service_type}"](around:{radius},{latitude},{longitude});
      way["amenity"="{service_type}"](around:{radius},{latitude},{longitude});
      relation["amenity"="{service_type}"](around:{radius},{latitude},{longitude});
    );
    out center;
    """
    
    data = await make_overpass_request(overpass_query)
    
    if not data:
        return "Unable to fetch service data."
    
    elements = data.get("elements", [])
    
    if not elements:
        return f"No {service_type} services found within {radius}m of the specified location."
    
    results = [format_service_result(element) for element in elements]
    
    return json.dumps({
        "service_type": service_type,
        "search_center": {
            "latitude": latitude,
            "longitude": longitude
        },
        "search_radius": f"{radius}m",
        "results_count": len(results),
        "services": results
    }, indent=2, ensure_ascii=False)

@mcp.tool()
async def get_directions(start_lat: float, start_lon: float, end_lat: float, end_lon: float, profile: str = "driving") -> str:
    """Get directions between two points using OSRM API.
    
    Args:
        start_lat: Starting point latitude
        start_lon: Starting point longitude
        end_lat: Destination latitude
        end_lon: Destination longitude
        profile: Transportation profile ('driving', 'walking', 'cycling') - default: 'driving'
    """
    print(f"get_directions called with start: {start_lat},{start_lon}, end: {end_lat},{end_lon}, profile: {profile}", file=sys.stderr)
    
    # Validate profile
    valid_profiles = ["driving", "walking", "cycling"]
    if profile not in valid_profiles:
        return f"Invalid profile. Must be one of: {', '.join(valid_profiles)}"
    
    # Build OSRM URL
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{OSRM_API_BASE}/route/v1/{profile}/{coordinates}"
    
    params = {
        "overview": "full",
        "steps": "true",
        "geometries": "geojson"
    }
    
    # Add params to URL
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{param_string}"
    
    data = await make_osrm_request(full_url)
    
    if not data:
        return "Unable to fetch routing data."
    
    if data.get("code") != "Ok":
        return f"Routing error: {data.get('message', 'Unknown error')}"
    
    result = format_route_result(data)
    
    return json.dumps({
        "start_coordinates": {
            "latitude": start_lat,
            "longitude": start_lon
        },
        "end_coordinates": {
            "latitude": end_lat,
            "longitude": end_lon
        },
        "profile": profile,
        "route": result
    }, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("OpenStreetMap MCP server starting...", file=sys.stderr)
    
    try:
        # Initialize and run the server
        mcp.run(transport='stdio')
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)