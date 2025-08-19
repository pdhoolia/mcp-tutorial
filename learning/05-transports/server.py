# Based on examples/servers/simple-streamablehttp
# Real-world HTTP server using OpenWeatherMap API
import logging
import os
from datetime import datetime, timedelta
from typing import Dict
from mcp.server.fastmcp import FastMCP
import httpx
import anyio

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Create server with HTTP support
mcp = FastMCP(
    "Real Weather HTTP Service",
    host="localhost",
    port=8000
)

# Configuration
# To use this server, you need a free API key from OpenWeatherMap:
# 1. Sign up at https://openweathermap.org/api
# 2. Get your API key from the account page
# 3. Set it as an environment variable: export OPENWEATHER_API_KEY=your_key_here
API_KEY = os.getenv("OPENWEATHER_API_KEY", "demo")
BASE_URL = "https://api.openweathermap.org/data/2.5"

# Cache for weather data (city -> (data, timestamp))
weather_cache: Dict[str, tuple[dict, datetime]] = {}
CACHE_DURATION = timedelta(minutes=10)  # Cache for 10 minutes

async def fetch_weather_from_api(city: str) -> dict:
    """Fetch real weather data from OpenWeatherMap API"""
    if API_KEY == "demo":
        # Return demo data if no API key is set
        return {
            "temperature": 20.0,
            "feels_like": 19.0,
            "humidity": 65,
            "pressure": 1013,
            "condition": "partly cloudy",
            "description": "Demo mode - Set OPENWEATHER_API_KEY for real data",
            "wind_speed": 5.5,
            "wind_direction": 180,
            "visibility": 10000,
            "clouds": 40,
            "sunrise": "06:30",
            "sunset": "18:45",
            "city": city,
            "country": "XX"
        }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/weather",
                params={
                    "q": city,
                    "appid": API_KEY,
                    "units": "metric"  # Use Celsius
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse the API response
            return {
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"],
                "wind_direction": data["wind"].get("deg", 0),
                "visibility": data.get("visibility", 0),
                "clouds": data["clouds"]["all"],
                "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
                "city": data["name"],
                "country": data["sys"]["country"],
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"City '{city}' not found")
            elif e.response.status_code == 401:
                raise ValueError("Invalid API key. Please check your OPENWEATHER_API_KEY")
            else:
                raise ValueError(f"API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching weather for {city}: {e}")
            raise ValueError(f"Failed to fetch weather: {str(e)}")

@mcp.tool()
async def get_weather(city: str, force_refresh: bool = False) -> dict:
    """
    Get current weather for a city.
    
    Args:
        city: Name of the city (e.g., "London", "New York", "Tokyo")
        force_refresh: Skip cache and fetch fresh data
    
    Returns:
        Weather data including temperature, conditions, wind, etc.
    """
    # Check cache first (unless force_refresh is True)
    if not force_refresh and city.lower() in weather_cache:
        cached_data, timestamp = weather_cache[city.lower()]
        if datetime.now() - timestamp < CACHE_DURATION:
            logger.info(f"Returning cached weather for {city}")
            cached_data["cached"] = True
            cached_data["cache_age_seconds"] = (datetime.now() - timestamp).total_seconds()
            return cached_data
    
    # Fetch fresh data
    logger.info(f"Fetching fresh weather data for {city}")
    weather_data = await fetch_weather_from_api(city)
    
    # Update cache
    weather_cache[city.lower()] = (weather_data.copy(), datetime.now())
    
    # Send notification to connected clients (only works in FastMCP context)
    try:
        ctx = mcp.request_context
        await ctx.session.send_log_message(
            level="info",
            data=f"Weather fetched for {city}: {weather_data['temperature']}°C, {weather_data['condition']}",
            logger="weather_fetch"
        )
        
        # Notify about resource update
        await ctx.session.send_resource_updated(uri=f"weather://{city.lower()}")
        await ctx.session.send_resource_updated(uri="weather://recent")
    except (AttributeError, LookupError):
        # request_context not available in this context
        logger.info(f"Weather fetched for {city}: {weather_data['temperature']}°C, {weather_data['condition']}")
    
    weather_data["cached"] = False
    return weather_data

@mcp.tool()
async def get_forecast(city: str, days: int = 5) -> dict:
    """
    Get weather forecast for a city.
    
    Args:
        city: Name of the city
        days: Number of days to forecast (1-5)
    
    Returns:
        Weather forecast data
    """
    if days < 1 or days > 5:
        raise ValueError("Days must be between 1 and 5")
    
    if API_KEY == "demo":
        # Return demo forecast
        return {
            "city": city,
            "forecast": [
                {
                    "date": (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "temperature_min": 15 + i,
                    "temperature_max": 25 + i,
                    "condition": ["sunny", "cloudy", "rainy", "partly cloudy", "clear"][i % 5],
                    "precipitation_chance": (i * 20) % 100
                }
                for i in range(days)
            ],
            "message": "Demo forecast - Set OPENWEATHER_API_KEY for real data"
        }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/forecast",
                params={
                    "q": city,
                    "appid": API_KEY,
                    "units": "metric",
                    "cnt": days * 8  # API returns 8 forecasts per day (3-hour intervals)
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Group forecasts by day
            daily_forecasts = {}
            for item in data["list"]:
                date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
                if date not in daily_forecasts:
                    daily_forecasts[date] = {
                        "temps": [],
                        "conditions": [],
                        "rain": 0
                    }
                daily_forecasts[date]["temps"].append(item["main"]["temp"])
                daily_forecasts[date]["conditions"].append(item["weather"][0]["main"])
                daily_forecasts[date]["rain"] += item.get("rain", {}).get("3h", 0)
            
            # Calculate daily summaries
            forecast = []
            for date, day_data in list(daily_forecasts.items())[:days]:
                forecast.append({
                    "date": date,
                    "temperature_min": min(day_data["temps"]),
                    "temperature_max": max(day_data["temps"]),
                    "condition": max(set(day_data["conditions"]), key=day_data["conditions"].count),
                    "precipitation_mm": round(day_data["rain"], 1)
                })
            
            return {
                "city": data["city"]["name"],
                "country": data["city"]["country"],
                "forecast": forecast
            }
        except Exception as e:
            logger.error(f"Error fetching forecast for {city}: {e}")
            raise ValueError(f"Failed to fetch forecast: {str(e)}")

@mcp.tool()
async def compare_weather(cities: list[str]) -> dict:
    """
    Compare weather across multiple cities.
    
    Args:
        cities: List of city names to compare
    
    Returns:
        Comparison of weather data across cities
    """
    if len(cities) > 10:
        raise ValueError("Maximum 10 cities for comparison")
    
    results = {}
    errors = {}
    
    # Fetch weather for all cities concurrently
    async def fetch_city(city: str):
        try:
            return city, await get_weather(city)
        except Exception as e:
            return city, {"error": str(e)}
    
    # Use anyio to run fetches concurrently
    async with anyio.create_task_group() as tg:
        tasks = []
        for city in cities:
            tasks.append(tg.start_soon(fetch_city, city))
    
    # Collect results
    for city in cities:
        try:
            weather_data = await get_weather(city)
            results[city] = weather_data
        except Exception as e:
            errors[city] = str(e)
    
    # Calculate statistics
    valid_cities = [city for city in results if "error" not in results[city]]
    
    comparison = {
        "cities": results,
        "errors": errors,
        "summary": {}
    }
    
    if valid_cities:
        temps = [results[city]["temperature"] for city in valid_cities]
        comparison["summary"] = {
            "warmest": max(valid_cities, key=lambda c: results[c]["temperature"]),
            "coolest": min(valid_cities, key=lambda c: results[c]["temperature"]),
            "average_temperature": round(sum(temps) / len(temps), 1),
            "temperature_range": round(max(temps) - min(temps), 1)
        }
    
    return comparison

@mcp.resource("weather://recent")
async def get_recent_weather() -> str:
    """Get recently fetched weather data from cache"""
    if not weather_cache:
        return "No weather data in cache. Use get_weather tool to fetch data."
    
    recent = []
    for city, (data, timestamp) in weather_cache.items():
        age_seconds = (datetime.now() - timestamp).total_seconds()
        recent.append(f"{city.title()}: {data['temperature']}°C, {data['condition']} (cached {int(age_seconds)}s ago)")
    
    return "\n".join(recent)

@mcp.resource("weather://{city}")
async def get_city_weather_resource(city: str) -> str:
    """Get weather data for a specific city from cache"""
    city_lower = city.lower()
    if city_lower not in weather_cache:
        return f"No cached data for {city}. Use get_weather tool to fetch data."
    
    data, timestamp = weather_cache[city_lower]
    age_seconds = (datetime.now() - timestamp).total_seconds()
    
    return f"""Weather for {data['city']}, {data['country']}:
Temperature: {data['temperature']}°C (feels like {data['feels_like']}°C)
Condition: {data['condition']} - {data['description']}
Humidity: {data['humidity']}%
Wind: {data['wind_speed']} m/s from {data['wind_direction']}°
Pressure: {data['pressure']} hPa
Visibility: {data['visibility']/1000:.1f} km
Cloud cover: {data['clouds']}%
Sunrise: {data['sunrise']} / Sunset: {data['sunset']}
(Cached {int(age_seconds)} seconds ago)"""

@mcp.prompt(title="Weather Report")
async def weather_report(cities: str) -> str:
    """Generate a weather report prompt for multiple cities
    
    Args:
        cities: Comma-separated list of city names (e.g., "London,Paris,Tokyo")
    """
    # Split the comma-separated string into a list
    cities_list = [city.strip() for city in cities.split(',')]
    weather_data = await compare_weather(cities_list)
    
    report = "Please provide a natural language weather report based on this data:\n\n"
    
    for city, data in weather_data["cities"].items():
        if "error" not in data:
            report += f"{city}: {data['temperature']}°C, {data['condition']}, "
            report += f"humidity {data['humidity']}%, wind {data['wind_speed']} m/s\n"
    
    if weather_data["summary"]:
        report += f"\nWarmest city: {weather_data['summary']['warmest']}\n"
        report += f"Coolest city: {weather_data['summary']['coolest']}\n"
        report += f"Temperature range: {weather_data['summary']['temperature_range']}°C\n"
    
    report += "\nPlease create a conversational weather summary highlighting key differences and notable conditions."
    
    return report

if __name__ == "__main__":
    import sys
    # Determine transport mode from command line argument
    # Valid options: stdio, sse, streamable-http
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    
    print(f"Weather API Mode: {'Real' if API_KEY != 'demo' else 'Demo'}")
    if API_KEY == "demo":
        print("To use real weather data:")
        print("1. Sign up at https://openweathermap.org/api")
        print("2. Export your API key: export OPENWEATHER_API_KEY=your_key_here")
    
    # Handle different transport modes
    if transport == "sse":
        print(f"\nStarting SSE server on http://localhost:8000")
        print("\nSSE endpoints:")
        print("  - GET  /sse        - SSE event stream (returns session_id)")
        print("  - POST /messages   - Send JSON-RPC messages (requires session_id)")
        print("\nTo test, run the SSE client in another terminal:")
        print("  uv run python learning/08_c_test_sse_client.py")
        print("\nOr use curl (more complex):")
        print("  1. curl -N http://localhost:8000/sse")
        print("     (Keep this running, note the session_id from endpoint event)")
        print("  2. In another terminal, send messages with the session_id")
        mcp.run(transport="sse")
    elif transport == "streamable-http":
        print(f"\nStarting Streamable HTTP server on http://localhost:8000")
        print("\nTest with: learning/05-transports/client_streamable.http")
        mcp.run(transport="streamable-http")
    else:
        print("\nStarting in stdio mode")
        print("Test with: uv run mcp dev learning/05-transports/server.py stdio")
        mcp.run(transport="stdio")