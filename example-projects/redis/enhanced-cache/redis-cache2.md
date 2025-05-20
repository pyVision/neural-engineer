# Advanced Caching Techniques with aiocache and Redis

In modern applications, effective caching strategies can dramatically improve performance. The `aiocache` library stands out as a powerful asynchronous caching solution for Python, particularly when paired with Redis. This article focuses on advanced decorator patterns that solve three common challenges:

1. Bypassing cache when needed, even with valid TTL
2. Implementing dynamic TTL based on content or context

## Setup and Installation

First, let's install the required packages:

```python
# Install required packages
pip install aiocache redis aiohttp
```

## Introduction to aiocache

`aiocache` is an asynchronous caching library for Python that provides a common interface for different cache backends. It was designed with asyncio in mind and works particularly well in asynchronous applications.

We had seen a introduct to aiosync library in the article 

Let's begin with some basic setup:

```python
from aiocache import Cache, RedisCache
from aiocache.serializers import JsonSerializer
import asyncio
import time
import json
import logging
import inspect
import functools
from datetime import datetime
from typing import Callable, Any, Optional, Union

# Configure Redis cache
cache = RedisCache(
    endpoint="localhost",
    port=6379,
    namespace="app",
    password="asdf",  # Change or remove this based on your Redis configuration
    serializer=JsonSerializer()
)

# Helper function to simulate fetching data from an external source
async def fetch_data_from_source(key=None):
    """Simulate fetching data from a slow external source"""
    await asyncio.sleep(1)  # Simulate network delay
    return {
        "timestamp": datetime.now().isoformat(),
        "data": f"Data for {key}" if key else "Generic data",
        "source": "External API"
    }
```

## Beyond Basic Caching: Building an Enhanced Decorator

The standard `aiocache.cached` decorator is useful, but let's create an enhanced version that allows us to:
1. Bypass the cache on demand
2. Set dynamic TTL values based on the result
3. Share cached objects between functions
4. Track cache statistics

```python
from aiocache.base import SENTINEL
from aiocache.decorators import cached as original_cached

logger = logging.getLogger(__name__)

class enhanced_cached(original_cached):
    """
    Enhanced version of aiocache's cached decorator, adding these features:
    
    Bypass cache using a parameter (even when TTL hasn't expired)
    Cache invalidation methods
    TTL override parameter for runtime flexibility and Asynchronous TTL updates on cache hits
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
                if runtime_ttl is not None:
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
            effective_ttl = self._calculate_ttl(result)
            if aiocache_wait_for_write:
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
            ttl = ttl if ttl is not None else self.ttl
            await self.cache.set(key, value, ttl=ttl)
        except Exception:
            logger.exception("Couldn't set %s in key %s, unexpected error", value, key)

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
```

```python
# Example 1: Basic usage with bypass_cache
@enhanced_cached(    
    ttl=10,
    cache=Cache.REDIS,
    track_stats=True,
    serializer=JsonSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10                 
                 )  # 30 seconds TTL for demo
async def get_user_data(user_id):
    """Get user data with caching"""
    print(f"Fetching data for user {user_id} from source...")
    await asyncio.sleep(0.5)  # Simulate API call
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "last_updated": datetime.now().isoformat()
    }
```

Here's how we can test the cache bypass functionality:

```python
async def test_cache_bypass():
    print("1. Testing bypass_cache parameter:")
    
    # First call - should be cache miss
    print("First call (should be cache miss):")
    user1 = await get_user_data(101)
    print(f"  Timestamp: {user1['last_updated']}")
    
    # Second call - should be cache hit with same timestamp
    print("\nSecond call (should be cache hit):")
    user2 = await get_user_data(101)
    print(f"  Timestamp: {user2['last_updated']}")
    print(f"  Same data? {user1['last_updated'] == user2['last_updated']}")
    
    # Third call with bypass_cache=True - should be fresh data
    print("\nThird call with bypass_cache=True:")
    user3 = await get_user_data(101, bypass_cache=True)
    print(f"  Timestamp: {user3['last_updated']}")
    print(f"  Fresh data? {user1['last_updated'] != user3['last_updated']}")
    
    # Test explicit cache invalidation
    print("\n2. Testing explicit invalidation:")
    
    # First invalidate the cache
    print("Invalidating cache...")
    await get_user_data.invalidate(101)
    
    # This should be a cache miss
    print("\nCall after invalidation (should be cache miss):")
    user4 = await get_user_data(101)
    print(f"  Timestamp: {user4['last_updated']}")
    print(f"  Fresh data? {user3['last_updated'] != user4['last_updated']}")
    
    # Display cache statistics
    print("\nCache Statistics:")
    print(f"  {get_user_data.cache_stats}")
```

