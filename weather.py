from typing import Any
import httpx
import json
import os
from mcp.server.fastmcp import FastMCP
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Initialize FastMCP server
mcp = FastMCP("weather")

print("Enhanced Weather server initialized", file=sys.stderr)

# Constants
NWS_API_BASE = "https://api.weather.gov"
OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
USER_AGENT = "weather-app/1.0"

# Get OpenWeatherMap API key from environment
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"NWS API error: {e}", file=sys.stderr)
            return None

async def make_openweather_request(url: str, params: dict) -> dict[str, Any] | None:
    """Make a request to OpenWeatherMap API with proper error handling."""
    if not OPENWEATHER_API_KEY:
        print("OpenWeatherMap API key not found", file=sys.stderr)
        return None
    
    params["appid"] = OPENWEATHER_API_KEY
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"OpenWeatherMap API error: {e}", file=sys.stderr)
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

def format_current_weather(data: dict, units: str) -> dict:
    """Format current weather data from OpenWeatherMap."""
    temp_unit = "°C" if units == "metric" else "°F"
    speed_unit = "m/s" if units == "metric" else "mph"
    
    try:
        weather = {
            "location": {
                "name": data.get("name", "Unknown"),
                "country": data.get("sys", {}).get("country", "Unknown"),
                "coordinates": {
                    "latitude": data.get("coord", {}).get("lat", 0),
                    "longitude": data.get("coord", {}).get("lon", 0)
                }
            },
            "current": {
                "temperature": f"{data.get('main', {}).get('temp', 0)}{temp_unit}",
                "feels_like": f"{data.get('main', {}).get('feels_like', 0)}{temp_unit}",
                "humidity": f"{data.get('main', {}).get('humidity', 0)}%",
                "pressure": f"{data.get('main', {}).get('pressure', 0)} hPa",
                "wind": {
                    "speed": f"{data.get('wind', {}).get('speed', 0)} {speed_unit}",
                    "direction": data.get('wind', {}).get('deg', 0)
                },
                "weather": {
                    "main": data.get('weather', [{}])[0].get('main', "Unknown"),
                    "description": data.get('weather', [{}])[0].get('description', "Unknown"),
                    "icon": data.get('weather', [{}])[0].get('icon', "Unknown")
                },
                "visibility": f"{data.get('visibility', 0) / 1000} km",
                "cloudiness": f"{data.get('clouds', {}).get('all', 0)}%",
                "sunrise": data.get('sys', {}).get('sunrise', 0),
                "sunset": data.get('sys', {}).get('sunset', 0)
            }
        }
        
        if 'rain' in data:
            weather['current']['rain'] = {
                "1h": f"{data['rain'].get('1h', 0)} mm"
            }
        
        if 'snow' in data:
            weather['current']['snow'] = {
                "1h": f"{data['snow'].get('1h', 0)} mm"
            }
        
        return weather
    except Exception as e:
        print(f"Error formatting weather data: {e}", file=sys.stderr)
        return {"error": "Error formatting weather data"}

def format_forecast(data: dict, days: int, units: str) -> dict:
    """Format forecast data from OpenWeatherMap."""
    temp_unit = "°C" if units == "metric" else "°F"
    speed_unit = "m/s" if units == "metric" else "mph"
    
    try:
        city_data = data.get("city", {})
        forecast_list = data.get("list", [])
        
        daily_forecasts = {}
        
        for item in forecast_list:
            date = item.get("dt_txt", "").split(" ")[0]
            
            if date not in daily_forecasts:
                daily_forecasts[date] = []
            
            daily_forecasts[date].append({
                "time": item.get("dt_txt", "").split(" ")[1],
                "temperature": f"{item.get('main', {}).get('temp', 0)}{temp_unit}",
                "feels_like": f"{item.get('main', {}).get('feels_like', 0)}{temp_unit}",
                "min_temp": f"{item.get('main', {}).get('temp_min', 0)}{temp_unit}",
                "max_temp": f"{item.get('main', {}).get('temp_max', 0)}{temp_unit}",
                "humidity": f"{item.get('main', {}).get('humidity', 0)}%",
                "pressure": f"{item.get('main', {}).get('pressure', 0)} hPa",
                "weather": {
                    "main": item.get('weather', [{}])[0].get('main', "Unknown"),
                    "description": item.get('weather', [{}])[0].get('description', "Unknown"),
                    "icon": item.get('weather', [{}])[0].get('icon', "Unknown")
                },
                "wind": {
                    "speed": f"{item.get('wind', {}).get('speed', 0)} {speed_unit}",
                    "direction": item.get('wind', {}).get('deg', 0)
                },
                "cloudiness": f"{item.get('clouds', {}).get('all', 0)}%"
            })
        
        forecast_dates = list(daily_forecasts.keys())[:days]
        limited_forecasts = {date: daily_forecasts[date] for date in forecast_dates if date in daily_forecasts}
        
        return {
            "location": {
                "name": city_data.get("name", "Unknown"),
                "country": city_data.get("country", "Unknown"),
                "coordinates": {
                    "latitude": city_data.get("coord", {}).get("lat", 0),
                    "longitude": city_data.get("coord", {}).get("lon", 0)
                }
            },
            "forecast": limited_forecasts
        }
    except Exception as e:
        print(f"Error formatting forecast data: {e}", file=sys.stderr)
        return {"error": "Error formatting forecast data"}

