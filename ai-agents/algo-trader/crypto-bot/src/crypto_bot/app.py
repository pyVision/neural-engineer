#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crypto Market Dashboard

A FastAPI application that displays cryptocurrency market data similar to Google Finance.
Features include:
- List of cryptocurrencies with key metrics
- Pagination (50 entries per page)
- Sorting by different columns
- Basic search functionality
"""

import os
import sys
import asyncio
from typing import List, Optional
from fastapi import FastAPI, Request, Query, HTTPException, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

try:
    from .init_application import initialization_result
    from .data_controller import get_data_controller
except ImportError:
    from crypto_bot.init_application import initialization_result
    from crypto_bot.data_controller import get_data_controller

# Add parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the CryptoExchange class
from crypto_exchange import CryptoExchange


# Cache configuration
CACHE_KEY_PREFIX = "crypto_dashboard"
CACHE_DATA_KEY = f"{CACHE_KEY_PREFIX}:all_cryptos"
CACHE_METADATA_KEY = f"{CACHE_KEY_PREFIX}:metadata"
CACHE_DURATION = 600  # 10 minutes in seconds

exchange = None 
# Create FastAPI app
app = FastAPI(
    title="Crypto Market Dashboard",
    description="A dashboard for cryptocurrency market data",
    version="1.0.0"
)

async def is_cache_valid():
    """Check if the Redis cache is still valid"""
    try:
        data_controller = await get_data_controller()
        metadata = await data_controller.cache.get_from_cache(CACHE_METADATA_KEY)
        
        if not metadata or "last_updated" not in metadata:
            return False
        
        last_updated = datetime.fromisoformat(metadata["last_updated"])
        time_since_update = datetime.now() - last_updated
        
        print("Checking cache validity...")
        flag = time_since_update.total_seconds() < metadata.get("cache_duration", CACHE_DURATION)
        print(f"Cache valid: {flag} (last updated: {time_since_update.total_seconds()}, duration: {metadata.get('cache_duration', CACHE_DURATION)} seconds)")
        return flag
    except Exception as e:
        print(f"Error checking cache validity: {e}")
        return False

async def update_global_cache(crypto_data):
    """Update the Redis cache with new cryptocurrency data"""
    try:
        data_controller = await get_data_controller()
        
        # Create metadata with timestamp
        metadata = {
            "last_updated": datetime.now().isoformat(),
            "cache_duration": CACHE_DURATION,
            "data_count": len(crypto_data)
        }
        
        # Store data and metadata in Redis - our enhanced JsonSerializer will handle Pydantic models now
        await data_controller.cache.set_in_cache(CACHE_DATA_KEY, crypto_data)
        await data_controller.cache.set_in_cache(CACHE_METADATA_KEY, metadata)
        
        print(f"Cache updated with {len(crypto_data)} cryptocurrencies at {metadata['last_updated']}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error updating cache: {e}")

async def get_valid_cached_data():
    """Get cryptocurrency data from Redis cache if valid, otherwise return None"""
    try:
        if not await is_cache_valid():
            return None
        
        data_controller = await get_data_controller()
        crypto_data = await data_controller.cache.get_from_cache(CACHE_DATA_KEY)
        
        if crypto_data:
            metadata = await data_controller.cache.get_from_cache(CACHE_METADATA_KEY)
            print(f"Using valid cached data from {metadata.get('last_updated', 'unknown time')}")
            
        return crypto_data
    except Exception as e:
        print(f"Error getting valid cached data: {e}")
        return None

async def get_cached_data_regardless_of_validity():
    """Get cryptocurrency data from Redis cache even if it's expired"""
    try:
        data_controller = await get_data_controller()
        crypto_data = await data_controller.cache.get_from_cache(CACHE_DATA_KEY)
        
        if crypto_data:
            metadata = await data_controller.cache.get_from_cache(CACHE_METADATA_KEY)
            cache_valid = await is_cache_valid()
            status = "valid" if cache_valid else "expired"
            print(f"Using {status} cached data from {metadata.get('last_updated', 'unknown time')}")
            
        return crypto_data
    except Exception as e:
        print(f"Error getting cached data: {e}")
        return None

# Startup event to initialize exchange when the application starts
@app.on_event("startup")
async def startup_event():
    """Initialize the exchange when the application starts."""
    global exchange
    try:
        print("Initializing exchange on startup...")
        # Get exchange instance
        get_exchange()
        print(f"Exchange initialized successfully on startup.")
    except Exception as e:
        print(f"Error initializing exchange on startup: {e}")

# Set up templates
templates_path = os.path.join(current_dir, "templates")
os.makedirs(templates_path, exist_ok=True)
templates = Jinja2Templates(directory=templates_path)