Using custom key builders for versioned caching:

```python
# Example with custom key builder for more control over caching
def versioned_key_builder(func, *args, **kwargs):
    """Build a cache key that includes version information"""
    base_key = func.__name__
    
    # Extract primary arg (assume it's first positional arg)
    entity_id = args[0] if args else "unknown"
    
    # Extract version from kwargs or use default
    version = kwargs.get('version', 'v1')
    
    return f"{base_key}:{entity_id}:ver{version}"

@enhanced_cached(    
    key_builder=versioned_key_builder,
    ttl=10,
    cache=Cache.REDIS,
    track_stats=True,
    serializer=JsonSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10                 
                 ) 
async def get_product_data(product_id, version='v1'):
    """Get product data with versioned caching"""
    print(f"Fetching product {product_id} (version {version}) from source...")
    await asyncio.sleep(0.5)  # Simulate API call
    return {
        "product_id": product_id,
        "name": f"Product {product_id}",
        "version": version,
        "timestamp": datetime.now().isoformat()
    }
```

We can test this versioned caching approach:

```python
async def test_versioned_cache():
    print("\n3. Testing versioned cache keys:")
    
    # First call with v1 - should be cache miss
    print("First call with v1:")
    product1 = await get_product_data(201, version='v1')
    print(f"  Version: {product1['version']}")
    print(f"  Timestamp: {product1['timestamp']}")
    
    # Second call with v1 - should be cache hit
    print("\nSecond call with v1:")
    product2 = await get_product_data(201, version='v1')
    print(f"  Version: {product2['version']}")
    print(f"  Timestamp: {product2['timestamp']}")
    print(f"  Cache hit? {product1['timestamp'] == product2['timestamp']}")
    
    # Call with v2 - should be cache miss (different key)
    print("\nCall with v2:")
    product3 = await get_product_data(201, version='v2')
    print(f"  Version: {product3['version']}")
    print(f"  Timestamp: {product3['timestamp']}")
    print(f"  Fresh data? {product1['timestamp'] != product3['timestamp']}")
```

## 2. Implementing Dynamic TTL Values

Now let's explore how our enhanced decorator can implement dynamic TTL strategies:
1. Using a TTL function based on result content
2. Different TTL values for different types of objects
3. Scaling TTL based on result complexity

```python
# Example with dynamic TTL based on result content
@enhanced_cached(
    ttl=10,
    cache=Cache.REDIS,
    track_stats=True,
    serializer=JsonSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10, 
    ttl_func=lambda result: 60 if result.get('is_premium') else 20  # 60s for premium, 20s for regular
)
async def get_user_subscription(user_id):
    """Get user subscription with dynamic TTL based on subscription type"""
    print(f"Fetching subscription for user {user_id}...")
    await asyncio.sleep(0.5)  # Simulate API call
    is_premium = user_id % 3 == 0  # Every 3rd user is premium
    return {
        "user_id": user_id,
        "is_premium": is_premium,
        "plan": "premium" if is_premium else "basic",
        "timestamp": datetime.now().isoformat()
    }

# Example with TTL based on result complexity
def complexity_based_ttl(result):
    """TTL scales based on data complexity/size"""
    if not result:
        return 10  # Default low TTL for empty results
        
    # Estimate complexity by serialized size
    size = len(json.dumps(result))
    
    # Scale TTL: larger results get cached longer
    # Between 20-60 seconds based on size
    return max(20, min(60, 20 + (size // 20)))

@enhanced_cached(    
    ttl=10,
    cache=Cache.REDIS,
    track_stats=True,
    serializer=JsonSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10,
    ttl_func=complexity_based_ttl
)
async def get_product_catalog(category, include_details=False):
    """Get product catalog with dynamically scaled TTL"""
    print(f"Fetching catalog for {category} (details: {include_details})...")
    await asyncio.sleep(0.8)  # Simulate API call
    
    # Generate variable number of products
    product_count = (hash(category) % 10) + 2
    
    products = []
    for i in range(1, product_count + 1):
        product = {
            "id": i,
            "name": f"{category} Product {i}",
        }
        
        # Add more details to increase complexity/size
        if include_details:
            product.update({
                "description": f"Detailed description for {category} Product {i}",
                "specifications": {
                    "weight": f"{i * 0.5} kg",
                    "dimensions": f"{i * 5} x {i * 3} x {i * 2} cm",
                    "colors": ["red", "blue", "black"] if i % 2 else ["white", "grey"],
                },
                "features": [f"Feature {j}" for j in range(1, (i % 5) + 3)]
            })
    
        products.append(product)
    
    result = {
        "category": category,
        "product_count": len(products),
        "products": products,
        "timestamp": datetime.now().isoformat()
    }
    
    return result
```

