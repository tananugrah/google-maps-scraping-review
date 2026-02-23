import re
from playwright.sync_api import sync_playwright

def test_place_id():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating...")
        page.goto("https://www.google.com/maps/place/SiCepat+Ekspres+Indonesia+Pusat/@-6.2097714,106.8283779,17z/data=!3m1!4b1!4m6!3m5!1s0x2e69f502d6abe5df:0x38210cb1e0d382e8!8m2!3d-6.2097714!4d106.8309528!16s%2Fg%2F11fjbkw9g4?entry=ttu")
        page.wait_for_load_state("networkidle")
        html = page.content()
        
        print("Looking for ChIJ...")
        matches_user = re.findall(r'(ChIJ[a-zA-Z0-9_-]{20,})', html)
        matches_lenient = re.findall(r'ChIJ[\w-]+', html)
        
        print("User Pattern (>= 20 chars):", set(matches_user))
        print("Lenient Pattern:", set(matches_lenient))
        browser.close()

if __name__ == "__main__":
    test_place_id()
