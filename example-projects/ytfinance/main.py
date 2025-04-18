import yfinance as yf
import json
import sys
import pandas as pd


import requests_cache
import os
import pickle
import time
from datetime import datetime, timedelta
from requests_ratelimiter import LimiterSession



def create_session(cache_name='yfinance_cache', expire_after=3600, rate_limit=True, max_requests=2, period=1, proxy=None):
            """
            Create a session with caching and optional rate limiting
            
            Args:
                cache_name (str): Name for the cache file
                expire_after (int): Cache expiration time in seconds
                rate_limit (bool): Whether to apply rate limiting
                max_requests (int): Maximum number of requests allowed in the period
                period (int): Time period in seconds for rate limiting
                proxy (str): Optional proxy server URL
                
            Returns:
                session: Configured session object
            """
            session = requests_cache.CachedSession(
                cache_name,
                backend='sqlite',
                expire_after=expire_after
            )
            
            # Add rate limiting if requested
            if rate_limit:
                session = LimiterSession(
                    per_second=max_requests/period,
                    session=session
                )
            
            # Add proxy if provided
            if proxy:
                session.proxies = {'http': proxy, 'https': proxy}
                
            # Set user agent
            session.headers['User-agent'] = 'my-program/1.0'
            
            return session

def analyze_stock(ticker):
    
    info = ticker.info
    financials = ticker.financials
    balance_sheet = ticker.balance_sheet
    cashflow = ticker.cashflow

    #print(json.dumps(info, indent=2))
    try:
        # Current Price and 52-week Range
        current_price = info.get("currentPrice", None)
        fifty_two_week_high = info.get("fiftyTwoWeekHigh", None) 
        fifty_two_week_low = info.get("fiftyTwoWeekLow", None)
        market_cap = info.get("marketCap", None)

        # Core Profitability & Valuation
        roe = info.get("returnOnEquity", None)
        profit_margin = info.get("profitMargins", None)
        pe_ratio = info.get("trailingPE", None)
        pb_ratio = info.get("priceToBook", None)
        eps = info.get("trailingEps", None)
        peg = info.get("trailingPegRatio", None)
        revenue_growth = info.get("revenueGrowth", None)
        operating_margin = info.get("operatingMargins", None)

        # Financial Health
        def safe_get_value(df, key):
            try:
                return df.loc[key].iloc[0] if key in df.index else None
            except:
                return None

        print(financials.index)

        print(cashflow.index)

        total_equity = safe_get_value(balance_sheet, "Total Stockholder Equity")
        if not total_equity:
             total_equity = safe_get_value(balance_sheet, "Stockholders Equity")

        long_term_debt = safe_get_value(balance_sheet, "Long Term Debt")

             
        current_assets = safe_get_value(balance_sheet, "Total Current Assets")
        if not current_assets:
            current_assets = safe_get_value(balance_sheet, "Current Assets")

        current_liabilities = safe_get_value(balance_sheet, "Total Current Liabilities")
        if not current_liabilities:
            current_liabilities = safe_get_value(balance_sheet, "Current Liabilities")


        ebit = info.get("ebitda",None)
        interest_expense = safe_get_value(financials, "Interest Expense")
        current_ratio = info.get("currentRatio", None)
        
        #print("XX",interest_expense)
        #ddd
        #interest_expense = financials.loc["Interest Expense"].iloc[0]

        
        interest_coverage = ebit / abs(interest_expense)


        debt_to_equity = info.get("debtToEquity", None)

        # Cash Flow
        op_cash_flow = info.get("operatingCashflow", None)
        capex = safe_get_value(cashflow,"Capital Expenditure")

        free_cash_flow = info.get("freeCashflow", None)
        net_income = info.get("netIncomeToCommon")
        depreciation = info.get("depreciation")
        if not depreciation:
            depreciation = safe_get_value(cashflow, "Depreciation And Amortization")

        owner_earnings = (net_income or 0) + (depreciation or 0) - (capex or 0)
        #print("AA",cashflow["Capital Expenditure"])
        # Efficiency & Insider Actions (if available)
        inventory_turnover = info.get("inventoryTurnover")
        insider_ownership = info.get("heldPercentInsiders")
        shares_outstanding = info.get("sharesOutstanding")
        share_buyback = info.get("buybackYield")
        return {
            "Company Name": info.get("longName"),
            "Ticker": ticker.ticker,
            "Currency": info.get("currency"),
            "Current Price": current_price,
            "52-Week High": fifty_two_week_high,
            "52-Week Low": fifty_two_week_low,
            "Market Cap": market_cap,
            "EBITA": ebit,
            "ROE": roe,
            "Profit Margin": profit_margin,
            "Operating Margin": operating_margin,
            "P/E Ratio": pe_ratio,
            "P/B Ratio": pb_ratio,
            "PEG Ratio": peg,
            "EPS": eps,
            "Revenue Growth": revenue_growth,
            "Free Cash Flow": free_cash_flow,
            "Operating Cash Flow": op_cash_flow,
            "Owner Earnings": owner_earnings,
            "Debt/Equity": debt_to_equity,
            "Current Ratio": current_ratio,
            "Interest Coverage": interest_coverage,
            "Inventory Turnover": inventory_turnover,
            "Insider Ownership": insider_ownership,
            "Shares Outstanding": shares_outstanding,
            "Total Equity": total_equity,
            "Long Term Debt": long_term_debt,
            "Current Assets": current_assets,
            "Current Liabilities": current_liabilities,
            "Capital Expenditures": capex,
            "Free Cash Flow": free_cash_flow,
            "Net Income": net_income,
            "Depreciation": depreciation
            #"Share Buyback Yield": share_buyback
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"Error": str(e)}