### Dynamically Updateable TTL

A particularly useful feature is the ability to dynamically update the TTL of a cached item after it's been cached:

```python
# Example with dynamically updateable TTL after caching
@enhanced_cached(
    ttl=30,
    cache=Cache.REDIS,
    track_stats=True,
    serializer=JsonSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10,
    # Default TTL is 30 seconds, but can be updated after caching
)
async def get_product_data(product_id, ttl=None):
    """Get product data with TTL that can be dynamically updated on subsequent calls"""
    print(f"Fetching data for product {product_id}...")
    await asyncio.sleep(0.7)  # Simulate API call
    
    # Generate product details based on ID
    return {
        "product_id": product_id,
        "name": f"Product {product_id}",
        "price": round(10 + (product_id % 90), 2),
        "in_stock": product_id % 4 != 0,
        "timestamp": datetime.now().isoformat()
    }
```

Here's how we can test the dynamic TTL functions:

```python
async def test_dynamic_ttl():
    print("\nTesting Dynamic TTL:")
    
    # Test premium vs regular subscriptions
    print("\n1. Testing subscription-based TTL:")
    
    # Regular user
    print("Regular user:")
    regular = await get_user_subscription(101)  # Non-premium
    print(f"  Plan: {regular['plan']}")
    print(f"  TTL: 20 seconds")
    
    # Premium user
    print("\nPremium user:")
    premium = await get_user_subscription(102)  # Premium
    print(f"  Plan: {premium['plan']}")
    print(f"  TTL: 60 seconds")
    
    # Test complexity-based TTL
    print("\n2. Testing complexity-based TTL:")
    
    # Simple catalog
    print("Simple catalog:")
    simple_catalog = await get_product_catalog("Books")
    simple_ttl = complexity_based_ttl(simple_catalog)
    print(f"  Products: {simple_catalog['product_count']}")
    print(f"  Calculated TTL: {simple_ttl} seconds")
    
    # Detailed catalog (larger/more complex)
    print("\nDetailed catalog:")
    detailed_catalog = await get_product_catalog("Electronics", include_details=True)
    detailed_ttl = complexity_based_ttl(detailed_catalog)
    print(f"  Products: {detailed_catalog['product_count']}")
    print(f"  Calculated TTL: {detailed_ttl} seconds")
    
    print("\nComparing TTLs:")
    print(f"  Simple catalog TTL: {simple_ttl} seconds")
    print(f"  Detailed catalog TTL: {detailed_ttl} seconds")
    print(f"  Difference: {detailed_ttl - simple_ttl} seconds")

# Test dynamically updating TTL
async def test_dynamic_ttl_update():
    print("\n3. Testing dynamically updateable TTL:")
    
    # First call - cache miss (uses default TTL of 30 seconds)
    data1 = await get_product_data(333)
    print(f"  Product ID: {data1['product_id']}")
    # Second call - cache hit (asynchronously updates TTL to 60 seconds)
    data2 = await get_product_data(333, ttl=60)
    print(f"  Product ID: {data2['product_id']}")
    # Third call after waiting - will still be a cache hit 
    # because TTL was extended to 60 seconds
    await asyncio.sleep(35)  # Wait longer than the default TTL
    data3 = await get_product_data(333)  # Still a cache hit
    print(f"  Product ID: {data3['product_id']}")
```


## Conclusion

We've demonstrated how to extend aiocache's decorators to create a powerful caching system that addresses three key challenges:

**Bypassing Cache When Needed**
   - Using `bypass_cache=True` parameter
   - Implementing explicit `.invalidate()` methods
   - Using versioned or custom cache keys

**Dynamic TTL Implementation**
   - Setting TTL based on result content (premium vs. regular)
   - Adjusting TTL based on data characteristics (size/complexity)
   - Dynamically updating TTL for existing cached items

The complete source code for this article is available in our [NeuralEngineer](https://github.com/pyVision/neural-engineer.git) at the path example-projects/redis/enhanced-cache



Our enhanced decorator provides a clean, declarative approach to caching that combines flexibility with performance. By intelligently managing cache lifetimes and sharing cached objects when appropriate, applications can achieve optimal balance between performance and data freshness.