# Set up static files
static_path = os.path.join(current_dir, "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Models
class CryptoListing(BaseModel):
    symbol: str
    name: str
    price: float
    percentage_change: float
    volume_24h: float
    market_cap: Optional[float] = None


class CryptoListingResponse(BaseModel):
    cryptos: List[CryptoListing]
    total_count: int
    page: int
    page_size: int
    total_pages: int


def load_api_credentials():
    """Load API credentials from environment variables or .env file."""
    load_dotenv()
    api_key = initialization_result.get("env_vars", {}).get("API_KEY") or os.getenv("API_KEY")

    api_secret = initialization_result.get("env_vars", {}).get("API_SECRET") or os.getenv("API_SECRET")

    cms_api = initialization_result.get("env_vars", {}).get("CMC_API_KEY") or os.getenv("CMC_API_KEY")

    return api_key, api_secret,cms_api

# Initialize exchange connection
def get_exchange():
    global exchange

    if exchange is None:
        exchange = CryptoExchange()  # Initialize the exchange
        api_key, api_secret,cms_api = load_api_credentials()
        exchange.init_exchange("binance", api_key, api_secret,cms_api)
        print("Exchange initialized with API credentials.",cms_api)

    return exchange


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main dashboard page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Crypto Market Dashboard"}
    )


@app.get("/api/cache-status")
async def get_cache_status():
    """Get information about the current cache status"""
    try:
        cache_valid = await is_cache_valid()
        
        data_controller = await get_data_controller()
        metadata = await data_controller.cache.get_from_cache(CACHE_METADATA_KEY)
        
        if not metadata:
            return {
                "cache_valid": False,
                "last_updated": None,
                "data_count": 0,
                "cache_duration_seconds": CACHE_DURATION,
                "time_until_refresh": 0
            }
        
        last_updated = datetime.fromisoformat(metadata.get("last_updated", datetime.now().isoformat()))
        data_count = metadata.get("data_count", 0)
        cache_duration = metadata.get("cache_duration", CACHE_DURATION)
        
        time_until_refresh = 0
        if cache_valid:
            time_until_refresh = cache_duration - (datetime.now() - last_updated).total_seconds()
            if time_until_refresh < 0:
                time_until_refresh = 0
        
        return {
            "cache_valid": cache_valid,
            "last_updated": last_updated.isoformat(),
            "data_count": data_count,
            "cache_duration_seconds": cache_duration,
            "time_until_refresh": time_until_refresh
        }
    except Exception as e:
        print(f"Error getting cache status: {e}")
        return {
            "cache_valid": False,
            "last_updated": None,
            "data_count": 0,
            "cache_duration_seconds": CACHE_DURATION,
            "time_until_refresh": 0,
            "error": str(e)
        }

