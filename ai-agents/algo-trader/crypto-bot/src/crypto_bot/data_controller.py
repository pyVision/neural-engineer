"""
Redis-based data access controller for repository storage
"""
import os
import json
import logging
from typing import List, Dict, Optional
from redis import asyncio as aioredis
#from functools import lru_cache
from .init_application import initialization_result



class JsonSerializer:
    @staticmethod
    def serialize(data: any) -> str:
        """Serialize data to JSON string"""
        return json.dumps(data)

    @staticmethod
    def deserialize(data_str: str) -> any:
        """Deserialize JSON string to data"""
        return json.loads(data_str) if data_str else None

class Cache:

    """A simple Redis-based cache controller with dynamic TTL support"""

    def __init__(self, ttl: Optional[int] = None, namespace: str = None, endpoint: str = None, 
                port: str = None, password: str = None, db: str = None):
        """Initialize Redis connection and cache settings"""
        self.ttl = ttl if ttl is not None else 3600

        # Get Redis configuration from initialization_result if not provided
        namespace = namespace 
        endpoint = endpoint 
        port = port 
        password = password 
        db = db 

        # Construct Redis URL
        redis_url = f"redis://{'' if not password else f':{password}@'}{endpoint}:{port}/{db}"
        self.cache = aioredis.from_url(redis_url, decode_responses=True)

        self.logger = logging.getLogger(__name__)
        if not self.cache:
            self.logger.error("Redis cache initialization failed, cache will not be available")
        else:
            self.logger.info("Redis cache initialized successfully with namespace %s", namespace)
        self.logger.info("Redis cache URL: %s", redis_url)
        """Initialize Redis connection and cache settings"""
        self.ttl = ttl if ttl is not None else 3600

      

    async def clear_cache(self):
        """Clear the entire cache"""
        try:
            await self.cache.flushdb()
        except Exception:
            self.logger.exception("Couldn't clear cache, unexpected error")


    # async def run_cache(self, key: str, value_fn, *args, ttl: Optional[int] = None, **kwargs):
    #     """
    #     Get value from cache or call function to set it if not present
    #     :param key: Cache key
    #     :param value_fn: Function to call if value not in cache
    #     :param args: Additional positional arguments to pass to value_fn
    #     :param ttl: Time to live for the cache entry, defaults to self.ttl
    #     :param kwargs: Additional keyword arguments to pass to value_fn
    #     :return: Cached value or the newly computed value
    #     """

    #     # Check if we should bypass cache based on arguments
    #     bypass_cache = kwargs.pop('bypass_cache', False)
    #     force_refresh = kwargs.pop('force_refresh', False)
        
    #     # Extract TTL from kwargs if present, otherwise use default
    #     ttl_value = kwargs.pop('ttl', ttl) if ttl is None else ttl
        
    #     # If bypass or force refresh, skip cache lookup
    #     if bypass_cache or force_refresh:
    #         result = await value_fn(*args, **kwargs)
    #         if not bypass_cache:  # Still cache the result if not bypassing completely
    #         await self.set_in_cache(key, result, ttl_value)
    #         return result
            
    #     cached_value = await self.get_from_cache(key)
    #     if cached_value is not None:
    #         return cached_value
        

            
    #     # Set result in cache
    #     await self.set_in_cache(key, result, ttl)
    #     return result



    async def get_from_cache(self, key: str):
        """Get value from cache"""
        try:
            value = await self.cache.get(key)
            if value:
                return JsonSerializer.deserialize(value)
        except Exception as e:
            self.logger.error(f"Error getting value from cache: {str(e)}")
        return None

    async def set_in_cache(self, key: str, value: any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL"""
        try:
            serialized_value = JsonSerializer.serialize(value)
            ttl1=ttl or self.ttl
            if ttl1:
                await self.cache.set(key, serialized_value, ex=ttl1)
            else:
                await self.cache.set(key, serialized_value)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.error(f"Error setting value in cache: {str(e)}")




class DataAccessController:

    def __init__(self, cache=None):
        """Initialize Redis connection and cache"""
        # Get Redis configuration from initialization_result

        namespace = initialization_result["env_vars"]["REDIS_NAMESPACE"]
        endpoint = initialization_result["env_vars"]["REDIS_HOST"]
        port = initialization_result["env_vars"]["REDIS_PORT"]
        password = initialization_result["env_vars"]["REDIS_PASSWORD"]
        db = initialization_result["env_vars"]["REDIS_DB"]
        
        self.ADDED_REPOS_KEY = f"{namespace}:all_tickers"
        if cache is not None:
            self.cache = cache
        else:
            self.cache = Cache(namespace=namespace, endpoint=endpoint, port=port, 
                         password=password, db=db)
        
        self.serializer = JsonSerializer()

    async def get_all_tickers(self) -> List[Dict[str, str]]:
        """
        Get all tickers (both remote and default)
        Returns list of dicts with owner and name, remote repos first
        """
        remote_repos = await self.cache.get_from_cache(self.ADDED_REPOS_KEY)
        

        if remote_repos is None:
            remote_repos = []
        # Return remote repos first, followed by filtered default repos
        return remote_repos 

    async def add_all_tickers(self, all_tickers) -> bool:
        """
        Add a repository to the persistent storage if it doesn't exist
        Returns True if added successfully, False if already exists
        """
        # Check both remote and default repos

        
        # Save updated remote repos
        #serialized_data = self.serializer.serialize(remote_repos)
        await self.cache.set_in_cache(self.ADDED_REPOS_KEY, all_tickers)
        return True

    async def delete_all_tickers(self) -> bool:
        """
        Delete all tickers from Redis storage
        Returns True if deleted successfully, False if operation failed
        """
        try:
            # Delete the key containing all tickers
            await self.cache.cache.delete(self.ADDED_REPOS_KEY)
            return True
        except Exception as e:
            logging.error(f"Error deleting all tickers: {str(e)}")
            return False



# Module-level instance
_data_controller_instance = None

async def get_data_controller() -> DataAccessController:
    """Singleton pattern for DataAccessController"""
    global _data_controller_instance
    if _data_controller_instance is None:
        _data_controller_instance = DataAccessController()
    return _data_controller_instance
