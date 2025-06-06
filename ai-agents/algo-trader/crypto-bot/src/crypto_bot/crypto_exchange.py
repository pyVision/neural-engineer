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
import requests
from typing import List, Dict, Optional

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
        self.cmc_api_key = None
        self.cms_results = None 

    def set_cmc_api_key(self, api_key: str):
        """
        Set the CoinMarketCap API key for market cap data.
        
        Args:
            api_key (str): Your CoinMarketCap API key
        """
        self.cmc_api_key = api_key

    def get_market_volume_summary(self, symbols: List[str], convert: str = 'USD') -> Dict:
        """
        Get a summary of market volume data for specified symbols.
        
        Args:
            symbols (List[str]): List of cryptocurrency symbols
            convert (str): Currency to convert values to (default: 'USD')
            
        Returns:
            Dict: Summary statistics of the market data
        """
        market_data = self.get_market_volume_by_symbols(symbols, convert)
        
        if not market_data:
            return None
        
        # Filter out None values (failed requests)
        valid_data = {k: v for k, v in market_data.items() if v is not None}
        
        if not valid_data:
            return {"error": "No valid market data retrieved"}
        
        # Calculate summary statistics
        total_market_cap = sum(data['pricing']['market_cap'] for data in valid_data.values() if data['pricing']['market_cap'])
        total_volume_24h = sum(data['pricing']['volume_24h'] for data in valid_data.values() if data['pricing']['volume_24h'])
        
        summary = {
            'total_symbols_requested': len(symbols),
            'successful_retrievals': len(valid_data),
            'failed_retrievals': len(symbols) - len(valid_data),
            'total_market_cap': total_market_cap,
            'total_volume_24h': total_volume_24h,
            'average_market_cap': total_market_cap / len(valid_data) if valid_data else 0,
            'average_volume_24h': total_volume_24h / len(valid_data) if valid_data else 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'convert_currency': convert
        }
        
        # Add top performers
        if valid_data:
            sorted_by_market_cap = sorted(valid_data.items(), key=lambda x: x[1]['pricing']['market_cap'] or 0, reverse=True)
            sorted_by_volume = sorted(valid_data.items(), key=lambda x: x[1]['pricing']['volume_24h'] or 0, reverse=True)
            
            summary['top_by_market_cap'] = [(symbol, data['pricing']['market_cap']) for symbol, data in sorted_by_market_cap[:5]]
            summary['top_by_volume_24h'] = [(symbol, data['pricing']['volume_24h']) for symbol, data in sorted_by_volume[:5]]
        
        return summary
    

    def get_quote_symbols(self, all_tickers,quote_currency='USDT'):
        """
        Get symbols that match the specified quote currency from the tickers.
        
        Args:
            tickers (dict): Dictionary of ticker data
            quote_currency (str): Quote currency to filter by (default: 'USDT')

        Returns:
            List[str]: List of symbols that match the quote currency
        """

        quote_symbols =[]
        for symbol, ticker in all_tickers.items():
            # Filter by quote currency
            #print(f"Checking symbol: {symbol}")
            if not symbol.endswith(f"/{quote_currency}"):
                continue     

            quote_symbols.append(symbol.replace(f"/{quote_currency}",""))
    
        return quote_symbols

    def get_market_volume_by_symbols(self, symbols: List[str], convert: str = 'USD') -> Dict:
        """
        Get market volume and market cap data for specified symbols using CoinMarketCap API.
        
        Args:
            symbols (List[str]): List of cryptocurrency symbols (e.g., ['BTC', 'ETH', 'ADA'])
            convert (str): Currency to convert values to (default: 'USD')
            
        Returns:
            Dict: Dictionary containing market data for each symbol or None if an error occurs
        """
        if not self.cmc_api_key:
            print("CoinMarketCap API key not set. Please use set_cmc_api_key() method first.")
            return None

        # CoinMarketCap API endpoint
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
        
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
        }

        result = {}
        batch_size = 100  # CoinMarketCap allows up to 100 symbols per request
        
        # Process symbols in batches
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            symbol_string = ",".join(batch)  
            
            parameters = {
                "symbol": symbol_string
            }
            
            try:
                #print(f"Fetching market data for batch: {batch}")
                response = requests.get(url, headers=headers, params=parameters)
                response.raise_for_status()
                
                data = response.json()
                
                if data['status']['error_code'] == 0:
                    # Process each symbol in the response
                    for symbol in batch:
                        # if symbol == 'USDS':
                        #     print(data)
                        if symbol in data['data']:
                            symbol_data = data['data'][symbol]
                            quote_data = symbol_data['quote'][convert]

                            result[symbol] = {
                                'id': symbol_data['id'],
                                'name': symbol_data['name'],
                                'symbol': symbol_data['symbol'],
                                'slug': symbol_data['slug'],
                                'cmc_rank': symbol_data['cmc_rank'],
                                'circulating_supply': symbol_data['circulating_supply'],
                                'total_supply': symbol_data['total_supply'],
                                'max_supply': symbol_data['max_supply'],
                                'last_updated': symbol_data['last_updated'],
                                'pricing': {
                                    'price': quote_data['price'],
                                    'volume_24h': quote_data['volume_24h'],
                                    'volume_change_24h': quote_data['volume_change_24h'],
                                    'percent_change_1h': quote_data['percent_change_1h'],
                                    'percent_change_24h': quote_data['percent_change_24h'],
                                    'percent_change_7d': quote_data['percent_change_7d'],
                                    'percent_change_30d': quote_data['percent_change_30d'],
                                    'percent_change_60d': quote_data['percent_change_60d'],
                                    'percent_change_90d': quote_data['percent_change_90d'],
                                    'market_cap': quote_data['market_cap'],
                                    'market_cap_dominance': quote_data['market_cap_dominance'],
                                    'fully_diluted_market_cap': quote_data['fully_diluted_market_cap'],
                                    'last_updated': quote_data['last_updated']
                                }
                            }
                        else:
                            #print(f"Symbol {symbol} not found in CoinMarketCap API")
                            result[symbol] = None
                else:
                    print(f"CoinMarketCap API error: {data['status']['error_message']}")
                    # Mark all symbols in this batch as failed
                    for symbol in batch:
                        result[symbol] = None
                        
            except requests.exceptions.RequestException as e:
                print(f"Request error fetching data for batch {batch}: {e}")
                # Mark all symbols in this batch as failed
                for symbol in batch:
                    result[symbol] = None
            except Exception as e:
                print(f"Error processing batch {batch}: {e}")
                # Mark all symbols in this batch as failed
                for symbol in batch:
                    result[symbol] = None
            
            # Rate limiting - CoinMarketCap has rate limits
            # Basic plan: 333 requests per day, 10,000 requests per month
            # Wait 1 second between batches to be safe
            if i + batch_size < len(symbols):
                time.sleep(1)
            #break

        return result
    
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

    def init_exchange(self, exchange_id, api_key=None, api_secret=None,cmc_api_key=None):
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

            self.set_cmc_api_key(cmc_api_key)  # 
                
            return self.exchange
        except AttributeError:
            print(f"Exchange {exchange_id} not found.")
            return None
    
    def get_market_volume(self, symbol=None, convert='USD',market_data=None):

        if market_data is not None:
            #print("Using provided market data.")
            self.cms_results= market_data

        if self.cms_results is None:
            print("CoinMarketCap results not initialized. Please call get_market_volume_by_symbols() first.")
            return 0

        #symbol= symbol.replace("/","")

        sdata=self.cms_results.get(symbol,None)
        if sdata is None:
            print(f"Symbol {symbol} not found in CoinMarketCap data.")
            return 0
        if sdata['pricing']['market_cap'] is None:
            print(f"Market cap for {symbol} is None.")
            return 0
        if sdata['pricing']['market_cap'] < 0:
            print(f"Market cap for {symbol} is negative: {sdata['pricing']['market_cap']}.")
            return 0
        if sdata['pricing']['market_cap'] == 0:
            print(f"Market cap for {symbol} is zero.")
            return 0
        
        return sdata['pricing']['market_cap'] 



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

    def quote_symbols(self, all_tickers,quote_currency='USD'):

        symbols= []

        for symbol, ticker in all_tickers.items():
            # Filter by quote currency
            if not symbol.endswith(f"/{quote_currency}"):
                continue        
            symbols.append(symbol)

        return symbols

    def get_exchange_info(self, exchange_id=None):
        """
        Get comprehensive information about the exchange.
        
        Args:
            exchange_id (str, optional): The ID of the exchange. If None, uses the already initialized exchange.
            
        Returns:
            dict: Detailed information about the exchange or None if an error occurs
        """
        # if exchange_id and not self.exchange:
        #     self.init_exchange(exchange_id)
            
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
                print("Fetching all tickers")
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
            import traceback
            traceback.print_exc()
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
            
    def get_top_movers(self, quote_currency='USDT', limit=10, windowSize='1d', sort_by='percentage_change', sort_desc=True):
        """
        Get top gainers and losers based on percentage change within a specified time window.
        
        Args:
            quote_currency (str): Quote currency to filter by (e.g., 'USDT', 'BTC')
            limit (int): Number of top/bottom pairs to return
            windowSize (str): Time window for percentage change (e.g., '1h', '1d', '7d')
            sort_by (str): Field to sort by (e.g., 'percentage_change', 'volume', 'market_cap')
            sort_desc (bool): Sort in descending order (True) or ascending order (False)
            
        Returns:
            dict: Dictionary containing gainers, losers, and related metadata
        """
        if not self.exchange:
            print("Exchange not initialized.")
            return None
            
        try:
            # Get all tickers for the specified quote currency
            all_tickers = self.get_tickers()
            if not all_tickers:
                print("Failed to fetch tickers.")
                return None
                
            # Filter tickers by quote currency
            filtered_tickers = {}
            for symbol, ticker in all_tickers.items():
                if symbol.endswith(f'/{quote_currency}'):
                    filtered_tickers[symbol] = ticker
            
            if not filtered_tickers:
                print(f"No tickers found for {quote_currency} quote currency.")
                return None
                
            # Extract base symbols for market cap data
            base_symbols = [symbol.split('/')[0] for symbol in filtered_tickers.keys()]
            market_data = self.get_market_volume_by_symbols(base_symbols) if self.cmc_api_key else None
            
            # Prepare data for sorting
            pairs_data = []
            for symbol, ticker in filtered_tickers.items():
                base = symbol.split('/')[0]
                
                # Get percentage change based on window size
                if windowSize == '1h':
                    percentage = ticker.get('change', {}).get('percent_change_1h', None)
                elif windowSize == '1d':
                    percentage = ticker.get('change', {}).get('percentage', None)  # Default 24h change
                elif windowSize == '7d':
                    percentage = ticker.get('change', {}).get('percent_change_7d', None)
                else:
                    percentage = ticker.get('change', {}).get('percentage', None)
                
                # Get volume and market cap
                volume = ticker.get('volume', {}).get('quote_volume', 0)
                market_cap = self.get_market_volume(base, market_data=market_data) if market_data else 0
                
                # Get price data
                last = ticker.get('pricing_information', {}).get('last', 0)
                
                # Skip entries with no price or percentage change
                if last == 0 or percentage is None:
                    continue
                    
                # Add entry to pairs data
                pairs_data.append({
                    'symbol': symbol,
                    'base': base,
                    'quote': quote_currency,
                    'last': last,
                    'percentage': percentage,
                    'volume': volume,
                    'market_cap': market_cap,
                    'timestamp': ticker.get('timestamp', None)
                })
            
            if not pairs_data:
                print("No valid pairs data found.")
                return None
                
            # Sort data for gainers (highest first)
            if sort_by == 'percentage_change':
                sort_field = 'percentage'
            elif sort_by == 'volume':
                sort_field = 'volume'
            elif sort_by == 'market_cap':
                sort_field = 'market_cap'
            else:
                sort_field = 'percentage'
                
            # Sort data for gainers and losers
            sorted_pairs = sorted(pairs_data, key=lambda x: x[sort_field] if x[sort_field] is not None else 0, reverse=sort_desc)
            
            # Get top gainers and losers
            gainers = sorted_pairs[:limit] if sort_desc else sorted_pairs[-limit:]
            losers = sorted_pairs[-limit:] if sort_desc else sorted_pairs[:limit]
            losers.reverse()  # Show biggest losers first
            
            # Return the result
            return {
                'gainers': gainers,
                'losers': losers,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'quote_currency': quote_currency,
                'window': windowSize
            }
            
        except Exception as e:
            traceback.print_exc()
            print(f"Error fetching top movers: {e}")
            return None
        
    def calculate_market_metrics(self, symbols: List[str], convert: str = 'USD') -> Dict:
        """
        Calculate various advanced market-related metrics for the specified cryptocurrencies
        
        Args:
            symbols (List[str]): List of cryptocurrency symbols
            convert (str): Currency to convert values to (default: 'USD')
            
        Returns:
            Dict: Dictionary containing additional market metrics for each symbol
        """
        # Get basic market data
        market_data = self.get_market_volume_by_symbols(symbols, convert)
        
        if not market_data:
            return {}
            
        # Filter out None values (failed requests)
        valid_data = {k: v for k, v in market_data.items() if v is not None}
        
        if not valid_data:
            return {}
            
        # Calculate total market cap of all valid cryptocurrencies to use for market dominance calculation
        total_market_cap = sum(data['pricing']['market_cap'] for data in valid_data.values() if data['pricing'].get('market_cap'))
        
        # Calculate additional metrics for each cryptocurrency
        result = {}
        for symbol, data in valid_data.items():
            pricing = data['pricing']
            
            # Calculate volume-to-market-cap ratio (higher values may indicate more trading activity relative to size)
            volume_to_mc_ratio = None
            if pricing.get('market_cap') and pricing.get('market_cap') > 0:
                volume_to_mc_ratio = pricing.get('volume_24h', 0) / pricing.get('market_cap', 1)
                
            # Calculate market dominance (percentage of total market cap)
            dominance = None
            if pricing.get('market_cap') and total_market_cap > 0:
                dominance = (pricing.get('market_cap', 0) / total_market_cap) * 100
                
            # Calculate circulating to max supply ratio
            circulating_to_max_ratio = None
            if data.get('max_supply') and data.get('max_supply') > 0:
                circulating_to_max_ratio = (data.get('circulating_supply', 0) / data.get('max_supply', 1)) * 100
                
            # Store calculated metrics
            result[symbol] = {
                'volume_to_mc_ratio': volume_to_mc_ratio,
                'market_dominance_percent': dominance if dominance != data.get('pricing', {}).get('market_cap_dominance') else None,
                'circulating_to_max_ratio': circulating_to_max_ratio,
                'fully_diluted_valuation': pricing.get('fully_diluted_market_cap')
            }
            
        return result

