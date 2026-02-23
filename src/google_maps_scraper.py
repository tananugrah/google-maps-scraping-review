import time
import random
import os
import re
from src.utils import random_delay, load_selectors, extract_place_id_from_url
from src.logger_handler import setup_logger

logger = setup_logger()

class GoogleMapsScraper:
    def __init__(self, page):
        self.page = page
        self.selectors = load_selectors()

    def search_place(self, name):
        """Searches for a place and navigates to its details."""
        try:
            logger.info(f"Searching for: {name}")
            search_input = self.selectors['search']['input']
            
            # Type with human-like delay
            self.page.fill(search_input, "")
            self.page.type(search_input, name, delay=random.randint(50, 150))
            self.page.press(search_input, "Enter")
            
            # Wait for search results or direct redirect
            self.page.wait_for_load_state("networkidle")
            
            # Use a loop to wait for either results or detail page
            for _ in range(5):
                if self.page.locator(self.selectors['search']['recommendation_item']).count() > 0:
                    logger.info("Multiple results found. Selecting the first one.")
                    self.page.click(self.selectors['search']['recommendation_item'] + " " + self.selectors['search']['recommendation_link'])
                    self.page.wait_for_load_state("networkidle")
                    random_delay(2, 4)
                    break
                elif "!1s" in self.page.url or "ChIJ" in self.page.url:
                    break
                random_delay(1, 2)
            
            return True
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return False

    def _extract_from_html(self, html_content, pattern, group=1, default=None):
        """Helper function to extract data from HTML using regex."""
        try:
            match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(group)
            return default
        except Exception as e:
            logger.debug(f"Error extracting with pattern: {e}")
            return default

    def _get_place_id(self, html_content, metadata=None):
        """Extracts the Google Place ID."""
        if metadata and metadata.get('place_id'):
            return metadata['place_id']

        # Fall back to searching HTML for ChIJ pattern
        place_id = self._extract_from_html(html_content, r'(ChIJ[a-zA-Z0-9_-]{20,})', 1)
        return place_id

    def get_place_details(self, name):
        """Extracts basic info about the place."""
        page_html = self.page.content()
        place_id = self._get_place_id(page_html)
        if not place_id:
            place_id = extract_place_id_from_url(self.page.url)

        details = {
            'place_id': place_id,
            'place_url': self.page.url,
            'nama_tempat': name,
            'rating_total': None,
            'ulasan_total': None,
            'alamat': None,
            'website': None,
            'telepon': None,
            'description': None,
            'is_spending': False,
            'competitors': None,
            'can_claim': False,
            'owner': None,
            'featured_image': None,
            'main_category': None,
            'categories': None,
            'workday_timing': None,
            'is_temporarily_closed': False,
            'is_permanently_closed': False,
            'closed_on': None,
            'review_keywords': None
        }
        
        try:
            sel = self.selectors['place_details']
            
            # Wait for any detail element to ensure page is loaded
            try:
                self.page.wait_for_selector(sel['name'], timeout=10000)
            except:
                logger.warning("Main name element not found within timeout.")

            # Name check (verify redirect)
            if self.page.locator(sel['name']).count() > 0:
                actual_name = self.page.text_content(sel['name'])
                details['actual_name'] = actual_name.strip() if actual_name else name
            else:
                details['actual_name'] = name
            
            # Rating
            rating_loc = self.page.locator(sel['rating'])
            if rating_loc.count() > 0:
                rating_text = rating_loc.first.text_content()
                details['rating_total'] = rating_text.strip().replace(',', '.') if rating_text else None
                
            # Reviews count
            reviews_count_loc = self.page.locator(sel['reviews_count'])
            if reviews_count_loc.count() > 0:
                # Try getting from aria-label first as it's cleaner
                aria_label = reviews_count_loc.first.get_attribute("aria-label")
                if aria_label:
                    count = "".join(filter(str.isdigit, aria_label))
                    details['ulasan_total'] = int(count) if count else 0
                else:
                    reviews_count_text = reviews_count_loc.first.text_content()
                    if reviews_count_text:
                        count = "".join(filter(str.isdigit, reviews_count_text))
                        details['ulasan_total'] = int(count) if count else 0
                
            # Optional info - Use both text_content and aria-label fallbacks
            for key, selector in [('alamat', 'address'), ('website', 'website'), ('telepon', 'phone')]:
                loc = self.page.locator(sel[selector])
                if loc.count() > 0:
                    # Prefer text inside if available, else aria-label
                    txt = loc.first.text_content()
                    if not txt or len(txt.strip()) < 5: # Some buttons only have icons/aria-label
                        aria = loc.first.get_attribute("aria-label")
                        if aria:
                            # Clean "Alamat: ", "Telepon: ", etc.
                            details[key] = aria.split(":")[-1].strip()
                        else:
                            details[key] = txt.strip() if txt else None
                    else:
                        details[key] = txt.strip()
            
            # New Field Extractions
            
            # Rating & Review Count
            rating_loc = self.page.locator("div.F7nice")
            if rating_loc.count() > 0:
                 r_text = rating_loc.first.text_content().strip()
                 # Expected format: "4.5(2,530)" or "4.5(2.530)"
                 # rating_match Example text: 4.8(2,530)
                 # Adjust regex to handle whitespace and ensure first group is rating, second group is count
                 rating_match = re.search(r"([\d\,]+[\.\,]?[\d]*)\s*\(([\d\,\.]+)\)", r_text)
                 if rating_match:
                     details['rating_total'] = rating_match.group(1).replace(',', '.') # Normalize rating to float format
                     details['ulasan_total'] = rating_match.group(2).replace('.', '').replace(',', '') # Normalize count
                 else:
                     # Fallback if regex fails but rating exists
                     details['rating_total'] = r_text
            
            # Description
            desc_loc = self.page.locator("div.PYvSYb")
            if desc_loc.count() > 0:
                details['description'] = desc_loc.first.text_content().strip()
                
            # Is Spending (Sponsored)
            details['is_spending'] = self.page.locator("div:has-text('Disponsori')").count() > 0
            
            # Can Claim
            details['can_claim'] = self.page.locator("a[data-item-id='merchant']").count() > 0
            
            # Categories
            cat_loc = self.page.locator("button.DkEaL")
            if cat_loc.count() > 0:
                cats = [c.strip() for c in cat_loc.all_text_contents() if c.strip()]
                if cats:
                    details['main_category'] = cats[0]
                    details['categories'] = ", ".join(cats)
                    
            # Featured Image
            img_loc = self.page.locator("button.aoRNLd img")
            if img_loc.count() > 0:
                details['featured_image'] = img_loc.first.get_attribute("src")
                
            # Closure status
            details['is_temporarily_closed'] = self.page.locator("span:has-text('Tutup sementara')").count() > 0
            details['is_permanently_closed'] = self.page.locator("span:has-text('Tutup permanen')").count() > 0
            
            # Workday Timing (attempts to extract the aria-label of the schedule dropdown)
            timing_loc = self.page.locator("div[aria-label*='Sembunyikan jam buka'], div[aria-label*='Tampilkan jam buka']")
            if timing_loc.count() > 0:
                 details['workday_timing'] = timing_loc.first.get_attribute("aria-label")
            
            # --- XPath Fallbacks for Details ---
            xf = self.selectors.get('xpath_fallbacks', {})
            if not details.get('alamat') and xf.get('address'):
                details['alamat'] = self.page.text_content(xf['address']).strip() if self.page.locator(xf['address']).count() > 0 else details['alamat']
            if not details.get('website') and xf.get('website'):
                details['website'] = self.page.text_content(xf['website']).strip() if self.page.locator(xf['website']).count() > 0 else details['website']
            if not details.get('telepon') and xf.get('phone'):
                details['telepon'] = self.page.text_content(xf['phone']).strip() if self.page.locator(xf['phone']).count() > 0 else details['telepon']
            if not details.get('rating_total') and xf.get('rating'):
                details['rating_total'] = self.page.text_content(xf['rating']).strip() if self.page.locator(xf['rating']).count() > 0 else details['rating_total']
            if not details.get('ulasan_total') and xf.get('reviews_count'):
                count_txt = self.page.text_content(xf['reviews_count'])
                if count_txt:
                    count = "".join(filter(str.isdigit, count_txt))
                    details['ulasan_total'] = int(count) if count else details['ulasan_total']
            
            logger.info(f"Extracted details for: {details['actual_name']}")
            return details
        except Exception as e:
            logger.warning(f"Some details could not be extracted: {e}")
            return details

    def scrape_reviews(self, place_id, name, place_url=""):
        """Navigates to reviews tab and scrapes them with infinite scroll."""
        reviews = []
        try:
            sel = self.selectors['reviews']
            
            # Click reviews tab - Try both aria-label and text
            tab_locators = [
                self.page.locator(sel['tab_button']),
                self.page.locator("button:has-text('Ulasan')"),
                self.page.locator("div[role='tab']:has-text('Ulasan')")
            ]
            
            tab_clicked = False
            for loc in tab_locators:
                if loc.count() > 0 and loc.first.is_visible():
                    logger.info(f"Clicking reviews tab using locator: {loc}")
                    loc.first.click()
                    tab_clicked = True
                    break
            
            if not tab_clicked:
                logger.error("Reviews tab not found or not clickable.")
                return []
            
            # Use explicit delay instead of networkidle which hangs on Google Maps
            random_delay(3, 5)
                
            # Sort by newest
            sort_btn = self.page.locator(sel['sort_button'])
            xf = self.selectors.get('xpath_fallbacks', {})
            
            if sort_btn.count() == 0 and xf.get('sort_button'):
                sort_btn = self.page.locator(xf['sort_button'])
                
            if sort_btn.count() > 0 and sort_btn.first.is_visible():
                logger.info("Opening sort menu.")
                sort_btn.first.click()
                random_delay(2, 3)
                
                # Wait for menu items and try multiple strategies for 'Terbaru'
                try:
                    self.page.wait_for_selector("div[role='menuitemradio'], div[role='menuitem']", timeout=5000)
                except:
                    pass
                    
                newest_opt = self.page.locator(sel['sort_newest'])
                if newest_opt.count() == 0:
                    newest_opt = self.page.locator("div[role='menuitemradio']:has-text('Terbaru'), div[role='menuitem']:has-text('Terbaru')")
                if newest_opt.count() == 0:
                    newest_opt = self.page.locator("text=Terbaru")
                if newest_opt.count() == 0 and xf.get('sort_newest'):
                    newest_opt = self.page.locator(xf['sort_newest'])
                    
                if newest_opt.count() > 0:
                    logger.info(f"Selecting 'Terbaru' sort option.")
                    newest_opt.first.click()
                    # Wait for reviews to refresh using manual delay rather than networkidle
                    random_delay(4, 6)
                else:
                    logger.warning("Sort option 'Terbaru' not found.")
            else:
                logger.warning("Sort button not found.")
                
            # Infinite scroll logic - Use a more robust way to find the scrollable container
            # In GMap, the scrollable list is typically the div with tabindex="-1" inside the main role.
            container_locator = self.page.locator("div.m6QErb.DxyBCb.kA9KIf.dS8AEf[tabindex='-1']").first
            
            if container_locator.count() == 0:
                container_locator = self.page.locator("div[role='main']").locator("..").locator("div.m6QErb[tabindex='-1']").first
            if container_locator.count() == 0:
                container_locator = self.page.locator("div[role='main']").first
                
            if container_locator.count() == 0:
                logger.error(f"Review container not found.")
                return []

            last_height = container_locator.evaluate("node => node.scrollHeight")

            max_scrolls = int(os.getenv("SCROLL_RETRY", "5")) * 10
            scroll_count = 0
            
            while scroll_count < max_scrolls:
                # Scroll down using the correct element
                container_locator.evaluate("node => node.scrollBy(0, 5000)")
                # Also try to scroll the last review item into view if possible
                try:
                    last_item = self.page.locator(sel['item']).last
                    if last_item.count() > 0:
                        last_item.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                
                random_delay(1.5, 3)
                
                # Check for 'Ulasan lainnya' button (Pagination)
                more_reviews_btn = self.page.locator(sel['more_reviews_button'])
                if more_reviews_btn.count() > 0 and more_reviews_btn.first.is_visible():
                    logger.info("Clicking 'Ulasan lainnya' button.")
                    more_reviews_btn.first.click()
                    random_delay(2, 4)
                
                new_height = container_locator.evaluate("node => node.scrollHeight")
                if new_height == last_height:
                    # Give it one more chance with a slightly bigger scroll
                    container_locator.evaluate("node => node.scrollBy(0, 5000)")
                    random_delay(1, 2)
                    new_height = container_locator.evaluate("node => node.scrollHeight")
                    if new_height == last_height:
                        logger.info("Reached the end of the list or stuck.")
                        break
                    
                last_height = new_height
                scroll_count += 1
                
                # Check if we have enough reviews based on date or count threshold
                current_count = self.page.locator(sel['item']).count()
                max_reviews = int(os.getenv("MAX_REVIEWS", "100"))
                if max_reviews > 0 and current_count >= max_reviews: 
                    break
                
            logger.info(f"Finished scrolling/clicking. Found {self.page.locator(sel['item']).count()} potential reviews.")
            
            # Extract data from review items
            review_items = self.page.locator(sel['item']).all()
            for item in review_items:
                try:
                    # Click 'More' if exists to expand long text
                    more_btn = item.locator(sel['more_button'])
                    if more_btn.count() > 0:
                        more_btn.first.click()
                        random_delay(0.5, 1)
                        
                    review_data = {
                        'place_id': place_id,
                        'place_url': place_url,
                        'nama_tempat': name,
                        'review_id': item.get_attribute("data-review-id"),
                        'author_name': item.locator(sel['author']).text_content(),
                        'rating_ulasan': item.locator(sel['rating']).get_attribute("aria-label"),
                        'tanggal_raw': item.locator(sel['date']).text_content(),
                        'isi_review': item.locator(sel['text']).text_content() if item.locator(sel['text']).count() > 0 else "",
                        # Owner reply detection
                        'balasan_pemilik': "",
                        'tanggal_balasan_raw': ""
                    }
                    
                    # Small logic for owner reply (usually nested or separate div with same text style but different container)
                    # This depends on local language. In REVIEWS_PAGE_HTML we saw 'Balasan dari pemilik' pattern.
                    # For now, we use a simple approach or fallback.
                    
                    reviews.append(review_data)
                except Exception as ex:
                    logger.warning(f"Error extracting single review: {ex}")
                    
            return reviews
        except Exception as e:
            logger.error(f"Error during review scraping: {e}")
            return reviews