# NWS Tools (US only)
@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    print(f"get_alerts called with state: {state}", file=sys.stderr)
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location using NWS (US only).

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    print(f"get_forecast called with lat: {latitude}, lon: {longitude}", file=sys.stderr)
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

# OpenWeatherMap Tools (Global)
@mcp.tool()
async def get_current_weather(city: str, units: str = "metric") -> str:
    """Get current weather for a city using OpenWeatherMap.

    Args:
        city: City name (e.g. 'London', 'New York')
        units: Units of measurement ('metric' or 'imperial')
    """
    print(f"get_current_weather called with city: {city}, units: {units}", file=sys.stderr)
    
    if not OPENWEATHER_API_KEY:
        return "OpenWeatherMap API key not configured. Please set OPENWEATHER_API_KEY environment variable."
    
    url = f"{OPENWEATHER_API_BASE}/weather"
    params = {
        "q": city,
        "units": units
    }
    
    data = await make_openweather_request(url, params)
    
    if not data:
        return "Unable to fetch current weather data."
    
    result = format_current_weather(data, units)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_weather_forecast(city: str, days: int = 3, units: str = "metric") -> str:
    """Get weather forecast for a city using OpenWeatherMap.

    Args:
        city: City name (e.g. 'London', 'New York')
        days: Number of days (1-5)
        units: Units of measurement ('metric' or 'imperial')
    """
    print(f"get_weather_forecast called with city: {city}, days: {days}, units: {units}", file=sys.stderr)
    
    if not OPENWEATHER_API_KEY:
        return "OpenWeatherMap API key not configured. Please set OPENWEATHER_API_KEY environment variable."
    
    if days < 1 or days > 5:
        return "Days must be between 1 and 5."
    
    url = f"{OPENWEATHER_API_BASE}/forecast"
    params = {
        "q": city,
        "units": units
    }
    
    data = await make_openweather_request(url, params)
    
    if not data:
        return "Unable to fetch forecast data."
    
    result = format_forecast(data, days, units)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_weather_by_coordinates(latitude: float, longitude: float, units: str = "metric") -> str:
    """Get current weather by coordinates using OpenWeatherMap.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
        units: Units of measurement ('metric' or 'imperial')
    """
    print(f"get_weather_by_coordinates called with lat: {latitude}, lon: {longitude}, units: {units}", file=sys.stderr)
    
    if not OPENWEATHER_API_KEY:
        return "OpenWeatherMap API key not configured. Please set OPENWEATHER_API_KEY environment variable."
    
    url = f"{OPENWEATHER_API_BASE}/weather"
    params = {
        "lat": latitude,
        "lon": longitude,
        "units": units
    }
    
    data = await make_openweather_request(url, params)
    
    if not data:
        return "Unable to fetch weather data by coordinates."
    
    result = format_current_weather(data, units)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    
    
    if OPENWEATHER_API_KEY:
        print("OpenWeatherMap API key found - global weather features enabled", file=sys.stderr)
    else:
        print("OpenWeatherMap API key not found - only US NWS features available", file=sys.stderr)
    
    try:
        # Initialize and run the server
        mcp.run(transport='stdio')
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)