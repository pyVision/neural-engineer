


from playwright.sync_api import sync_playwright
import json

def test_website_title():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://miko.ai')
        
        # Check if the title contains expected text
        assert 'Miko' in page.title(), f"Expected 'Miko' in title, but got '{page.title()}'"
        print(f"Page title: {page.title()}")
        
        browser.close()


import asyncio
from playwright.async_api import async_playwright
import argparse

async def test_website_title_async():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('https://miko.ai')
        
        # Check if the title contains expected text
        title = await page.title()
        assert 'Miko' in title, f"Expected 'Miko' in title, but got '{title}'"
        print(f"Page title: {title}")
        
        await browser.close()

        
from playwright.sync_api import sync_playwright
import asyncio
from playwright.async_api import async_playwright

def scrape_cloudflare_protected_site():
    with sync_playwright() as p:
        # Launch Safari browser instead of Chromium
        browser = p.webkit.launch(headless=True, 
                      slow_mo=100)
        
        # Use a custom user agent
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
            viewport={"width": 1280, "height": 800}
        )   

        # Mask navigator.webdriver to avoid detection
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => false})"
        )

        page = context.new_page()

        page.goto("https://www.nseindia.com", timeout=12000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
           
        response = page.goto('https://www.nseindia.com/api/allIndices', wait_until="domcontentloaded")
        
        content = response.text()
        data = json.loads(content)
        
        browser.close()
        return data

async def scrape_cloudflare_protected_site_async():
    async with async_playwright() as p:
        # Launch Safari browser instead of Chromium
        browser = await p.webkit.launch(headless=True, 
                      slow_mo=100)
        
        # Use a custom user agent
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
            viewport={"width": 1280, "height": 800}
        )   

        # Mask navigator.webdriver to avoid detection
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => false})"
        )

        page = await context.new_page()

        await page.goto("https://www.nseindia.com", timeout=12000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
           
        response = await page.goto('https://www.nseindia.com/api/allIndices', wait_until="domcontentloaded")
        
        content = await response.text()
        data = json.loads(content)
        
        await browser.close()
        return data
        
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test website with Playwright')
    parser.add_argument('--mode', type=str)
            
    args = parser.parse_args()
            
    if args.mode == '0':
        print("Running synchronous test:")
        test_website_title()
            
    elif args.mode == '1':
        print("Running asynchronous test:")
        asyncio.run(test_website_title_async())

    elif args.mode == '2':
        print("Running Cloudflare protected site scraping:")
        content = scrape_cloudflare_protected_site()
        print(content)
        
    elif args.mode == '3':
        print("Running async Cloudflare protected site scraping:")
        content = asyncio.run(scrape_cloudflare_protected_site_async())
        print(content)