@app.post("/api/refresh-cache")
async def refresh_cache(exchange: CryptoExchange = Depends(get_exchange)):
    """Manually refresh the cryptocurrency data cache"""
    try:
        # Force refresh by calling get_cryptos with force_refresh=True
        result = await get_cryptos(
            exchange=exchange,
            page=1,
            page_size=50,
            quote_currency="USDT",
            sort_by="market_cap",
            sort_desc=True,
            search=None,
            force_refresh=True
        )
        
        # Get updated cache metadata
        data_controller = await get_data_controller()
        metadata = await data_controller.cache.get_from_cache(CACHE_METADATA_KEY)
        
        return {
            "message": "Cache refreshed successfully",
            "timestamp": metadata.get("last_updated", datetime.now().isoformat()),
            "data_count": result.total_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh cache: {str(e)}")



def process_cached_data(
    crypto_data: List[CryptoListing],
    page: int,
    page_size: int,
    quote_currency: str,
    sort_by: str,
    sort_desc: bool,
    search: Optional[str]
) -> CryptoListingResponse:
    """
    Process cached cryptocurrency data with filtering, searching, sorting, and pagination
    """

    print(f"Processing cached data for page {page}, page_size {page_size}, quote_currency {quote_currency}, sort_by {sort_by}, sort_desc {sort_desc}, search '{search}'")
    # Filter by quote currency
    filtered_data = []
    print(f"Total cryptocurrencies in cache: {len(crypto_data)}")
    for crypto in crypto_data:
        # Filter by quote currency
        if not crypto.get("symbol").endswith(f"/{quote_currency}"):
            continue
            
        # Skip if search term doesn't match
        if search and search.lower() not in crypto.get("name").lower() and search.lower() not in crypto.get("symbol").lower():
            continue
            
        filtered_data.append(crypto)
    
    print(f"Filtered cryptocurrencies: {len(filtered_data)}")
    # Create a dataframe for easier sorting and pagination
    if filtered_data:
        df = pd.DataFrame(filtered_data)

        # Sort data
        if sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=not sort_desc)
        
        # Calculate pagination
        total_count = len(df)
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        
        # Calculate start and end indices for pagination
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_count)
        
        # Get page data
        page_df = df.iloc[start_idx:end_idx]
        
        # Convert back to model objects
        cryptos = [CryptoListing(**row) for row in page_df.to_dict('records')]
    else:
        total_count = 0
        total_pages = 0
        cryptos = []
    
    print(f"Returning {len(cryptos)} cryptocurrencies for page {page} of {total_pages} (total count: {total_count})")
    return CryptoListingResponse(
        cryptos=cryptos,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@app.get("/api/top-movers")
async def get_top_movers(
    exchange: CryptoExchange = Depends(get_exchange),
    quote_currency: str = Query("USDT", description="Quote currency (e.g., USDT, BTC)"),
    limit: int = Query(10, ge=5, le=50, description="Number of top/bottom pairs to return"),
    window: str = Query("1d", description="Time window (1m-59m, 1h-23h, 1d-7d)"),
    background_tasks: BackgroundTasks = None
):
    """Get top gainers and losers based on percentage change within a specified time window"""
    try:
        # Use the get_top_movers function from CryptoExchange class
        gainers = await get_cryptos(
            exchange=exchange,
            page=1,
            page_size=limit,
            quote_currency=quote_currency,
            sort_by="percentage_change",
            sort_desc=True,
            search=None,
            force_refresh=False,
            background_tasks=background_tasks
        )

        losers = await get_cryptos(
            exchange=exchange,
            page=1,
            page_size=limit,
            quote_currency=quote_currency,
            sort_by="percentage_change",
            sort_desc=False,
            search=None,
            force_refresh=False,
            background_tasks=None  # Only need to schedule refresh once
        )

        top_volume = await get_cryptos(
            exchange=exchange,
            page=1,
            page_size=limit,
            quote_currency=quote_currency,
            sort_by="volume_24h",
            sort_desc=True,
            search=None,
            force_refresh=False,
            background_tasks=None  # Only need to schedule refresh once
        )
        
        if not gainers:
            raise HTTPException(
                status_code=404, 
                detail=f"No top movers data available for {quote_currency} pairs"
            )
            
        return {
            "gainers": gainers,
            "losers": losers,
            "volume": top_volume,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch top movers data: {str(e)}")


@app.get("/api/cryptos", response_model=CryptoListingResponse)
async def get_cryptos(
    exchange: CryptoExchange = Depends(get_exchange),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=100, description="Items per page"),
    quote_currency: str = Query("USDT", description="Quote currency (e.g., USDT, BTC)"),
    sort_by: str = Query("market_cap", description="Field to sort by"),
    sort_desc: bool = Query(True, description="Sort in descending order"),
    search: Optional[str] = Query(None, description="Search term for symbol or name"),
    force_refresh: bool = Query(False, description="Force refresh cache"),
    background_tasks: BackgroundTasks = None
):
    """
    Get a paginated list of cryptocurrencies with market data
    """
    try:
        # First, check for any cached data, even if expired
        cached_data = await get_cached_data_regardless_of_validity()
        cache_valid = await is_cache_valid()
        
        # If we're forcing a refresh or we don't have any data in cache
        if force_refresh or cached_data is None:
            print("Fetching fresh cryptocurrency data immediately...")
            # Fetch all tickers from the exchange
            all_tickers = exchange.get_tickers()
            
            # Process and filter data
            crypto_data = []
            
            quote_symbols = exchange.get_quote_symbols(all_tickers)
            market_data = exchange.get_market_volume_by_symbols(quote_symbols, convert='USD')

            for symbol, ticker in all_tickers.items():
                # Extract base symbol (cryptocurrency name)
                base_symbol = symbol.split('/')[0]
                
                # Get quote currency from symbol
                symbol_quote = symbol.split('/')[1] if '/' in symbol else 'UNKNOWN'
                
                # Sometimes market cap might not be available from all exchanges
                market_cap = exchange.get_market_volume(base_symbol, market_data=market_data)
                    
                last = ticker.get("pricing_information").get('last', 0)
                if not last:
                    last = 0
                if last == 0:
                    continue 
                    
                entry = CryptoListing(
                    symbol=symbol,
                    name=base_symbol,
                    price=float(last),
                    percentage_change=float(ticker.get("change").get('percentage', 0) or 0),
                    volume_24h=float(ticker.get("volume").get('quote_volume', 0) or 0),
                    market_cap=market_cap
                )
                crypto_data.append(entry.dict())
                
            # Update the global cache
            await update_global_cache(crypto_data)
            
            # Process and return the data
            return process_cached_data(
                crypto_data, page, page_size, quote_currency, 
                sort_by, sort_desc, search
            )
        
        else:
            print(f"Using cached data (valid: {cache_valid})")
            
            # If cache is valid, simply return it
            if cache_valid:
                return process_cached_data(
                    cached_data, page, page_size, quote_currency, 
                    sort_by, sort_desc, search
                )
            
            # If cache is expired, trigger an async refresh and return the stale data
            if background_tasks:
                print("Scheduling background cache update...")
                background_tasks.add_task(update_cache_in_background, exchange)
            else:
                # If no background_tasks available, start a non-awaited task
                print("Starting cache update task...")
                asyncio.create_task(update_cache_in_background(exchange))
            
            # Return the stale cached data while the refresh happens in the background
            return process_cached_data(
                cached_data, page, page_size, quote_currency, 
                sort_by, sort_desc, search
            )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch cryptocurrency data: {str(e)}")


@app.get("/api/crypto/{symbol}")
async def get_crypto_detail(symbol: str, exchange: CryptoExchange = Depends(get_exchange)):
    """Get detailed information for a specific cryptocurrency"""
    try:
        # Get ticker for the specific symbol
        ticker = exchange.exchange.fetch_ticker(symbol)
        
        # Get more detailed data if available
        order_book = exchange.get_order_book(symbol, limit=20)
        
        # Enhance the order book with additional statistics and explanations
        order_book_stats = {}
        
        if order_book:
            # Get existing statistics from order book
            order_book_stats = {
                "bids": order_book.get("bids", []),
                "asks": order_book.get("asks", []),
                "datetime": order_book.get("datetime"),
                "timestamp": order_book.get("timestamp")
            }
            
            # Add top bid/ask values with explanations
            if order_book.get("top_bid"):
                order_book_stats["top_bid"] = {
                    "value": order_book.get("top_bid"),
                    "explanation": "The highest price that buyers are currently willing to pay for this cryptocurrency"
                }
            
            if order_book.get("top_ask"):
                order_book_stats["top_ask"] = {
                    "value": order_book.get("top_ask"),
                    "explanation": "The lowest price that sellers are currently willing to accept for this cryptocurrency"
                }
            
            # Add average bid/ask prices with explanations
            if order_book.get("average_bid") is not None:
                order_book_stats["average_bid"] = {
                    "value": order_book.get("average_bid"),
                    "explanation": "The arithmetic mean of all bid prices in the order book, representing the average buyer price intention"
                }
            
            if order_book.get("average_ask") is not None:
                order_book_stats["average_ask"] = {
                    "value": order_book.get("average_ask"),
                    "explanation": "The arithmetic mean of all ask prices in the order book, representing the average seller price intention"
                }
            
            # Add spread calculation with explanation
            if order_book.get("spread") is not None:
                spread = order_book.get("spread")
                spread_percentage = (spread / order_book.get("top_bid")[0]) * 100 if order_book.get("top_bid") else None
                
                order_book_stats["spread"] = {
                    "value": spread,
                    "percentage": spread_percentage,
                    "explanation": "The difference between the best ask price and the best bid price. A smaller spread typically indicates higher liquidity and trading activity."
                }
            
            # Add weighted average values with explanations
            if order_book.get("weighted_bid") is not None:
                order_book_stats["weighted_bid"] = {
                    "value": order_book.get("weighted_bid"),
                    "explanation": "The volume-weighted average price (VWAP) of all bids, giving more importance to price levels with higher order volumes"
                }
            
            if order_book.get("weighted_ask") is not None:
                order_book_stats["weighted_ask"] = {
                    "value": order_book.get("weighted_ask"),
                    "explanation": "The volume-weighted average price (VWAP) of all asks, giving more importance to price levels with higher order volumes"
                }
            
            # Add liquidity assessment
            bid_volume = sum(bid[1] for bid in order_book.get("bids", [])) if order_book.get("bids") else 0
            ask_volume = sum(ask[1] for ask in order_book.get("asks", [])) if order_book.get("asks") else 0
            
            order_book_stats["liquidity"] = {
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
                "ratio": bid_volume / ask_volume if ask_volume > 0 else None,
                "explanation": "The ratio between buy and sell order volumes indicates market sentiment. A ratio > 1 suggests stronger buying pressure, while a ratio < 1 suggests stronger selling pressure."
            }
            
            # Add general descriptions for bids and asks
            order_book_stats["descriptions"] = {
                "bids": "Bids are buy orders placed by traders willing to purchase the cryptocurrency at specific prices. They are sorted in descending order with the highest bid (best price for sellers) at the top.",
                "asks": "Asks are sell orders placed by traders willing to sell the cryptocurrency at specific prices. They are sorted in ascending order with the lowest ask (best price for buyers) at the top."
            }
        
        return {
            "symbol": symbol,
            "price": ticker.get('last', 0),
            "change": ticker.get('change', 0),
            "percentage_change": ticker.get('percentage', 0),
            "high_24h": ticker.get('high', 0),
            "low_24h": ticker.get('low', 0),
            "volume_24h": ticker.get('quoteVolume', 0),
            "order_book": order_book,
            "order_book_stats": order_book_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {symbol}: {str(e)}")


@app.get("/api/markets")
async def get_markets(exchange: CryptoExchange = Depends(get_exchange)):
    """Get available markets and quote currencies"""
    try:
        #exchange_info = exchange.get_exchange_info()
        
        # Get unique quote currencies
        exchange_info = exchange.get_exchange_info()
        markets=exchange_info.get("crypto_currencies_list")
        #print("AA",markets)  # Uncommented for debugging
        quote_currencies = set()
        
        for symbol in markets:
            if '/' in symbol:
                quote = symbol.split('/')[1]
                quote_currencies.add(quote)
        
        return {
            "exchange": exchange_info.get('name', 'Unknown'),
            "quote_currencies": sorted(list(quote_currencies)),
            "market_count": exchange_info.get('total_markets', 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        print("error is ",traceback.format_exc())
        
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")


@app.get("/api/currency-info")
async def get_currency_info(
    exchange: CryptoExchange = Depends(get_exchange),
    symbols: str = Query(None, description="Comma-separated list of currency symbols (e.g., BTC,ETH,ADA)"),
    convert: str = Query("USD", description="Currency to convert values to (e.g., USD, EUR)")
):
    """Get detailed currency information from CoinMarketCap including market cap, supply, and price metrics"""
    try:
        if not symbols:
            raise HTTPException(status_code=400, detail="Please provide at least one currency symbol")
            
        # Split comma-separated symbols into a list
        symbol_list = [symbol.strip().upper() for symbol in symbols.split(",")]
        
        # Call the exchange function to get market data
        market_data = exchange.get_market_volume_by_symbols(symbol_list, convert=convert)
        
        if not market_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No data available for the provided symbols: {symbols}"
            )
        
        # Filter out None values (symbols that weren't found)
        valid_data = {k: v for k, v in market_data.items() if v is not None}
        
        # Get additional market metrics
        additional_metrics = exchange.calculate_market_metrics(symbol_list, convert=convert)
        
        # Add additional metrics to the response data
        for symbol, metrics in additional_metrics.items():
            if symbol in valid_data:
                valid_data[symbol]['additional_metrics'] = metrics
        
        return {
            "data": valid_data,
            "convert": convert,
            "count": len(valid_data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch currency information: {str(e)}")


async def update_cache_in_background(exchange: CryptoExchange):
    """Update the cryptocurrency data cache in the background"""
    print("Starting background cache update...")
    try:
        # Fetch all tickers from the exchange
        all_tickers = exchange.get_tickers()
        
        # Process and filter data
        crypto_data = []
        
        quote_symbols = exchange.get_quote_symbols(all_tickers)
        market_data = exchange.get_market_volume_by_symbols(quote_symbols, convert='USD')

        for symbol, ticker in all_tickers.items():
            # Extract base symbol (cryptocurrency name)
            base_symbol = symbol.split('/')[0]
            
            # Get quote currency from symbol
            symbol_quote = symbol.split('/')[1] if '/' in symbol else 'UNKNOWN'
            
            # Sometimes market cap might not be available from all exchanges
            market_cap = exchange.get_market_volume(base_symbol, market_data=market_data)
                
            last = ticker.get("pricing_information").get('last', 0)
            if not last:
                last = 0
            if last == 0:
                continue 
                
            entry = CryptoListing(
                symbol=symbol,
                name=base_symbol,
                price=float(last),
                percentage_change=float(ticker.get("change").get('percentage', 0) or 0),
                volume_24h=float(ticker.get("volume").get('quote_volume', 0) or 0),
                market_cap=market_cap
            )
            crypto_data.append(entry.dict())
            
        # Update the global cache
        await update_global_cache(crypto_data)
        print("Background cache update completed successfully")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in background cache update: {e}")

# Function defined earlier in the file

def run():
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
