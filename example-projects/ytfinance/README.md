# YTFinance Documentation

YTFinance is a powerful library for retrieving financial market data from Yahoo Finance. Here's how to use it effectively for both Indian and US markets.

## Installation and Overview

Yahoo Finance offers an excellent range of market data on stocks, bonds, currencies and cryptocurrencies. It also offers market news, reports and analysis and additionally options and fundamentals data- setting it apart from some of it’s competitors. Yahoo Finance used to have their own official API, but this was decommissioned on May 15th 2017, following wide-spread misuse of data. These days a range of unofficial APIs and libraries exist to access the same data, including   yfinance.

yfinance is an open-source library that scrapes financial data from Yahoo Finance using their API endpoints. You can find the official repository at [https://github.com/ranaroussi/yfinance](https://github.com/ranaroussi/yfinance).

Installation is simple:
```bash
pip install yfinance 
```

The library works by making HTTP requests to Yahoo Finance's API endpoints and parsing the JSON responses. It handles rate limiting, data caching, and provides a Pythonic interface to access financial data.

Key features:
- Downloads historical market data from Yahoo Finance's API
- Retrieves real-time and historical pricing
- Access to fundamental data, company info, and financial statements
- Supports multiple global markets including US and Indian exchanges

## Available Classes and Functions

The yfinance package exposes these public classes and functions:

* `Ticker`: Access single ticker data
* `Tickers`: Handle multiple tickers
* `Market`: Access market summary and status
* `download`: Download market data for multiple tickers
* `Search`: Access search results
* `Sector`: Access sector information
* `Industry`: Access industry information
* `EquityQuery`: Build equity query filters
* `FundQuery`: Build fund query filters

screen: Run equity/fund queries.


## Basic Usage

```python
import yfinance as yf
```

## Getting Stock Information


```python
# Get information for a specific stock
def get_apple_stock():
    aapl = yf.Ticker("AAPL")
    return aapl

# Example usage
apple_data = get_apple_stock()
```

You can adapt this function for any stock by changing the ticker symbol. For Indian stocks, add `.NS` for NSE listings (e.g., "RELIANCE.NS").

### Stock Analysis Features


The `analyze_stock(ticker)` function performs comprehensive financial analysis using various data structures provided by YFinance's Ticker object.

**ticker.info** - Contains fundamental company information and real-time market data
**ticker.financials** - Contains annual financial statements
**ticker.balance_sheet**  - Contains annual balance sheet data
**ticker.cashflow** - Contains annual cash flow statements


**Current Price and Market Position**
   ```python
   {
       "Current Price": info["currentPrice"],
       "52-Week High": info["fiftyTwoWeekHigh"],
       "52-Week Low": info["fiftyTwoWeekLow"],
       "Market Cap": info["marketCap"]
   }
   ```

**Profitability and Valuation**
   ```python
   {
       "ROE": info["returnOnEquity"],
       "Profit Margin": info["profitMargins"],
       "Operating Margin": info["operatingMargins"],
       "P/E Ratio": info["trailingPE"],
       "P/B Ratio": info["priceToBook"],
       "PEG Ratio": info["trailingPegRatio"]
   }
   ```

**Financial Health**
   ```python
   {
       "Total Equity": balance_sheet["Total Stockholder Equity"],
       "Long Term Debt": balance_sheet["Long Term Debt"],
       "Current Ratio": info["currentRatio"],
       "Interest Coverage": ebit / abs(interest_expense)
   }
   ```

**Cash Flow Analysis**
   ```python
   {
       "Operating Cash Flow": info["operatingCashflow"],
       "Free Cash Flow": info["freeCashflow"],
       "Owner Earnings": net_income + depreciation - capex
   }
   ```

# Example usage
```
apple_data = analyze_stock(ticker)
```


### Working with Multiple Stocks

The `get_multiple_stocks` function allows you to retrieve data for multiple stock tickers simultaneously.

```python
def get_multiple_stocks(ticker_symbols):

    tickers = yf.Tickers(ticker_symbols)

    return tickers;
```

## Advanced Usage with Caching and Rate Limiting

When working with YFinance, implementing proper caching and rate limiting is essential to avoid being blocked by Yahoo Finance servers and to optimize your application's performance.


YFinance can be used with `requests_cache` and `requests_ratelimiter` libraries to efficiently manage API request , The `requests_cache` library stores responses locally to avoid redundant requests, while `requests_ratelimiter` ensures you don't exceed Yahoo Finance's rate limits.

```
pip install yfinance[nospam]
```

For a detailed guide on optimizing Python requests with caching and rate limiting techniques, check out [this comprehensive article](https://medium.com/neural-engineer/python-request-optimization-caching-and-rate-limiting-79ceb5e6eb1e).


### Creating Optimized Sessions
```python
def create_session(cache_name='yfinance_cache', expire_after=3600, rate_limit=True, max_requests=2, period=1, proxy=None):
    """
    Create an optimized session with caching and optional rate limiting for yfinance requests.
    
    Args:
        cache_name (str): Name of the cache database file
        expire_after (int): Cache expiration time in seconds (default: 1 hour)
        rate_limit (bool): Whether to enable rate limiting
        max_requests (int): Maximum number of requests allowed in the specified period
        period (int): Time period in seconds for rate limiting
        proxy (str): Optional proxy server URL
    
    Returns:
        Session object configured with caching and rate limiting
    """
    # Initialize a cached session to store responses
    session = requests_cache.CachedSession(
        cache_name,
        backend='sqlite',  # Using SQLite as the storage backend
        expire_after=expire_after  # Cache entries expire after this many seconds
    )
    
    # Apply rate limiting if enabled
    if rate_limit:
        session = LimiterSession(
            per_second=max_requests/period,  # Calculate requests per second
            session=session  # Apply limiter to our cached session
        )
    
    # Configure proxy settings if provided
    if proxy:
        session.proxies = {'http': proxy, 'https': proxy}
    
    # Set a custom user agent to identify your application
    session.headers['User-agent'] = 'my-program/1.0'
    return session
```

When implemented, the SQLite cache , fetched financial data is stored in a local file called my_cache.sqlite 

```python
def get_stock_cache(ticker_symbol):
    """
    Get stock data using yfinance with SQLite cache to avoid excessive API calls
    
    Args:
        ticker_symbol (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        
    Returns:
        yfinance.Ticker: Ticker object with cached data
    """
    
    # Use the create_session function we defined earlier
    session = create_session(
        cache_name='my_cache',
        expire_after=3600,  # Cache for 1 hour
        rate_limit=False    # No rate limiting for basic cache
    )

    ticker = yf.Ticker(ticker_symbol, session=session)

    return ticker
```


## Using Proxy with yfinance

When accessing financial data through yfinance, you may need to use a proxy server to handle rate limiting, access restrictions, or network requirements. This section explains how to configure and use proxies with the yfinance library.

You can find free proxies online, but be aware they:
- Are often unreliable or insecure 
- May log your activity
- Have high latency

🧪 Examples:
Sites like:
- https://free-proxy-list.net/
- https://www.sslproxies.org/ 
- https://spys.one/en/


In the current example we will use socks5 proxy  `170.39.119.109:1100`

```python
# Configure proxy settings"  # Replace with your proxy

 session = create_session(
                cache_name='balance_sheet_cache',
                expire_after=3600,
                rate_limit=rate_limit,
                max_requests=max_requests,
                period=period,
                proxy=proxy
            )
        
# Add proxy if provided
if proxy and session:
            session.proxies = {'socks5': proxy}

proxy_credentials = {
    "socks5": proxy
}

ticker_obj = yf.Ticker(ticker, session=session)
ticker_obj.get_balance_sheet()

```
### Example Code and Usage

```bash
python main.py <mode> [arguments]
```

Available modes:
1. Stock analysis
2. Historical data retrieval
3. Data download to CSV
4. Cached stock data
5. Rate-limited queries
6. Indian market stocks
7. Multiple stock analysis
8. Balance sheet retrieval

Example usage:
```bash
# Basic analysis
python main.py 1

# Historical data with period
python main.py 2 5d

# Download ticker data
python main.py 3 AAPL 1d 1h output.csv

# Cached stock data
python main.py 4 MSFT

# Rate-limited queries
python main.py 5 GOOGL 2 1

#Indian Stocks
python main.py 6 INFY.NS

# Multiple stocks analysis
python main.py 7 AAPL,MSFT,GOOGL

#proxuy
python main.py 8 INFY.NS 170.39.119.109:1100
```
# Conclusion

YFinance provides a robust and flexible way to access financial market data from Yahoo Finance. With the techniques demonstrated in this documentation, you can efficiently retrieve, analyze, and cache stock data for both US and Indian markets while respecting rate limits and optimizing performance.

This library is particularly valuable for:
- Financial analysis and research
- Algorithmic trading development
- Portfolio tracking applications
- Market trend visualization

By implementing proper caching and rate limiting as shown in the examples, you can build reliable financial applications that maintain consistent access to market data without overwhelming Yahoo Finance's servers.

## Full Code Repository

The complete code for all examples in this documentation is available on GitHub:
[https://github.com/pyVision/neural-engineer/tree/main/example-projects/ytfinancee](https://github.com/pyVision/neural-engineer/tree/main/example-projects/ytfinance)

Feel free to clone the repository, submit issues, or contribute improvements to make this resource even more valuable for the financial data community.

