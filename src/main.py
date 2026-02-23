import pandas as pd
import os
from src.browser_manager import BrowserManager
from src.google_maps_scraper import GoogleMapsScraper
from src.data_processor import DataProcessor
from src.logger_handler import setup_logger
from src.utils import random_delay

logger = setup_logger()

def main():
    # Load configuration
    input_file = os.getenv("INPUT_FILE", "input_data/nama_tempat.csv")
    gmaps_url = os.getenv("G_MAPS_URL", "https://www.google.com/maps")
    
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return

    # Load input data
    df_input = pd.read_csv(input_file)
    places = df_input['nama_tempat'].tolist()
    
    # Process batch size based on environment variable, default to parsing all
    batch_size_env = os.getenv("MAX_PLACES")
    if batch_size_env and batch_size_env.isdigit():
        batch_size = int(batch_size_env)
        to_process = places[:batch_size]
    else:
        to_process = places # Process all rows from the input CSV
    
    logger.info(f"Starting scrape for {len(to_process)} places.")

    browser_mgr = BrowserManager(headless=(os.getenv("HEADLESS", "true").lower() == "true"))
    processor = DataProcessor()
    
    errors = []

    try:
        page = browser_mgr.start_browser()
        scraper = GoogleMapsScraper(page)

        for place_name in to_process:
            try:
                logger.info(f"--- Processing: {place_name} ---")
                page.goto(gmaps_url)
                page.wait_for_load_state("domcontentloaded")
                
                if scraper.search_place(place_name):
                    # Give it a bit more time to settle the URL
                    random_delay(2, 4)
                    details = scraper.get_place_details(place_name)
                    place_id = details.get('place_id')
                    place_url = details.get('place_url', page.url)
                    
                    # Proceed even if place_id is missing
                    raw_reviews = scraper.scrape_reviews(place_id, place_name, place_url)
                    processed_reviews = processor.process_reviews(raw_reviews, details)
                    
                    # Write progressively to clear memory and secure data
                    processor.export_to_csv(processed_reviews)
                    logger.info(f"Successfully scraped and exported {len(processed_reviews)} reviews for {place_name}.")
                    
                    if not place_id:
                        logger.warning(f"Note: Place ID was not found for {place_name}, but continuing with name/link.")
                else:
                    logger.warning(f"Place not found: {place_name}")
                    errors.append({"place_name": place_name, "error": "Search failed"})
                
                # Random delay between places
                random_delay(5, 10)
                
                # Fresh context every 2 places to avoid detection
                if to_process.index(place_name) % 2 == 1:
                    logger.info("Switching to a fresh browser context.")
                    page = browser_mgr.get_new_context()
                    scraper.page = page

            except Exception as e:
                logger.error(f"Unexpected error processing {place_name}: {e}")
                errors.append({"place_name": place_name, "error": str(e)})

        # Export errors
        processor.export_errors(errors)

    finally:
        browser_mgr.close_browser()
        logger.info("Scraping process completed.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