def get_apple_stock():
    aapl = yf.Ticker("AAPL")
    return aapl

def get_historical_data(ticker:yf.Ticker, period='1w'):
        """
        Get historical market data for a given ticker
        periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
        """
        try:
            hist = ticker.history(period=period)
            return hist
        except Exception as e:
            return {"Error": str(e)}
        

def download_ticker(ticker_symbol, period='1d', interval='1d',start=None,end=None,output_file=None):
    """
    Download ticker data using yfinance and save to a CSV file
    
    Args:
        ticker_symbol (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        period (str): Data period (e.g., '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max')
        interval (str): Data interval (e.g., '1m','2m','5m','15m','30m','60m','90m','1h','1d','5d','1wk','1mo','3mo')
        output_file (str): Path to save CSV file. If None, uses ticker_symbol_period_interval.csv
    
    Returns:
        str: Path to the saved CSV file
    """
    try:
        # Download the data
        if start and end:
            data = yf.download(ticker_symbol, start=start, end=end, interval=interval)
        else:
            data = yf.download(ticker_symbol, period=period, interval=interval)
        # Generate default filename if not provided
        if output_file is None:
            if start and end:
                output_file = f"{ticker_symbol}_{start}_{end}_{interval}.csv"
            else:
                output_file = f"{ticker_symbol}_{period}_{interval}.csv"
        
        print(data)
        # Save to CSV
        data.to_csv(output_file, 
                index=True,            # Include the datetime index
                float_format='%.4f',   # Format floating point numbers to 4 decimal places
                date_format='%Y-%m-%d %H:%M:%S',  # Format datetime objects
                encoding='utf-8')      # Specify encoding
        print(f"Data successfully saved to {output_file}")
        return output_file
    except Exception as e:
        print(f"Error downloading {ticker_symbol}: {str(e)}")
        return None


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

def get_stock_with_rate_limit(ticker_symbol, max_requests=2, period=1):
    """
    Get stock data using yfinance with SQLite cache and rate limiting
    
    Args:
        ticker_symbol (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        max_requests (int): Maximum number of requests allowed in the period
        period (int): Time period in seconds for rate limiting
        
    Returns:
        yfinance.Ticker: Ticker object with cached and rate-limited data
    """
    try:
        
        # Create a session using the create_session function
        limiter_session = create_session(
            cache_name='my_cache',
            expire_after=3600,  # Cache for 1 hour
            rate_limit=True,
            max_requests=max_requests,
            period=period
        )
        ticker = yf.Ticker(ticker_symbol, session=limiter_session)
        
        return ticker
    except Exception as e:
        print("Error ")
        return None 



def get_multiple_stocks(ticker_symbols, max_requests=2, period=1):
    """
    Get data for multiple stocks using yfinance with caching and rate limiting
    
    Args:
        ticker_symbols (list): List of stock ticker symbols (e.g., ['AAPL', 'MSFT'])
        max_requests (int): Maximum number of requests allowed in the period
        period (int): Time period in seconds for rate limiting
        
    Returns:
        dict: Dictionary of ticker objects with ticker symbols as keys
    """
    try:
        # Create a session using the create_session function
        limiter_session = create_session(
            cache_name='multiple_stocks_cache',
            expire_after=3600,  # Cache for 1 hour
            rate_limit=True,
            max_requests=max_requests,
            period=period
        )
        
        
        tickers = yf.Tickers(ticker_symbols, session=limiter_session)

            
        return tickers
    except Exception as Error:
        print("Warning: requests_ratelimiter not found. Using cached session only.")
        return None


