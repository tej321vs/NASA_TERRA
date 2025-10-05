from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging
import os
import re

# --- Flask & API Configuration ---
# Specify a different folder for the animated GIF file.
ANIMATION_FOLDER = 'data_output'
app = Flask(__name__, static_folder=None) # No default static folder
logging.basicConfig(level=logging.INFO)

AIR_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
geolocator = Nominatim(user_agent="3d_satellite_explorer")

# --- Helper Functions ---

def get_coordinates_from_location(location_name):
    """Converts a location name to latitude and longitude."""
    try:
        location = geolocator.geocode(location_name, timeout=5)
        if location:
            return location.latitude, location.longitude
        return None, None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logging.error(f"Geocoding failed for '{location_name}': {e}")
        return None, None

def get_single_location_data(lat, lon):
    """Fetches Air Quality and Weather data for a single point."""
    air_params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["carbon_monoxide", "nitrogen_dioxide", "ozone", 
                    "sulphur_dioxide", "pm10", "pm2_5", "ammonia", 
                    "aerosol_optical_depth", "dust", "uv_index"],
        "domains": "cams_global",
        "timezone": "auto"
    }
    
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "weather_code", "cloud_cover"],
        "temperature_unit": "fahrenheit",
        "timezone": "auto"
    }

    try:
        air_response = requests.get(AIR_API_URL, params=air_params)
        air_response.raise_for_status()
        air_data = air_response.json()

        weather_response = requests.get(WEATHER_API_URL, params=weather_params)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        air_current = air_data["current"]
        air_units = air_data["current_units"]
        weather_current = weather_data["current"]
        weather_units = weather_data["current_units"]

        return {
            'success': True,
            'latitude': lat,
            'longitude': lon,
            'timezone': air_data.get("timezone", "N/A"),
            'co': f"{air_current.get('carbon_monoxide')} {air_units.get('carbon_monoxide', 'N/A')}",
            'no2': f"{air_current.get('nitrogen_dioxide')} {air_units.get('nitrogen_dioxide', 'N/A')}",
            'o3': f"{air_current.get('ozone')} {air_units.get('ozone', 'N/A')}",
            'so2': f"{air_current.get('sulphur_dioxide')} {air_units.get('sulphur_dioxide', 'N/A')}",
            'pm10': f"{air_current.get('pm10')} {air_units.get('pm10', 'N/A')}",
            'pm2_5': f"{air_current.get('pm2_5')} {air_units.get('pm2_5', 'N/A')}",
            'ammonia': f"{air_current.get('ammonia')} {air_units.get('ammonia', 'N/A')}",
            'aerosol_depth': f"{air_current.get('aerosol_optical_depth')} {air_units.get('aerosol_optical_depth', 'N/A')}",
            'dust': f"{air_current.get('dust')} {air_units.get('dust', 'N/A')}",
            'uv_index': f"{air_current.get('uv_index')} {air_units.get('uv_index', 'N/A')}",
            'temp': f"{weather_current.get('temperature_2m')} {weather_units.get('temperature_2m', 'N/A')}",
            'cloud_cover': f"{weather_current.get('cloud_cover')} {weather_units.get('cloud_cover', 'N/A')}",
            'weather_code': weather_current.get('weather_code', 'N/A')
        }

    except Exception as e:
        logging.error(f"Failed to fetch data for {lat}, {lon}: {e}")
        return {
            'success': False,
            'latitude': lat,
            'longitude': lon,
            'error': f"Failed to fetch data: {e}"
        }

# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/get_data', methods=['POST'])
def get_data_endpoint():
    """Handles data requests from the frontend."""
    data = request.json
    location_input = data.get('location_input', '').strip()
    
    results = []
    
    locations = [loc.strip() for loc in location_input.split(';') if loc.strip()]
    
    for loc_str in locations:
        lat, lon = None, None
        
        if re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*$', loc_str):
            try:
                lat, lon = map(float, loc_str.split(','))
            except (ValueError, IndexError):
                pass
        
        if lat is None or lon is None:
            lat, lon = get_coordinates_from_location(loc_str)

        if lat is not None and lon is not None:
            result = get_single_location_data(lat, lon)
            results.append(result)
        else:
            results.append({
                'success': False,
                'location_input': loc_str,
                'error': f'Could not find coordinates for location: {loc_str}'
            })
            
    if not results:
        return jsonify({
            'success': False,
            'error': 'Invalid input: Please provide a valid coordinate pair or location name.'
        }), 400

    return jsonify({'success': True, 'results': results})

# --- New route to serve the animation GIF ---
@app.route('/animation/<path:filename>')
def serve_animation(filename):
    return send_from_directory(ANIMATION_FOLDER, filename)

if __name__ == '__main__':
    print("Running Flask app. Navigate to http://127.0.0.1:5000/")
    # Ensure the folder for the animation exists
    if not os.path.exists(ANIMATION_FOLDER):
        os.makedirs(ANIMATION_FOLDER)
    app.run(debug=True)