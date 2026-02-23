import time
import random
import re
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

def random_delay(min_val=None, max_val=None):
    """Wait for a random duration."""
    min_d = float(os.getenv("MIN_DELAY", 2)) if min_val is None else min_val
    max_d = float(os.getenv("MAX_DELAY", 5)) if max_val is None else max_val
    time.sleep(random.uniform(min_d, max_d))

def parse_relative_date(date_str):
    """Convert relative date strings (e.g., '15 jam lalu', '3 minggu lalu') to YYYY-MM-DD."""
    if not date_str:
        return None
        
    now = datetime.now()
    date_str = date_str.lower()
    
    # Handle 'Baru'
    if 'baru' in date_str:
        return now.strftime("%Y-%m-%d")
        
    number = 0
    match = re.search(r'(\d+)', date_str)
    if match:
        number = int(match.group(1))
        
    if 'jam' in date_str:
        delta = timedelta(hours=number)
    elif 'hari' in date_str:
        delta = timedelta(days=number)
    elif 'minggu' in date_str:
        delta = timedelta(weeks=number)
    elif 'bulan' in date_str:
        delta = timedelta(days=number * 30)
    elif 'tahun' in date_str:
        delta = timedelta(days=number * 365)
    else:
        # Fallback to today if unknown
        return now.strftime("%Y-%m-%d")
        
    target_date = now - delta
    return target_date.strftime("%Y-%m-%d")

def extract_place_id_from_url(url):
    """Extract Place ID from Google Maps URL using regex patterns."""
    # Pattern: /data=!4m...!1s(PLACE_ID)!
    # Example: ChIJ3-Wr1gL1aS4R6ILT4LEMITg or hex format 0x...:0x...
    match = re.search(r'!1s([a-zA-Z0-9_:-]+)(?:!|$)', url)
    if match:
        return match.group(1)
    
    # Fallback search for ChIJ
    match = re.search(r'(ChIJ[a-zA-Z0-9_-]{10,})', url)
    if match:
        return match.group(1)
        
    return None

def load_selectors(file_path="config/selectors.json"):
    """Load selectors from JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading selectors: {e}")
        return {}
