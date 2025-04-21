# Getting Started with Playwright for Web Scrapping

Playwright is a powerful automation framework for web testing and web scraping that offers cross-browser support for Chromium, Firefox, and WebKit. Let's dive into how it can revolutionize your testing workflow.

## Why Choose Playwright?

- **Multi-browser support** out of the box
- **Auto-wait** capabilities that make tests more reliable
- **Network interception** for robust API testing
- **Mobile emulation** and responsive testing
- **Modern architecture** supporting async/await

## Source Code

All example code for this project is available in the following GitHub repository:
- Repository: [neural-engineer/example-projects](https://github.com/pyVision/neural-engineer/example-projects)
- Path: `/playwright`

## Quick Start Guide

First, install Playwright in your project:

```bash
pip install playwright
playwright install
```

### Basic Test Example

Here's a simple test that navigates to a website and checks the title:

```python
from playwright.sync_api import sync_playwright

def test_website_title():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://miko.ai')
        
        # Check if the title contains expected text
        assert 'Miko' in page.title(), f"Expected 'Miko' in title, but got '{page.title()}'"
        print(f"Page title: {page.title()}")
        
        browser.close()

# Run with: python main.py --mode 0
```

## Using Async Example

Playwright supports both synchronous and asynchronous approaches. Here's how to use the async API:

```python
import asyncio
from playwright.async_api import async_playwright

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

# Run with: python main.py --mode 1
```

## Web Scraping

Playwright excels at web scraping tasks, offering several advantages over traditional scraping tools:

- **Browser automation** provides access to JavaScript-rendered content
- **Stealth mode** helps avoid detection by anti-bot mechanisms
- **Handles Cloudflare protection** more effectively than basic HTTP requests
- **Cookie and session management** for authenticated scraping

### Advanced Example: Handling Protected Sites

Here's a more sophisticated example that demonstrates how to handle sites with anti-bot protection using Safari (WebKit):

```python
from playwright.sync_api import sync_playwright
import json

def scrape_cloudflare_protected_site():
    with sync_playwright() as p:
        # Launch Safari browser instead of Chromium for better protection bypass
        browser = p.webkit.launch(headless=True, 
                      slow_mo=100)
        
        # Use a Safari-specific user agent
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
            viewport={"width": 1280, "height": 800}
        )   

        # Mask navigator.webdriver to avoid detection
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => false})"
        )

        page = context.new_page()

        # Initial navigation with longer timeout and domcontentloaded wait
        page.goto("https://www.nseindia.com", timeout=12000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
           
        # Access API endpoint after session is established
        response = page.goto('https://www.nseindia.com/api/allIndices', wait_until="domcontentloaded")
        
        content = response.text()
        data = json.loads(content)
        
        browser.close()
        return data

# Run with: python main.py --mode 2
```

### Async Version of Protected Site Scraping

For better performance, you can use the async version:

```python
async def scrape_cloudflare_protected_site_async():
    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=True, 
                      slow_mo=100)
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
            viewport={"width": 1280, "height": 800}
        )   

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

# Run with: python main.py --mode 3
```

## Running the Examples

The project includes a command-line interface to run different examples:

```bash
# Run synchronous test
python main.py --mode 0

# Run async test
python main.py --mode 1

# Run protected site scraping (sync)
python main.py --mode 2

# Run protected site scraping (async)
python main.py --mode 3
```

## Conclusion

Playwright provides a robust foundation for both modern web testing and advanced web scraping. Its ability to simulate genuine browser behavior while maintaining fine-grained control makes it exceptionally well-suited for accessing challenging websites and automating complex user workflows. Whether you're developing end-to-end tests, creating sophisticated web scrapers, or simulating nuanced user interactions, Playwright offers the technical capabilities and developer experience to make these tasks more reliable and efficient.

For more information, visit the [official Playwright documentation](https://playwright.dev).