def get_balance_sheet(ticker, use_cache=True, rate_limit=True, max_requests=2, period=1, proxy=None):
    """
    Get balance sheet for a ticker with options for caching, rate limiting and proxy
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        use_cache (bool): Whether to use caching for API requests
        rate_limit (bool): Whether to apply rate limiting
        max_requests (int): Maximum number of requests allowed in the period (for rate limiting)
        period (int): Time period in seconds for rate limiting
        proxy (str): Optional proxy server URL (e.g., 'http://user:pass@host:port')
        
    Returns:
        pandas.DataFrame: Balance sheet data for the ticker
    """
    try:
        session = None
        


        # Use the function to create a session
        if use_cache:
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
        
        # Set user agent
        if session:
            ticker_obj = yf.Ticker(ticker, session=session)
        else:
            # Use default session if no cache/rate limit needed
            ticker_obj = yf.Ticker(ticker)
            

        # Get balance sheet data
        if proxy:
            balance_sheet = ticker_obj.get_balance_sheet()
        else:
            balance_sheet = ticker_obj.get_balance_sheet()
        return balance_sheet
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error getting balance sheet for {ticker}: {str(e)}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <mode> [period]")
        print("Modes: 1=analysis, 2=historical, 3=download, 4=cached, 5=rate-limited, 6=infosys, 7=multiple, 8=balance-sheet")
        print("For mode 3 (download): python main.py 3 <ticker> [period] [interval] [output_file]")
        print("For mode 4 (cached): python main.py 4 <ticker>")
        print("For mode 5 (rate-limited): python main.py 5 <ticker> [max_requests] [period]")
        print("For mode 6 (infosys): python main.py 6 [period]")
        print("For mode 7 (multiple): python main.py 7 <ticker1,ticker2,...> [max_requests] [period]")
        print("For mode 8 (balance-sheet): python main.py 8 <ticker> [proxy_url]")
        print("Period (optional): 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max")
        sys.exit(1)
        
    mode = int(sys.argv[1])
    
    if mode == 1:
        aapl = get_apple_stock()
        result = analyze_stock(aapl)
        print(json.dumps(result, indent=2))
    elif mode == 2:
        period = sys.argv[2] if len(sys.argv) > 2 else '5d'
        aapl = get_apple_stock()
        hist = get_historical_data(aapl, period)

        if isinstance(hist, pd.DataFrame) and not hist.empty:
            print("First row of historical data:")
            print(hist.iloc[0].to_string())
            print("\nIndex of first row (date):")
            print(hist.index[0])
        else:
            print(hist)  # Print error message if applicable
    elif mode == 3:
        if len(sys.argv) < 3:
            print("Error: Please provide a ticker symbol")
            sys.exit(1)
            
        ticker = sys.argv[2]
        period = sys.argv[3] if len(sys.argv) > 3 else '1d'
        interval = sys.argv[4] if len(sys.argv) > 4 else '1d'
        output_file = sys.argv[5] if len(sys.argv) > 5 else None
        
        download_ticker(ticker, period, interval, output_file=output_file)
    elif mode == 4:
        if len(sys.argv) < 3:
            print("Error: Please provide a ticker symbol")
            sys.exit(1)
            
        ticker_symbol = sys.argv[2]
        ticker = get_stock_cache(ticker_symbol)
        result = analyze_stock(ticker)
        print(json.dumps(result, indent=2))
    elif mode == 5:
        if len(sys.argv) < 3:
            print("Error: Please provide a ticker symbol")
            sys.exit(1)
            
        ticker_symbol = sys.argv[2]
        max_requests = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        period = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        
        ticker = get_stock_with_rate_limit(ticker_symbol, max_requests, period)
        result = analyze_stock(ticker)
        print(json.dumps(result, indent=2))
    elif mode == 6:
        # Get Infosys stock - use INFY ticker (Nasdaq listed)
        period = sys.argv[2] if len(sys.argv) > 2 else '1mo'
        infosys = get_stock_cache("INFY.NS")
        result = analyze_stock(infosys)
        print(json.dumps(result, indent=2))
        
        # Also show historical data
        hist = get_historical_data(infosys, period)
        if isinstance(hist, pd.DataFrame) and not hist.empty:
            print("\nRecent historical data for Infosys:")
            print(hist.tail().to_string())
    elif mode == 7:
        if len(sys.argv) < 3:
            print("Error: Please provide ticker symbols separated by commas")
            sys.exit(1)
            
        ticker_symbols = sys.argv[2].split(',')
        max_requests = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        period = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        
        tickers = get_multiple_stocks(ticker_symbols, max_requests, period)
        print(f"Fetched {len(ticker_symbols)} tickers")
        for symbol in ticker_symbols:
            print(f"\nAnalysis for {symbol}:")
            ticker = tickers.tickers[symbol.upper()]
            result = analyze_stock(ticker)
            print(result)
    elif mode == 8:
        if len(sys.argv) < 3:
            print("Error: Please provide a ticker symbol")
            sys.exit(1)
            
        ticker_symbol = sys.argv[2]
        saddr = sys.argv[3] if len(sys.argv) > 3 else None
        
        proxy = saddr 

        print(f"Fetching balance sheet for {ticker_symbol} using proxy: {proxy if proxy else 'None'}")
        balance_sheet = get_balance_sheet(ticker_symbol, use_cache=True, rate_limit=True, proxy=proxy)
        
        if isinstance(balance_sheet, pd.DataFrame) and not balance_sheet.empty:
            print("\nBalance Sheet Data:")
            print(balance_sheet.to_string())
        else:
            print("Failed to retrieve balance sheet data",balance_sheet)


if __name__ == "__main__":
    main()


