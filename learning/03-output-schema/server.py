# Based on examples/fastmcp/weather_structured.py
from datetime import datetime
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather Service")

class WeatherData(BaseModel):
    """Structured weather response"""
    temperature: float = Field(description="Temperature in Celsius")
    humidity: float = Field(description="Humidity percentage")
    condition: str = Field(description="Weather condition")
    timestamp: datetime = Field(default_factory=datetime.now)

@mcp.tool()
def get_weather(city: str) -> WeatherData:
    """Get current weather for a city"""
    # Mock data - in production, call a weather API
    weather_data = {
        "london": WeatherData(temperature=15.5, humidity=70, condition="cloudy"),
        "paris": WeatherData(temperature=18.2, humidity=65, condition="sunny"),
        "tokyo": WeatherData(temperature=22.1, humidity=80, condition="rainy"),
    }
    
    city_lower = city.lower()
    if city_lower in weather_data:
        return weather_data[city_lower]
    
    # Default weather for unknown cities
    return WeatherData(
        temperature=20.0,
        humidity=60,
        condition="partly cloudy"
    )

@mcp.tool()
def compare_weather(cities: list[str]) -> dict[str, WeatherData]:
    """Compare weather across multiple cities"""
    return {city: get_weather(city) for city in cities}

if __name__ == "__main__":
    mcp.run()