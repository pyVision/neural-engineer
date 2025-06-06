from aiocache.base import SENTINEL
from aiocache.decorators import cached as original_cached
import logging
import asyncio
from aiocache import Cache, RedisCache
from aiocache.serializers import JsonSerializer


logger = logging.getLogger(__name__)

class enhanced_cached(original_cached):
    """
    Enhanced version of aiocache's cached decorator, adding these features:
    
    Bypass cache using a parameter (even when TTL hasn't expired)
    Cache invalidation methods
    TTL override parameter for runtime flexibility and  Asynchronous TTL updates on cache hits
    Cache statistics tracking
    Dynamic TTL calculation based on the function result


 
    """

    def __init__(
        self,
        ttl=SENTINEL,
        ttl_func=None,
        key=None,
        namespace=None,
        key_builder=None,
        skip_cache_func=lambda x: False,
        cache=Cache.MEMORY,
        serializer=None,
        plugins=None,
        alias=None,
        noself=False,
        cache_key_prefix=None,
        shared_context=None,
        track_stats=False,
        update_ttl_on_hit=True,
        **kwargs,
    ):
        super().__init__(
            ttl=ttl,
            key=key,
            namespace=namespace,
            key_builder=key_builder,
            skip_cache_func=skip_cache_func,
            cache=cache,
            serializer=serializer,
            plugins=plugins,
            alias=alias,
            noself=noself,
            **kwargs,
        )
        self.ttl_func = ttl_func
        self.cache_key_prefix = cache_key_prefix
        self.shared_context = shared_context
        self.track_stats = track_stats
        self.stats = {"hits": 0, "misses": 0, "bypasses": 0}
        self.update_ttl_on_hit = update_ttl_on_hit

    def __call__(self, f):
        wrapped = super().__call__(f)
        
        # Add additional metadata and methods to the wrapped function
        wrapped.original_func = f
        wrapped.cache_stats = self.stats
        
        # Add a method to explicitly invalidate the cache for specific args
        async def invalidate(*args, **kwargs):
            """Explicitly invalidate cache for these function arguments"""
            key = self.get_cache_key(f, args, kwargs)
            await self.cache.delete(key)
            return True
        
        wrapped.invalidate = invalidate
        
        # Add a method to refresh the cache for specific args
        async def refresh(*args, **kwargs):
            """Force refresh of the cache for these function arguments"""
            key = self.get_cache_key(f, args, kwargs)
            # Execute function and update cache
            result = await f(*args, **kwargs)
            ttl = self._calculate_ttl(result)
            await self.cache.set(key, result, ttl=ttl)
            return result
            
        wrapped.refresh = refresh
        
        return wrapped

    def get_cache_key(self, f, args, kwargs):
        """Enhanced key generation with support for sharing contexts"""
        if self.key:
            base_key = self.key
        elif self.key_builder:
            base_key = self.key_builder(f, *args, **kwargs)
        else:
            base_key = self._key_from_args(f, args, kwargs)
        
        # If we have a shared context, use that instead of the function name
        if self.shared_context:
            parts = base_key.split(":", 1)
            if len(parts) > 1:
                # Replace function name with shared context
                base_key = f"{self.shared_context}:{parts[1]}" 
            else:
                base_key = f"{self.shared_context}:{base_key}"
        
        # Apply prefix if specified
        if self.cache_key_prefix:
            base_key = f"{self.cache_key_prefix}:{base_key}"
            
        return base_key

    async def decorator(
        self, f, *args, bypass_cache=False, force_refresh=False, 
        cache_read=True, cache_write=True, 
        aiocache_wait_for_write=True, ttl=None, **kwargs
    ):
        """
        Enhanced decorator with bypass_cache, force_refresh, and TTL override options
        
        Args:
            ttl: Optional TTL override to use instead of the default
                - On cache hit: Updates existing TTL in background (if update_ttl_on_hit=True)
                - On cache miss: Uses this TTL when storing the result
        """
        # Extract ttl from kwargs if provided (before removing it)
        runtime_ttl = kwargs.pop('ttl', None) if ttl is None else ttl
        
        if runtime_ttl is not None:
            ttl=runtime_ttl
            
        #print("AAAA", runtime_ttl)
        # Generate cache key
        key = self.get_cache_key(f, args, kwargs)
        
        # Handle cache bypass
        if bypass_cache or force_refresh:
            if self.track_stats:
                self.stats["bypasses"] += 1
            # Skip cache lookup, directly call function
            result = await f(*args, **kwargs)
            
            # Update cache if needed (unless skip_cache_func says otherwise)
            if not self.skip_cache_func(result) and cache_write and (force_refresh or bypass_cache):
                # Use provided TTL or calculate default
                if ttl is not None:
                    effective_ttl = ttl  
                else:
                    effective_ttl = self._calculate_ttl(result)
                    
                if aiocache_wait_for_write:
                    await self.set_in_cache(key, result, effective_ttl)
                else:
                    asyncio.create_task(self.set_in_cache(key, result, effective_ttl))
                    
            return result
        
        # Normal path - check cache first
        if cache_read:
            value = await self.get_from_cache(key)
            if value is not None:
                # Cache hit
                if self.track_stats:
                    self.stats["hits"] += 1
                
                # On cache hit, update TTL in background if requested
                if runtime_ttl is not None :
                    # Don't await - run asynchronously to avoid blocking
                    asyncio.create_task(self._update_ttl(key, runtime_ttl))
                
                return value
            
        # Cache miss or skipped read
        if self.track_stats:
            self.stats["misses"] += 1
            
        result = await f(*args, **kwargs)
        
        # Skip caching if needed
        if self.skip_cache_func(result):
            return result
            
        
        if cache_write:
            if ttl is not None:
                    effective_ttl = ttl  
            else:
                    effective_ttl = self._calculate_ttl(result)
            if aiocache_wait_for_write:
                print("Setting in cache", key, result.__getstate__())
                await self.set_in_cache(key, result, effective_ttl)
            else:
                
                asyncio.create_task(self.set_in_cache(key, result, effective_ttl))
                
        return result
        
    async def _update_ttl(self, key, ttl):
        """Update TTL for an existing cache entry without blocking"""
        try:
            # Update expiration time for the key
            await self.cache.expire(key, ttl)
        except Exception:
            logger.exception("Couldn't update TTL for key %s", key)
        
    def _calculate_ttl(self, result):
        """Calculate TTL dynamically if ttl_func is provided"""
        if self.ttl_func and callable(self.ttl_func):
            return self.ttl_func(result)
        return self.ttl
        
    async def set_in_cache(self, key, value, ttl=None):
        """Enhanced cache setter with dynamic TTL support"""
        try:
            #print("Setting in cache", key, value)
            ttl = ttl if ttl is not None else self.ttl
            await self.cache.set(key, value, ttl=ttl)
        except Exception as e:
            #import traceback
            #traceback.print_exc()
            #logger.error("Error setting cache for key %s: %s", key, traceback.format_exc())
            logger.exception("Couldn't set %s in key %s, unexpected error", value, key)
            pass

