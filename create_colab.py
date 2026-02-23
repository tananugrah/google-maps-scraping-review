import json
import os
import re

def create_notebook():
    # 1. Init notebook dict
    nb = {
        "cells": [],
        "metadata": {
            "colab": {
                "name": "Google_Maps_Scraper.ipynb",
                "provenance": []
            },
            "kernelspec": {
                "display_name": "Python 3",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }

    def add_markdown(text):
        nb["cells"].append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in text.split('\n')]
        })

    def add_code(text):
        nb["cells"].append({
            "cell_type": "code",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "source": [line + "\n" for line in text.split('\n')]
        })

    add_markdown("# Google Maps Reviews Scraper\nJalankan sel-sel di bawah ini secara berurutan.")

    add_markdown("## 1. Install Dependencies\nIni akan menginstall playwright, pandas, dan konfigurasi environment asynchronous di Google Colab.")
    add_code("!pip install playwright pandas nest_asyncio\n!playwright install chromium")

    add_markdown("## 2. Setup Asyncio\nGoogle Colab sudah berjalan di dalam loop asyncio, sehingga kita perlu mengaplikasikan `nest_asyncio`.")
    add_code("import nest_asyncio\nnest_asyncio.apply()")

    add_markdown("## 3. Core Script\nBerikut adalah gabungan semua modul dan file konfigurasi (utils, scraper, data processor).")
    
    # Read files
    def read_file(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    selectors_content = read_file('config/selectors.json')
    utils_content = read_file('src/utils.py')
    logger_content = read_file('src/logger_handler.py')
    browser_content = read_file('src/browser_manager.py')
    data_proc_content = read_file('src/data_processor.py')
    scraper_content = read_file('src/google_maps_scraper.py')

    combined_code = []
    combined_code.append('import json')
    combined_code.append('import pandas as pd')
    combined_code.append('import re, time, random, os, logging')
    combined_code.append('from datetime import datetime, timedelta')
    combined_code.append('from playwright.sync_api import sync_playwright')
    combined_code.append(f'\nSELECTORS_JSON = """\n{selectors_content}\n"""')
    combined_code.append('SELECTORS = json.loads(SELECTORS_JSON)\n')

    utils_mod = utils_content.replace('import json', '').replace('import os', '').replace('import random', '').replace('import time', '').replace('from datetime import datetime, timedelta', '').replace('import re', '').replace('from dotenv import load_dotenv', '')
    utils_mod = utils_mod.replace('def load_selectors(filepath="config/selectors.json"):\\n    """Load selectors from JSON file."""\\n    try:\\n        with open(filepath, \\\'r\\\', encoding=\\\'utf-8\\\') as f:\\n            return json.load(f)\\n    except FileNotFoundError:\\n        return {}', 'def load_selectors(filepath=None):\n    return SELECTORS')
    # simpler replace in case spacing differs
    utils_mod = re.sub(r'def load_selectors.*?return \{\}', 'def load_selectors(filepath=None):\n    return SELECTORS', utils_mod, flags=re.DOTALL)
    combined_code.append(utils_mod)

    logger_mod = logger_content.replace('import logging', '').replace('import os', '').replace('from datetime import datetime', '')
    combined_code.append(logger_mod)

    browser_mod = browser_content.replace('from playwright.sync_api import sync_playwright', '').replace('from src.logger_handler import setup_logger', '')
    combined_code.append(browser_mod)

    data_proc_mod = data_proc_content.replace('import pandas as pd', '').replace('import os', '').replace('from datetime import datetime', '').replace('from src.utils import parse_relative_date', '').replace('from src.logger_handler import setup_logger', '')
    combined_code.append(data_proc_mod)

    scraper_mod = scraper_content.replace('import json', '').replace('import os', '').replace('import time', '').replace('import re', '').replace('from src.utils import random_delay, load_selectors, extract_place_id_from_url', '').replace('from src.logger_handler import setup_logger', '')
    combined_code.append(scraper_mod)

    colab_main = """
logger = setup_logger()

def run_scraper(places_list, max_reviews=100):
    os.environ["MAX_REVIEWS"] = str(max_reviews)
    
    logger.info(f"Starting scrape for {len(places_list)} places.")
    browser_mgr = BrowserManager(headless=True)
    processor = DataProcessor()
    
    errors = []
    
    try:
        page = browser_mgr.start_browser()
        scraper = GoogleMapsScraper(page)
        
        for place_name in places_list:
            try:
                logger.info(f"--- Processing: {place_name} ---")
                page.goto("https://www.google.com/maps")
                page.wait_for_load_state("networkidle")
                
                if scraper.search_place(place_name):
                    random_delay(2, 4)
                    details = scraper.get_place_details(place_name)
                    place_id = details.get('place_id')
                    place_url = details.get('place_url', page.url)
                    
                    raw_reviews = scraper.scrape_reviews(place_id, place_name, place_url)
                    processed_reviews = processor.process_reviews(raw_reviews, details)
                    
                    processor.export_to_csv(processed_reviews)
                    logger.info(f"Successfully scraped and exported {len(processed_reviews)} reviews for {place_name}.")
                    
                    if not place_id:
                        logger.warning(f"Note: Place ID was not found for {place_name}, but continuing with name/link.")
                else:
                    logger.warning(f"Place not found: {place_name}")
                    errors.append({"place_name": place_name, "error": "Search failed"})
                
                random_delay(5, 10)
                
                if places_list.index(place_name) % 2 == 1:
                    logger.info("Switching to a fresh browser context.")
                    page = browser_mgr.get_new_context()
                    scraper.page = page

            except Exception as e:
                logger.error(f"Unexpected error processing {place_name}: {e}")
                errors.append({"place_name": place_name, "error": str(e)})

        processor.export_errors(errors)

    finally:
        browser_mgr.close_browser()
        logger.info("Scraping process completed. Silakan periksa file CSV di folder output_data/")
"""
    combined_code.append(colab_main)
    
    add_code("\n".join(combined_code))

    add_markdown("## 4. Jalankan Scraper\nMasukkan nama tempat yang ingin discrape ke dalam list di bawah ini. Atur `max_reviews` sesuai kebutuhan Anda.")
    run_code = """
tempat_yang_ingin_di_scrape = [
    "SiCepat Ekspres Indonesia Pusat",
    "SiCepat Ekspres General Affair Office",
    "SiCepat Ekspres Menteng",
    "SiCepat Ekspres Kemayoran",
    "SiCepat Ekspres Kebayoran Lama"
]

# Jalankan scraper dengan limit 100 review per tempat (gunakan 0 untuk max tanpa henti)
run_scraper(tempat_yang_ingin_di_scrape, max_reviews=100)

# Untuk mendownload/menampilkan file CSV terakhir
import glob
import os
import pandas as pd

list_of_files = glob.glob('output_data/*.csv')
if list_of_files:
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"Data tersimpan di {latest_file}. Anda dapat mendownloadnya dari tab Files di sisi kiri layar.")
    df = pd.read_csv(latest_file)
    display(df.head())
"""
    add_code(run_code)

    with open('Google_Maps_Scraper_Colab.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=2)
    print("Notebook generated.")

if __name__ == '__main__':
    create_notebook()
