import pandas as pd
import os
from datetime import datetime
from src.utils import parse_relative_date
from src.logger_handler import setup_logger

logger = setup_logger()

class DataProcessor:
    def __init__(self, output_folder="output_data"):
        self.output_folder = output_folder
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def process_reviews(self, raw_reviews, place_details=None):
        """Cleans and formats review data."""
        if place_details is None:
            place_details = {}
            
        processed = []
        for review in raw_reviews:
            # Parse date
            parsed_date = parse_relative_date(review.get('tanggal_raw'))
            
            # Filter by date (April 2025 onwards)
            if parsed_date and parsed_date < "2025-04-01":
                continue
                
            row = {
                'place_id': review.get('place_id'),
                'place_url': review.get('place_url'),
                'nama_tempat': review.get('nama_tempat'),
                'latitude': place_details.get('latitude'),
                'longitude': place_details.get('longitude'),
                'description': place_details.get('description'),
                'is_spending': place_details.get('is_spending'),
                'reviews': place_details.get('ulasan_total'),
                'competitors': place_details.get('competitors'),
                'website': place_details.get('website'),
                'can_claim': place_details.get('can_claim'),
                'owner': place_details.get('owner'),
                'featured_image': place_details.get('featured_image'),
                'main_category': place_details.get('main_category'),
                'categories': place_details.get('categories'),
                'total_rating': place_details.get('rating_total'),
                'total_reviews': place_details.get('ulasan_total'),
                'review_rating': review.get('rating_ulasan'),
                'workday_timing': place_details.get('workday_timing'),
                'is_temporarily_closed': place_details.get('is_temporarily_closed'),
                'is_permanently_closed': place_details.get('is_permanently_closed'),
                'closed_on': place_details.get('closed_on'),
                'phone': place_details.get('telepon'),
                'address': place_details.get('alamat'),
                'review_keywords': place_details.get('review_keywords'),
                'author_name': review.get('author_name', '').strip(),
                'tanggal_review': parsed_date,
                'isi_review': review.get('isi_review', '').strip(),
                'balasan_pemilik': review.get('balasan_pemilik', '').strip(),
                'tanggal_balasan': parse_relative_date(review.get('tanggal_balasan_raw')),
                'review_id': review.get('review_id'),
                'ingestion_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            processed.append(row)
            
        return processed

    def export_to_csv(self, data, name_prefix="gmaps_scrape", mode="a"):
        """Exports data to a CSV file."""
        if not data:
            logger.warning("No data to export.")
            return None
            
        filename = f"{name_prefix}_{self.session_timestamp}.csv"
        filepath = os.path.join(self.output_folder, filename)
        
        df = pd.DataFrame(data)
        # Ensure correct column order
        cols = [
            'place_id', 'place_url', 'nama_tempat', 'latitude', 'longitude', 'address', 'description', 'is_spending',
            'reviews', 'total_reviews', 'competitors', 'website', 'can_claim', 'owner', 'featured_image',
            'main_category', 'categories', 'total_rating', 'review_rating', 'workday_timing', 'is_temporarily_closed',
            'is_permanently_closed', 'closed_on', 'phone', 'review_id', 'review_keywords',
            'author_name', 'tanggal_review', 'isi_review', 'balasan_pemilik', 'tanggal_balasan', 'ingestion_time'
        ]
        
        # Keep only columns that actually exist to prevent KeyError
        existing_cols = [c for c in cols if c in df.columns]
        df = df[existing_cols]
        
        write_header = not os.path.exists(filepath) or mode == 'w'
        df.to_csv(filepath, index=False, mode=mode, header=write_header, encoding='utf-8-sig')
        logger.info(f"Data exported to {filepath}")
        return filepath

    def export_errors(self, errors):
        """Exports errors to a separate CSV."""
        if not errors:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"error_report_{timestamp}.csv"
        filepath = os.path.join(self.output_folder, filename)
        
        df = pd.DataFrame(errors)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"Error report exported to {filepath}")
        return filepath