# Helper function for creating shared cache keys between functions
def shared_key_builder(shared_prefix):
    """
    Create a key builder that uses a shared prefix instead of function name
    
    :param shared_prefix: The shared prefix to use instead of function name
    """
    def key_builder(func, *args, **kwargs):
        # Convert args to strings, filtering out non-serializable objects
        args_str = ":".join(str(arg) for arg in args if not callable(arg))
        kwargs_str = ":".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{shared_prefix}:{args_str}:{kwargs_str}"
    
    return key_builder

from aiocache import cached, Cache
from typing import Any, Tuple, Dict

def custom_key_builder(
    func: Any,
    *args: Tuple[Any],
    **kwargs: Dict[str, Any]
) -> str:
    """Custom key builder for cache entries.
    
    Args:
        namespace: Cache namespace
        fn: The function being cached
        args: Positional arguments
        kwargs: Keyword arguments
    
    Returns:
        Formatted cache key as string
    """
    # Extract function name

    
    key = []
    key.append(func.__qualname__ or func.__name__)
    # Format args/kwargs into string
    #args_str = ':'.join(str(arg) for arg in args)
    #kwargs_str = ':'.join(f"{k}={v}" for k, v in kwargs.items())

    args_str = ":".join(str(arg) for arg in args if not callable(arg))
    kwargs_str = ":".join(f"{k}={v}" for k, v in kwargs.items())   
    # Build key with components
    key_parts = key
    if args_str:
        key.append(args_str)
    if kwargs_str:
        key.append(kwargs_str)
        
    
    print("Key parts:", key,"LLL")
    return ":".join(key)