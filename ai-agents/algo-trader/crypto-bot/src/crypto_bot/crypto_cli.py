#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crypto CLI - Command-line interface for the CryptoExchange class

This module provides a command-line utility for interacting with cryptocurrency exchanges
using the CryptoExchange wrapper class. It supports various commands for retrieving market data,
analyzing historical prices, and displaying order book information.

Example usage:
    # List all supported exchanges
    python crypto_cli.py list-exchanges

    # Get exchange info
    python crypto_cli.py exchange-info --exchange binance

    # Get current ticker price for BTC/USDT
    python crypto_cli.py ticker --exchange binance --symbol BTC/USDT

    # Fetch historical data for BTC/USDT
    python crypto_cli.py historical --exchange binance --symbol BTC/USDT --timeframe 1h --start 2023-01-01 --end 2023-01-02

    # Get order book for BTC/USDT
    python crypto_cli.py orderbook --exchange binance --symbol BTC/USDT --limit 5

    # Get recent trades for BTC/USDT
    python crypto_cli.py trades --exchange binance --symbol BTC/USDT --limit 10
"""

import argparse
import json
import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate

# Add the parent directory to sys.path if needed
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the CryptoExchange class
from crypto_exchange import CryptoExchange

def load_api_credentials():
    """Load API credentials from environment variables or .env file."""
    load_dotenv()
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    return api_key, api_secret

def list_exchanges(args):
    """List all available exchanges supported by CCXT."""
    cx = CryptoExchange()
    exchanges = cx.get_exchanges()
    
    print(f"Available Exchanges ({len(exchanges)}):")
    for i, exchange in enumerate(sorted(exchanges)):
        print(f"{i+1}. {exchange}")

def get_exchange_info(args):
    """Get comprehensive information about an exchange."""
    cx = CryptoExchange()
    
    # Initialize the exchange
    api_key, api_secret = load_api_credentials()
    cx.init_exchange(args.exchange, api_key, api_secret)
    
    # Get exchange info
    info = cx.get_exchange_info()
    
    if info:
        print(f"\n{'=' * 50}")
        print(f"Exchange: {info['name']} ({info['id']})")
        print(f"Status: {info['status']}")
        print(f"Active: {info['active']}")
        print(f"Server Time: {info['server_time']}")
        print(f"Markets: {info['total_markets']} total")
        print(f"  - Crypto Markets: {info['crypto_currencies']}")
        print(f"  - Fiat Markets: {info['fiat_currencies']}")
        
        if args.verbose:
            print("\nCryptocurrency Markets Sample:")
            for market in info['crypto_currencies_list'][:10]:
                print(f"  - {market}")
                
            print("\nFiat Markets Sample:")
            for market in info['fiat_currencies_list'][:10]:
                print(f"  - {market}")
    else:
        print(f"Failed to retrieve information for {args.exchange}")

def get_ticker(args):
    """Get current ticker information for a specific symbol."""
    cx = CryptoExchange()
    
    # Initialize the exchange
    api_key, api_secret = load_api_credentials()
    cx.init_exchange(args.exchange, api_key, api_secret)
    
    # Get ticker information
    symbols = args.symbol.split(',')
    tickers = cx.get_tickers(symbols)
    
    if tickers:
        for symbol, ticker in tickers.items():
            price_info = ticker['pricing_information']
            
            print(f"\n{'=' * 50}")
            print(f"Ticker: {symbol}")
            print(f"Timestamp: {ticker['timestamp']}")
            print(f"\nPrice Information:")
            print(f"  Current: ${price_info['last']}")
            print(f"  24h High: ${price_info['high']}")
            print(f"  24h Low: ${price_info['low']}")
            print(f"  24h Open: ${price_info['open']}")
            print(f"  24h Close: ${price_info['close']}")
            
            print(f"\nTrading Volume:")
            print(f"  Base Volume: {ticker['volume']['base_volume']}")
            print(f"  Quote Volume: {ticker['volume']['quote_volume']}")
            
            print(f"\nPrice Changes:")
            print(f"  Absolute: {ticker['change']['price_change']}")
            print(f"  Percentage: {ticker['change']['percentage']}%")
            
            print(f"\nOrder Book Snapshot:")
            print(f"  Best Bid: ${ticker['order_book']['bid']} ({ticker['order_book']['bid_volume']})")
            print(f"  Best Ask: ${ticker['order_book']['ask']} ({ticker['order_book']['ask_volume']})")
            
            if args.json:
                print("\nFull JSON Data:")
                print(json.dumps(ticker, indent=2))
    else:
        print(f"Failed to retrieve ticker information for {args.symbol} on {args.exchange}")

def get_historical_data(args):
    """Fetch historical OHLCV data for a specific symbol and timeframe."""
    cx = CryptoExchange()
    
    # Initialize the exchange
    api_key, api_secret = load_api_credentials()
    cx.init_exchange(args.exchange, api_key, api_secret)
    
    # Parse start and end dates
    start_date = f"{args.start}T00:00:00Z" if "T" not in args.start else args.start
    end_date = f"{args.end}T23:59:59Z" if "T" not in args.end else args.end
    
    # Fetch historical data
    df = cx.fetch_historical_data(args.symbol, args.timeframe, start_date, end_date)
    
    if not df.empty:
        print(f"\nRetrieved {len(df)} candles for {args.symbol} ({args.timeframe})")
        
        if args.output:
            # Save to CSV or JSON
            if args.output.endswith('.csv'):
                df.to_csv(args.output, index=False)
            elif args.output.endswith('.json'):
                df.to_json(args.output, orient='records', date_format='iso')
            print(f"Data saved to {args.output}")
        else:
            # Display in console
            if len(df) > 10 and not args.show_all:
                print("\nFirst 5 candles:")
                print(tabulate(df.head(5), headers='keys', tablefmt='pretty'))
                print("\nLast 5 candles:")
                print(tabulate(df.tail(5), headers='keys', tablefmt='pretty'))
            else:
                print(tabulate(df, headers='keys', tablefmt='pretty'))
            
            # Display basic statistics
            if args.stats:
                print("\nBasic Statistics:")
                stats = df.describe()
                print(tabulate(stats, headers='keys', tablefmt='pretty'))
    else:
        print(f"No historical data available for {args.symbol} on {args.exchange} for the specified time period")

def get_order_book(args):
    """Get the order book for a specific symbol."""
    cx = CryptoExchange()
    
    # Initialize the exchange
    api_key, api_secret = load_api_credentials()
    cx.init_exchange(args.exchange, api_key, api_secret)
    
    # Get order book
    order_book = cx.get_order_book(args.symbol, limit=args.limit, best=args.best)
    
    if order_book:
        print(f"\n{'=' * 50}")
        print(f"Order Book: {args.symbol}")
        print(f"Timestamp: {order_book.get('datetime', 'N/A')}")
        
        if 'spread' in order_book and order_book['spread'] is not None:
            print(f"Spread: ${order_book['spread']:.2f}")
        
        if not args.best:
            # Display bid and ask information
            print(f"\nTop {len(order_book['bids'][:args.display_limit])} Bids (Buy Orders):")
            for i, (price, amount) in enumerate(order_book['bids'][:args.display_limit]):
                print(f"  {i+1}. Price: ${price:.2f}, Amount: {amount:.6f}, Total: ${price*amount:.2f}")
            
            print(f"\nTop {len(order_book['asks'][:args.display_limit])} Asks (Sell Orders):")
            for i, (price, amount) in enumerate(order_book['asks'][:args.display_limit]):
                print(f"  {i+1}. Price: ${price:.2f}, Amount: {amount:.6f}, Total: ${price*amount:.2f}")
        
            if 'weighted_bid' in order_book and order_book['weighted_bid']:
                print(f"\nWeighted Average Bid: ${order_book['weighted_bid']:.2f}")
            if 'weighted_ask' in order_book and order_book['weighted_ask']:
                print(f"\nWeighted Average Ask: ${order_book['weighted_ask']:.2f}")
        else:
            # Display only best bid and ask
            print("\nBest Bid (Buy):")
            print(f"  Price: ${order_book['bids'][0]:.2f}, Volume: {order_book['bids'][1]:.6f}")
            
            print("\nBest Ask (Sell):")
            print(f"  Price: ${order_book['asks'][0]:.2f}, Volume: {order_book['asks'][1]:.6f}")
            
        if args.json:
            print("\nFull Order Book JSON:")
            # Remove DataFrames from the output as they're not JSON serializable
            json_order_book = {k: v for k, v in order_book.items() if k not in ['buy', 'sell']}
            print(json.dumps(json_order_book, indent=2))
    else:
        print(f"Failed to retrieve order book for {args.symbol} on {args.exchange}")

def get_trades(args):
    """Get recent trades for a specific symbol."""
    cx = CryptoExchange()
    
    # Initialize the exchange
    api_key, api_secret = load_api_credentials()
    cx.init_exchange(args.exchange, api_key, api_secret)
    
    # Get recent trades
    trades_data = cx.get_trades(args.symbol, limit=args.limit)
    
    if trades_data:
        print(f"\n{'=' * 50}")
        print(f"Recent Trades for {args.symbol}")
        print(f"Timestamp: {trades_data['timestamp']}")
        
        print("\nTrade Summary:")
        print(f"  Buy Trades: {trades_data['buy_count']}")
        print(f"  Sell Trades: {trades_data['sell_count']}")
        print(f"  Buy Volume: {trades_data['buy_total']:.2f}")
        print(f"  Sell Volume: {trades_data['sell_total']:.2f}")
        
        if trades_data['buy_average']:
            print(f"  Average Buy Price: ${trades_data['buy_average']:.2f}")
        if trades_data['sell_average']:
            print(f"  Average Sell Price: ${trades_data['sell_average']:.2f}")
        if trades_data['buy_weighted_average']:
            print(f"  Weighted Buy Price: ${trades_data['buy_weighted_average']:.2f}")
        if trades_data['sell_weighted_average']:
            print(f"  Weighted Sell Price: ${trades_data['sell_weighted_average']:.2f}")
        
        # Display individual trades if needed
        if args.show_trades:
            print("\nBuy Trades:")
            if 'buy' in trades_data and not trades_data['buy'].empty:
                display_df = trades_data['buy'][['timestamp', 'price', 'amount', 'total']]
                print(tabulate(display_df, headers='keys', tablefmt='pretty'))
            else:
                print("  No buy trades in this batch")
                
            print("\nSell Trades:")
            if 'sell' in trades_data and not trades_data['sell'].empty:
                display_df = trades_data['sell'][['timestamp', 'price', 'amount', 'total']]
                print(tabulate(display_df, headers='keys', tablefmt='pretty'))
            else:
                print("  No sell trades in this batch")
    else:
        print(f"Failed to retrieve trades for {args.symbol} on {args.exchange}")

def get_balance(args):
    """Get the account balance."""
    cx = CryptoExchange()
    
    # Initialize the exchange
    api_key, api_secret = load_api_credentials()
    if not api_key or not api_secret:
        print("API credentials required for balance information")
        print("Please set API_KEY and API_SECRET environment variables")
        return
        
    cx.init_exchange(args.exchange, api_key, api_secret)
    
    # Get balance
    balance = cx.get_balance()
    
    if balance:
        print(f"\n{'=' * 50}")
        print(f"Account Balance on {args.exchange}")
        
        # Total balance info
        if 'total' in balance and balance['total']:
            print("\nTotal Balance (including orders):")
            # Filter zero balances unless --show-all is specified
            non_zero = {k: v for k, v in balance['total'].items() if v > 0 or args.show_zero}
            
            # Create a DataFrame for better display
            df = pd.DataFrame(list(non_zero.items()), columns=['Currency', 'Amount'])
            df = df.sort_values('Amount', ascending=False)
            
            # Display as table
            print(tabulate(df, headers='keys', tablefmt='pretty', showindex=False))
            
        # Free balance (available for trading)
        if 'free' in balance and balance['free']:
            print("\nFree Balance (available for trading):")
            non_zero = {k: v for k, v in balance['free'].items() if v > 0 or args.show_zero}
            
            df = pd.DataFrame(list(non_zero.items()), columns=['Currency', 'Available'])
            df = df.sort_values('Available', ascending=False)
            
            print(tabulate(df, headers='keys', tablefmt='pretty', showindex=False))
            
        # Used balance (in open orders)
        if 'used' in balance and balance['used']:
            print("\nUsed Balance (in open orders):")
            non_zero = {k: v for k, v in balance['used'].items() if v > 0 or args.show_zero}
            
            if non_zero:
                df = pd.DataFrame(list(non_zero.items()), columns=['Currency', 'In Orders'])
                df = df.sort_values('In Orders', ascending=False)
                
                print(tabulate(df, headers='keys', tablefmt='pretty', showindex=False))
            else:
                print("  No funds currently in orders")
    else:
        print(f"Failed to retrieve balance from {args.exchange}")

def get_exchanges_list(args):
    """Get detailed information about all supported exchanges or a specific one."""
    import ccxt
    
    if args.exchange:
        # Get info about a specific exchange
        try:
            exchange_class = getattr(ccxt, args.exchange)
            exchange = exchange_class()
            info = exchange.describe()
            
            print(f"\n{'=' * 50}")
            print(f"Exchange: {info.get('name', args.exchange)}")
            print(f"Countries: {', '.join(info.get('countries', ['Unknown']))}")
            print(f"Version: {info.get('version', 'Unknown')}")
            print(f"Has Public API: {info.get('has', {}).get('publicAPI', False)}")
            print(f"Has Private API: {info.get('has', {}).get('privateAPI', False)}")
            
            print("\nSupported Features:")
            for feature, supported in info.get('has', {}).items():
                if supported:
                    print(f"  - {feature}")
                    
            print("\nRate Limits:")
            for rate_limit in info.get('rateLimit', {}):
                print(f"  - {rate_limit}")
                
            print("\nURL Endpoints:")
            for name, url in info.get('urls', {}).items():
                if isinstance(url, str):
                    print(f"  - {name}: {url}")
            
        except AttributeError:
            print(f"Exchange {args.exchange} not found")
            
    else:
        # List all exchanges with basic info
        exchanges_data = []
        for exchange_id in ccxt.exchanges:
            try:
                exchange_class = getattr(ccxt, exchange_id)
                exchange = exchange_class()
                info = exchange.describe()
                
                exchanges_data.append({
                    'id': exchange_id,
                    'name': info.get('name', exchange_id),
                    'countries': ', '.join(info.get('countries', ['Unknown'])),
                    'has_fetchOHLCV': info.get('has', {}).get('fetchOHLCV', False),
                    'has_fetchTicker': info.get('has', {}).get('fetchTicker', False),
                })
            except Exception as e:
                # Skip exchanges that can't be instantiated
                pass
                
        # Convert to DataFrame for nice display
        df = pd.DataFrame(exchanges_data)
        print(tabulate(df, headers='keys', tablefmt='pretty', showindex=False))

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(
        description='Cryptocurrency Exchange CLI',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Global arguments
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List exchanges command
    list_parser = subparsers.add_parser('list-exchanges', help='List all supported exchanges')
    list_parser.set_defaults(func=list_exchanges)
    
    # Exchange info command
    info_parser = subparsers.add_parser('exchange-info', help='Get exchange information')
    info_parser.add_argument('--exchange', required=True, help='Exchange ID (e.g., binance)')
    info_parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    info_parser.set_defaults(func=get_exchange_info)
    
    # Ticker command
    ticker_parser = subparsers.add_parser('ticker', help='Get ticker information')
    ticker_parser.add_argument('--exchange', required=True, help='Exchange ID (e.g., binance)')
    ticker_parser.add_argument('--symbol', required=True, help='Trading pair symbol (e.g., BTC/USDT)')
    ticker_parser.add_argument('--json', action='store_true', help='Output full JSON data')
    ticker_parser.set_defaults(func=get_ticker)
    
    # Historical data command
    hist_parser = subparsers.add_parser('historical', help='Fetch historical OHLCV data')
    hist_parser.add_argument('--exchange', required=True, help='Exchange ID (e.g., binance)')
    hist_parser.add_argument('--symbol', required=True, help='Trading pair symbol (e.g., BTC/USDT)')
    hist_parser.add_argument('--timeframe', required=True, help='Timeframe (e.g., 1m, 5m, 1h, 1d)')
    hist_parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD or ISO 8601)')
    hist_parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD or ISO 8601)')
    hist_parser.add_argument('--output', help='Output file path (CSV or JSON)')
    hist_parser.add_argument('--show-all', action='store_true', help='Show all candles, not just first/last 5')
    hist_parser.add_argument('--stats', action='store_true', help='Show basic statistics')
    hist_parser.set_defaults(func=get_historical_data)
    
    # Order book command
    ob_parser = subparsers.add_parser('orderbook', help='Get order book')
    ob_parser.add_argument('--exchange', required=True, help='Exchange ID (e.g., binance)')
    ob_parser.add_argument('--symbol', required=True, help='Trading pair symbol (e.g., BTC/USDT)')
    ob_parser.add_argument('--limit', type=int, default=10, help='Order book depth')
    ob_parser.add_argument('--display-limit', type=int, default=5, help='Number of orders to display')
    ob_parser.add_argument('--best', action='store_true', help='Show only best bid/ask')
    ob_parser.add_argument('--json', action='store_true', help='Output full JSON data')
    ob_parser.set_defaults(func=get_order_book)
    
    # Trades command
    trades_parser = subparsers.add_parser('trades', help='Get recent trades')
    trades_parser.add_argument('--exchange', required=True, help='Exchange ID (e.g., binance)')
    trades_parser.add_argument('--symbol', required=True, help='Trading pair symbol (e.g., BTC/USDT)')
    trades_parser.add_argument('--limit', type=int, default=20, help='Maximum number of trades')
    trades_parser.add_argument('--show-trades', action='store_true', help='Show individual trades')
    trades_parser.set_defaults(func=get_trades)
    
    # Balance command
    balance_parser = subparsers.add_parser('balance', help='Get account balance')
    balance_parser.add_argument('--exchange', required=True, help='Exchange ID (e.g., binance)')
    balance_parser.add_argument('--show-zero', action='store_true', help='Show zero balances')
    balance_parser.set_defaults(func=get_balance)
    
    # Exchanges list command
    exchanges_parser = subparsers.add_parser('exchanges', help='Get detailed exchange information')
    exchanges_parser.add_argument('--exchange', help='Specific exchange to get details for')
    exchanges_parser.set_defaults(func=get_exchanges_list)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if a command was specified
    if not hasattr(args, 'func'):
        parser.print_help()
        return
    
    # Execute the command
    try:
        args.func(args)
    except Exception as e:
        if args.debug:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {str(e)}")
            print("Use --debug for more information")

if __name__ == "__main__":
    main()
