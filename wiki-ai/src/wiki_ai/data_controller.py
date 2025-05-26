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
            logger.exception("Couldn't clear cache, unexpected error")


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
        try:
            return await self.cache.get(key)
        except Exception:
            logger.exception("Couldn't retrieve %s, unexpected error", key)
        return None
    
    async def _update_ttl(self, key, ttl):
        """Update TTL for an existing cache entry without blocking"""
        try:
            # Update expiration time for the key
            await self.cache.expire(key, ttl)
        except Exception:
            logger.exception("Couldn't update TTL for key %s", key)

    async def set_in_cache(self, key, value, ttl=None):
        """Enhanced cache setter with dynamic TTL support"""
        try:
            #print("Setting in cache", key, value)
            ttl = ttl if ttl is not None else self.ttl
            if ttl is None:
                await self.cache.set(key, value)
            else:
                await self.cache.set(key, value, ex=ttl)
        except Exception as e:
            #import traceback
            #traceback.print_exc()
            #logger.error("Error setting cache for key %s: %s", key, traceback.format_exc())
            logger.exception("Couldn't set %s in key %s, unexpected error", value, key)
            pass



class DataAccessController:

    def __init__(self, cache=None):
        """Initialize Redis connection and cache"""
        # Get Redis configuration from initialization_result

        namespace = initialization_result["env_vars"]["REDIS_NAMESPACE"]
        endpoint = initialization_result["env_vars"]["REDIS_HOST"]
        port = initialization_result["env_vars"]["REDIS_PORT"]
        password = initialization_result["env_vars"]["REDIS_PASSWORD"]
        db = initialization_result["env_vars"]["REDIS_DB"]
        
        self.ADDED_REPOS_KEY = f"{namespace}:added_repositories"
        if cache is not None:
            self.cache = cache
        else:
            self.cache = Cache(namespace=namespace, endpoint=endpoint, port=port, 
                         password=password, db=db)
        
        self.serializer = JsonSerializer()

    async def get_all_repositories(self,default_repos=None) -> List[Dict[str, str]]:
        """
        Get all repositories (both remote and default)
        Returns list of dicts with owner and name, remote repos first
        """
        remote_repos = await self.get_added_repositories()
        
        default_repos1 = []
        # Convert DEFAULT_REPOS to the same format as remote repos
        if default_repos is not None:
            default_repos1 = [{"owner": repo["owner"], "name": repo["name"]} for repo in default_repos]
        
        # Filter out default repos that are already in remote repos
        filtered_default_repos = [
            repo for repo in default_repos1 
            if not any(r["owner"] == repo["owner"] and r["name"] == repo["name"] 
                      for r in remote_repos)
        ]
        
        # Return remote repos first, followed by filtered default repos
        return remote_repos + filtered_default_repos

    async def add_repository(self, owner: str, name: str) -> bool:
        """
        Add a repository to the persistent storage if it doesn't exist
        Returns True if added successfully, False if already exists
        """
        # Check both remote and default repos
        all_repos = await self.get_all_repositories()
        if any(r["owner"] == owner and r["name"] == name for r in all_repos):
            return False
        
        # Get current remote repos and append new one
        remote_repos = await self.get_added_repositories()
        remote_repos.append({"owner": owner, "name": name})
        
        # Save updated remote repos
        serialized_data = self.serializer.serialize(remote_repos)
        await self.cache.set_in_cache(self.ADDED_REPOS_KEY, serialized_data)
        return True

    async def get_added_repositories(self) -> List[Dict[str, str]]:
        """
        Get remote repositories from cache
        Returns list of dicts with owner and name
        """
        data = await self.cache.get_from_cache(self.ADDED_REPOS_KEY)
        if data:
            return self.serializer.deserialize(data)
        return []

    async def remove_repository(self, owner: str, name: str) -> bool:
        """
        Remove a repository from persistent storage
        Returns True if removed successfully, False if not found or is a default repo
        """
        # Only remove from remote repos, not default repos
        remote_repos = await self.get_added_repositories()
        initial_length = len(remote_repos)
        remote_repos = [r for r in remote_repos if not (r["owner"] == owner and r["name"] == name)]
        
        if len(remote_repos) < initial_length:
            serialized_data = self.serializer.serialize(remote_repos)
            await self.cache.set_in_cache(self.ADDED_REPOS_KEY, serialized_data)
            return True
        return False

    async def repository_exists(self, owner: str, name: str) -> bool:
        """Check if a repository exists in either remote or default repos"""
        all_repos = await self.get_all_repositories()
        return any(r["owner"] == owner and r["name"] == name for r in all_repos)

    async def clear_all_repositories(self) -> bool:
        """Clear all added repositories (mainly for testing purposes)"""
        try:
            await self.cache.clear_cache()
            return True
        except Exception:
            return False

#@lru_cache()
def get_data_controller() -> DataAccessController:
    """Singleton pattern for DataAccessController"""
    return DataAccessController()
