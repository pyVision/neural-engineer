#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CryptoExchange Class

This module provides a wrapper around the CCXT library for cryptocurrency exchange interactions.
It simplifies working with market data, order books, trades, and account information.
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
import traceback

class CryptoExchange:
    """
    A wrapper class for cryptocurrency exchange interactions using the CCXT library.
    
    This class provides methods to:
    - Initialize exchange connections
    - Retrieve market data (tickers, order books, trades)
    - Fetch historical price data
    - Check exchange status
    - Access account information
    
    Attributes:
        exchange: The CCXT exchange instance
        markets: Dictionary of markets available on the exchange
        currencies: Dictionary of currencies available on the exchange
        exchange_info: Information about the exchange including status and available markets
    """

    def __init__(self):
        """Initialize the CryptoExchange instance."""
        self.exchange = None
        self.markets = None
        self.currencies = None
        self.exchange_info = None

    def describe(self):
        """
        Override the describe method to add custom properties.
        """
        return self.exchange.describe() if self.exchange else {}
    
    def get_exchanges(self):
        """
        Get a list of all exchanges available in ccxt.
        
        Returns:
            list: List of exchange IDs supported by CCXT
        """
        return ccxt.exchanges

    def init_exchange(self, exchange_id, api_key=None, api_secret=None):
        """
        Initialize a specific exchange by its ID.
        
        Args:
            exchange_id (str): The ID of the exchange (e.g., 'binance', 'coinbase', 'kraken')
            api_key (str, optional): API key for authenticated requests
            api_secret (str, optional): API secret for authenticated requests
            
        Returns:
            object: The initialized exchange instance or None if initialization fails
        """
        try:
            self.exchange = getattr(ccxt, exchange_id)({
                'enableRateLimit': True  # Always enable rate limiting to avoid bans
            })
            
            if api_key and api_secret:
                self.exchange.apiKey = api_key
                self.exchange.secret = api_secret
                
            return self.exchange
        except AttributeError:
            print(f"Exchange {exchange_id} not found.")
            return None
    
    def is_exchange_active(self):
        """
        Check if the exchange is operational.
        
        Returns:
            bool: True if the exchange is operational, False otherwise
        """
        if not self.exchange:
            return False
            
        try:
            exchange_info = self.exchange.fetch_status()
            return exchange_info['status'] == 'ok'
        except Exception as e:
            print(f"Error checking exchange status: {e}")
            return False

    def get_exchange_info(self, exchange_id=None):
        """
        Get comprehensive information about the exchange.
        
        Args:
            exchange_id (str, optional): The ID of the exchange. If None, uses the already initialized exchange.
            
        Returns:
            dict: Detailed information about the exchange or None if an error occurs
        """
        if exchange_id and not self.exchange:
            self.init_exchange(exchange_id)
            
        if not self.exchange:
            return None
            
        try:
            exchange_info = self.exchange.fetch_status()
            server_time = self.exchange.fetchTime()

            # Load markets and currencies
            markets = self.exchange.load_markets()
            currencies = self.exchange.fetch_currencies()

            self.markets = markets
            self.currencies = currencies

            # Categorize currencies
            crypto_currencies = []
            fiat_currencies = []
            for currency in currencies.values():
                if currency['type'] == 'crypto' and currency['active']:
                    crypto_currencies.append(currency['code'])
                if currency['type'] == 'fiat' and currency['active']:
                    if currency['info'].get('isLegalMoney', False):
                        fiat_currencies.append(currency['code'])

            # Categorize markets
            final_crypto_currencies = []
            final_fiat_currencies = []
            for market in markets.values():
                if market['active'] and market['info'].get("status", "") == 'TRADING':
                    if market['base'] in crypto_currencies or market['quote'] in crypto_currencies:
                        final_crypto_currencies.append(market["id"])
                    
                    if market['base'] in fiat_currencies or market['quote'] in fiat_currencies:
                        final_fiat_currencies.append(market["id"])
            
            # Create comprehensive exchange info dictionary
            self.exchange_info = {
                'id': self.exchange.id,
                'name': self.exchange.name if hasattr(self.exchange, 'name') else self.exchange.id,
                'updated': server_time,
                'crypto_currencies': len(final_crypto_currencies),
                'fiat_currencies': len(final_fiat_currencies),
                'total_markets': len(final_crypto_currencies) + len(final_fiat_currencies),
                'crypto_currencies_list': final_crypto_currencies,
                'fiat_currencies_list': final_fiat_currencies,
                'status': exchange_info['status'],
                'server_time': datetime.fromtimestamp(server_time / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'server_time_unix': server_time,
                'active': self.is_exchange_active(),
            }
        
            return self.exchange_info
        except Exception as e:
            traceback.print_exc()
            print(f"Error fetching info for {self.exchange.id}: {e}")
            return None
    
    def fetch_historical_data(self, symbol, timeframe, start_timestamp, end_timestamp):
        """
        Fetch historical OHLCV data in batches, respecting exchange limits.
        
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTC/USDT')
            timeframe (str): Timeframe for candles (e.g., '1m', '1h', '1d')
            start_timestamp (str or int): Start time as timestamp or ISO 8601 string
            end_timestamp (str or int): End time as timestamp or ISO 8601 string
            
        Returns:
            DataFrame: Pandas DataFrame with OHLCV data or empty DataFrame if no data
        """
        if not self.exchange:
            print("Exchange not initialized.")
            return pd.DataFrame()
            
        all_candles = []
        
        # Convert string timestamps to milliseconds if needed
        if isinstance(start_timestamp, str):
            start_timestamp = self.exchange.parse8601(start_timestamp)
        if isinstance(end_timestamp, str):
            end_timestamp = self.exchange.parse8601(end_timestamp)
            
        since = start_timestamp
        limit = 1000  # Maximum candles per request
        
        print(f"Fetching {symbol} {timeframe} data from {datetime.fromtimestamp(start_timestamp/1000)} to {datetime.fromtimestamp(end_timestamp/1000)}")
        
        try:
            while since < end_timestamp:
                print(f"Fetching batch starting at {datetime.fromtimestamp(since/1000)}")
                candles = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                
                if (not candles) or len(candles) <= 0:
                    print("No more candles returned")
                    break
                    
                print(f"Received {len(candles)} candles")
                all_candles.extend(candles)

                since = int(candles[-1][0]) + 1  # Next timestamp after the last received candle
                
                # If we received less than the requested limit, we've reached the end
                if len(candles) < limit:
                    print(f"Received less than {limit} candles, reached the end")
                    break
                    
                # Respect the rate limit
                time.sleep(self.exchange.rateLimit / 1000)  
            
            # Convert to DataFrame
            if all_candles:
                if isinstance(all_candles[0], list):
                    print("Creating DataFrame from list of lists")
                    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    return df
                else:
                    # If all_candles is a list of DataFrames, concatenate them
                    print("Concatenating DataFrames")
                    df = pd.concat(all_candles, ignore_index=True)
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_tickers(self, symbols=None):
        """
        Get tickers for specified markets or all markets on the exchange.
        
        Args:
            symbols (list, optional): List of symbols to get tickers for (e.g., ['BTC/USDT', 'ETH/USDT'])
            
        Returns:
            dict: Dictionary of ticker data by symbol or None if an error occurs
        """
        if not self.exchange:
            print("Exchange not initialized.")
            return None
            
        try:
            result = {}
            
            # Fetch tickers based on whether symbols are provided
            if symbols:
                # Fetch specific tickers
                tickers = self.exchange.fetch_tickers(symbols)
            else:
                # Fetch all tickers
                tickers = self.exchange.fetch_tickers()
                
            for ticker in tickers.values():
                data = {
                    'symbol': ticker['symbol'],
                    'timestamp': datetime.fromtimestamp(ticker['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamp_unix': ticker['timestamp'],
                    
                    'pricing_information': {
                        'high': ticker['high'],
                        'low': ticker['low'],
                        'open': ticker['open'],
                        'last': ticker['last'],
                        'close': ticker['close'],
                        'prev_close': ticker['previousClose'],
                    },

                    'order_book': {
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'bid_volume': ticker['bidVolume'],
                        'ask_volume': ticker['askVolume'],
                    },

                    'volume': {
                        'base_volume': ticker['baseVolume'],
                        'quote_volume': ticker['quoteVolume'],
                    },

                    'change': {
                        'price_change': ticker['change'],
                        'percentage': ticker['percentage'],
                        'average': ticker['average'],
                        'vwap': ticker['vwap'],
                    },
                    
                    'last_trade': {
                        'timestamp': ticker['timestamp'],
                        'price': ticker['last'],
                        'amount': ticker['last'],
                    }
                }

                result[ticker['symbol']] = data

            return result
        except Exception as e:
            print(f"Error fetching tickers: {e}")
            return None

    def get_order_book(self, symbol, limit=5, best=False):
        """
        Get the order book for a specific symbol.
        
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTC/USDT')
            limit (int): How many price levels to include
            best (bool): If True, only get best bid and ask
            
        Returns:
            dict: Order book information or None if an error occurs
        """
        if not self.exchange:
            print("Exchange not initialized.")
            return None
            
        try:
            order_book = {}
            
            if best:
                # Get only best bid and ask
                ticker = self.exchange.fetch_bids_asks(symbol)
                order_book = {
                    'symbol': symbol,
                    'datetime': ticker['timestamp'],
                    'linux_timestamp': ticker['timestamp'],
                    'bids': [ticker['bid'], ticker['bidVolume']],
                    'asks': [ticker['ask'], ticker['askVolume']],
                    'timestamp': ticker['timestamp'],
                }
                order_book['spread'] = order_book['asks'][0] - order_book['bids'][0] if order_book['asks'] and order_book['bids'] else None
                order_book['top_bid'] = order_book['bids'] if order_book['bids'] else None
                order_book['top_ask'] = order_book['asks'] if order_book['asks'] else None
                order_book['average_bid'] = None
                order_book['average_ask'] = None
                order_book['weighted_bid'] = None
                order_book['weighted_ask'] = None
            else:
                # Get full order book
                order_book_data = self.exchange.fetch_order_book(symbol, limit)
                order_book = {
                    'symbol': symbol,
                    'timestamp': order_book_data['timestamp'],
                    'datetime': datetime.fromtimestamp(order_book_data['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S') if order_book_data['timestamp'] else None,
                    'bids': order_book_data['bids'],
                    'asks': order_book_data['asks'],
                }
            
            if not order_book.get('timestamp'):
                order_book['timestamp'] = time.time() * 1000 

            # Calculate additional metrics
            if not best:
                order_book['top_bid'] = order_book['bids'][0] if order_book['bids'] else None
                order_book['top_ask'] = order_book['asks'][0] if order_book['asks'] else None
                order_book['average_bid'] = sum([bid[0] for bid in order_book['bids']]) / len(order_book['bids']) if order_book['bids'] else None
                order_book['average_ask'] = sum([ask[0] for ask in order_book['asks']]) / len(order_book['asks']) if order_book['asks'] else None
                order_book['spread'] = order_book['top_ask'][0] - order_book['top_bid'][0] if order_book['top_bid'] and order_book['top_ask'] else None
                
                if order_book['bids']:
                    bid_sum = sum([bid[1] for bid in order_book['bids']])
                    order_book['weighted_bid'] = sum([bid[0] * bid[1] for bid in order_book['bids']]) / bid_sum if bid_sum else None
                else:
                    order_book['weighted_bid'] = None
                    
                if order_book['asks']:
                    ask_sum = sum([ask[1] for ask in order_book['asks']])
                    order_book['weighted_ask'] = sum([ask[0] * ask[1] for ask in order_book['asks']]) / ask_sum if ask_sum else None
                else:
                    order_book['weighted_ask'] = None

            return order_book
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {e}")
            return None
        
    def get_trades(self, symbol, since=None, limit=5):
        """
        Get recent trades for a specific symbol.
        
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTC/USDT')
            since (int, optional): Timestamp to fetch trades from
            limit (int): Maximum number of trades to fetch
            
        Returns:
            dict: Trade information with buy/sell analysis or None if an error occurs
        """
        if not self.exchange:
            print("Exchange not initialized.")
            return None
            
        try:
            trades = self.exchange.fetch_trades(symbol, since, limit)

            # Convert to DataFrame for easier analysis
            trades_df = pd.DataFrame([
                {
                    'timestamp': datetime.fromtimestamp(trade['timestamp'] / 1000),
                    'linux_timestamp': trade['timestamp'],
                    'side': trade['side'],
                    'price': trade['price'],
                    'amount': trade['amount'],
                    'cost': trade['cost'],
                    'total': trade['price'] * trade['amount'],
                    'id': trade['id']
                } for trade in trades
            ])

            # Aggregate trade data
            result = {
                'symbol': symbol,
                'timestamp': trades_df['timestamp'].iloc[0] if not trades_df.empty else None,
                'linux_timestamp': trades_df['linux_timestamp'].iloc[0] if not trades_df.empty else None,
            }
            
            # Split trades by side (buy/sell)
            buy_trades = trades_df[trades_df['side'] == 'buy']
            sell_trades = trades_df[trades_df['side'] == 'sell']
            
            # Calculate buy metrics
            result['buy'] = buy_trades
            result['buy_total'] = buy_trades['total'].sum() if not buy_trades.empty else 0
            result['buy_count'] = len(buy_trades)
            result['buy_average'] = buy_trades['price'].mean() if not buy_trades.empty else None
            
            if not buy_trades.empty and buy_trades['amount'].sum() > 0:
                result['buy_weighted_average'] = buy_trades['total'].sum() / buy_trades['amount'].sum() 
            else:
                result['buy_weighted_average'] = None
                
            # Calculate sell metrics
            result['sell'] = sell_trades
            result['sell_total'] = sell_trades['total'].sum() if not sell_trades.empty else 0
            result['sell_count'] = len(sell_trades)
            result['sell_average'] = sell_trades['price'].mean() if not sell_trades.empty else None
            
            if not sell_trades.empty and sell_trades['amount'].sum() > 0:
                result['sell_weighted_average'] = sell_trades['total'].sum() / sell_trades['amount'].sum()
            else:
                result['sell_weighted_average'] = None

            return result
        except Exception as e:
            print(f"Error fetching trades for {symbol}: {e}")
            return None
        
    def get_balance(self):
        """
        Get the account balance.
        
        Returns:
            dict: Balance information or None if an error occurs
        """
        if not self.exchange:
            print("Exchange not initialized.")
            return None
            
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return None
        
    def get_orders(self, symbol, order_type='open', order_id=None):
        """
        Get orders for a specific symbol.
        
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTC/USDT')
            order_type (str): Type of orders to get ('open', 'closed', 'all')
            order_id (str, optional): ID of specific order to fetch
            
        Returns:
            list: List of orders or None if an error occurs
        """
        if not self.exchange:
            print("Exchange not initialized.")
            return None
            
        try:
            if order_id and order_type == 'open':
                return self.exchange.fetch_open_order(order_id, symbol)
                
            if order_type == 'open':
                return self.exchange.fetch_open_orders(symbol)
            elif order_type == 'closed':
                return self.exchange.fetch_closed_orders(symbol)
            elif order_type == 'all':
                return self.exchange.fetch_orders(symbol)
            else:
                raise ValueError("Invalid order type. Use 'open', 'closed', or 'all'.")
                
        except Exception as e:
            print(f"Error fetching {order_type} orders for {symbol}: {e}")
            return None

# Example usage:
if __name__ == "__main__":
    # Initialize the exchange
    exchange = CryptoExchange()
    exchange.init_exchange("binance")  # No API keys means public data only
    
    # Get exchange info
    info = exchange.get_exchange_info()
    if info:
        print(f"Connected to {info['name']} exchange with {info['total_markets']} markets")
    
    # Get ticker data
    btc_ticker = exchange.get_tickers(['BTC/USDT'])
    if btc_ticker:
        price = btc_ticker['BTC/USDT']['pricing_information']['last']
        print(f"Current BTC/USDT price: ${price}")
    
    # Get order book
    order_book = exchange.get_order_book('BTC/USDT', limit=5)
    if order_book:
        print(f"BTC/USDT spread: ${order_book['spread']}")
        
        print("\nTop 5 bids:")
        for price, amount in order_book['bids']:
            print(f"${price:.2f}: {amount:.6f} BTC (${price*amount:.2f})")
            
        print("\nTop 5 asks:")
        for price, amount in order_book['asks']:
            print(f"${price:.2f}: {amount:.6f} BTC (${price*amount:.2f})")
