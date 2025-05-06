# Async Caching in Python with aiocache and Redis

Caching is essential for building high-performance applications, especially when dealing with expensive computations or slow data sources. For modern Python async applications, [aiocache](https://aiocache.readthedocs.io/) is a popular library that provides a simple and flexible caching interface with support for multiple backends, including Redis.

---

## What is aiocache?

aioCache is an asynchronous caching library for Python, designed to work seamlessly with asyncio-based frameworks like FastAPI, Starlette, and aiohttp. It provides decorators and cache objects to easily cache function results, objects, or arbitrary data.

---

## Using aiocache with Redis Backend

### Installation
```bash
# Install aiocache with Redis support
pip install aiocache[redis]

# Install Redis CLI (choose your platform)

# For Ubuntu/Debian
sudo apt-get install redis-tools

# For macOS using Homebrew
brew install redis

# For Windows, download from Redis website
# https://github.com/microsoftarchive/redis/releases
```


# Key Features of aiocache


## **Async Support:** Designed for asyncio, works natively with async functions. Here's a basic example:

```python
from aiocache import SimpleMemoryCache
import asyncio


cache = SimpleMemoryCache()

# Using in-memory cache
async def cache_example():
    cache = SimpleMemoryCache()

    print("Setting cache values...")
    await cache.set("k1", "v1")
    await cache.set("k2", "v2")

    print("Getting cache values...")
    r1 = await cache.get("k1")
    print(f"Value for k1: {r1}")
    
    r2 = await cache.get("k2") 
    print(f"Value for k2: {r2}")

# Run the example
asyncio.run(cache_example())
```



### **Multiple Backends:** Supports Redis, Memcached, SimpleMemoryCache, and allows custom backend implementations.

```python
from aiocache import RedisCache
import asyncio
import redis.asyncio as redis

# Using Redis cache with authentication
async def cache_example2():

    
    # Initialize Redis cache
    cache = RedisCache(
        namespace="main",
        endpoint="127.0.0.1", 
        port=6379,
        password="your-redis-password"
    )

    print("Setting cache values...")
    await cache.set("k1", "v1")
    await cache.set("k2", "v2")

    print("Getting cache values...")
    r1 = await cache.get("k1")
    print(f"Value for k1: {r1}")
    
    r2 = await cache.get("k2") 
    print(f"Value for k2: {r2}")

# Run the example
asyncio.run(cache_example2())
```
### View Cache Values in Redis CLI

To inspect the cached values using Redis CLI:

```bash

export redis_url="127.0.0.1"
export redis_port="6379"
export password="asdf"
# Connect to Redis CLI
redis-cli --pass ${password} -h ${redis_url} -p ${redis_port} 

# List all keys
keys *

```

we can see the keys created 

```bash
2) "n1:k2"
3) "n1:k1"
```

### **Function Decorators:** 

`@cached` provides simple function caching with Redis. Here's an example:

```python
from aiocache import cached, Cache
from aiocache.serializers import PickleSerializer

# Redis Cache with Decorator Example

This example demonstrates using Redis as a caching layer with a decorator pattern. The cache configuration uses aiocache library.

## Cache Configuration Details
- **TTL (Time To Live)**: 10 seconds
- **Cache Type**: Redis
- **Serializer**: PickleSerializer for object serialization
- **Namespace**: "n1" (used for key prefix)
- **Connection**: localhost:6379
- **Database**: 0
- **Pool Size**: 10 concurrent connections max

## Cache Behavior
- First call performs the actual operation and caches the result
- Subsequent calls within TTL period retrieve data from cache
- After TTL expiration, the cache is invalidated and the operation is performed again
# Using Redis cache with decorator
@cached(
    ttl=10,
    cache=Cache.REDIS, 
    serializer=PickleSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10
)
async def get_user_info(user_id: str) -> dict:
    # This would normally fetch from database
    # Simulating expensive operation
    await asyncio.sleep(1)  
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "status": "active"
    }

# Usage example
async def cache_example3():
    # First call - cache miss
    result1 = await get_user_info("123")
    print("First call result:", result1)
    
    # Second call - cache hit (fetches from cache)
    result2 = await get_user_info("123")
    print("Second call result:", result2)

# Run the example
asyncio.run(cache_example3())
```

we can see the key name in redis as 

```bash
"n1:__main__get_user_info('123',)[]"
```


## Custom Key Generation

You can customize how cache keys are generated using a key builder function. Here's an example:

```python
from aiocache import cached, Cache
from typing import Any, Tuple, Dict

def custom_key_builder(
    namespace: str,
    fn: Any,
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
    fname = fn.__name__
    
    # Format args/kwargs into string
    args_str = ':'.join(str(arg) for arg in args)
    kwargs_str = ':'.join(f"{k}={v}" for k, v in kwargs.items())
    
    # Build key with components
    key_parts = [namespace, fname]
    if args_str:
        key_parts.append(args_str)
    if kwargs_str:
        key_parts.append(kwargs_str)
        
    return ':'.join(key_parts)

# Usage example
@cached(
    key_builder=custom_key_builder,
    ttl=10,
    cache=Cache.REDIS, 
    serializer=PickleSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10
)
async def get_user_data(user_id: str, detail: bool = False):
    return {"id": user_id, "detail": detail}

# This will create keys like: "app:get_user_data:123:detail=True"
```

The key name in the cache can be observed as 

```bash
n1:get_user_data:123
```

the value is 

```
127.0.0.1:6379> GET n1:get_user_data:123
"\x80\x04\x95\x1a\x00\x00\x00\x00\x00\x00\x00}\x94(\x8c\x02id\x94\x8c\x03123\x94\x8c\x06detail\x94\x89u."
```

This gives you complete control over the cache key format while maintaining a clear namespace structure.


**Cache Invalidation:** Invalidate cache by key, pattern, or globally.


### Cache Invalidation
```python
await cache.delete("foo")  # Remove a single key
await cache.clear()        # Clear all cache

# Invalidate by pattern (Redis only)
cache = RedisCache()
# Set some test values
await cache.set("user:1", "data1")
await cache.set("user:2", "data2")
await cache.set("post:1", "post1")


```

**Serialization:** 


**Choosing a Serializer:**

Each serializer has specific use cases:

- **PickleSerializer (Default):**
    - Fastest performance
    - Handles complex Python objects
    - Security risk: vulnerable to code execution
    - Best for trusted internal systems

- **JsonSerializer:**
    - Human readable
    - Language-agnostic
    - Limited to JSON-serializable types
    - Best for web APIs or cross-service caching

- **StringSerializer:**
    - Minimal overhead
    - Limited to string data
    - Best for simple string caching

Example:
```python
from aiocache.serializers import JsonSerializer, PickleSerializer


from aiocache import cached, Cache
from typing import Any, Tuple, Dict

def custom_key_builder(
    namespace: str,
    fn: Any,
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
    fname = fn.__name__
    
    # Format args/kwargs into string
    args_str = ':'.join(str(arg) for arg in args)
    kwargs_str = ':'.join(f"{k}={v}" for k, v in kwargs.items())
    
    # Build key with components
    key_parts = [namespace, fname]
    if args_str:
        key_parts.append(args_str)
    if kwargs_str:
        key_parts.append(kwargs_str)
        
    return ':'.join(key_parts)

# Usage example
@cached(
    key_builder=custom_key_builder,
    ttl=10,
    cache=Cache.REDIS, 
    serializer=JsonSerializer(),
    namespace="n1",
    endpoint="localhost",
    port=6379,
    password="asdf",
    db=0,
    pool_max_size=10
)
async def get_user_data(user_id: str, detail: bool = False):
    return {"id": user_id, "detail": detail}


```

we can see that with json serializer the output is stored in json format in redis

```bash
127.0.0.1:6379> GET n1:example6:1234
"{\"id\": \"1234\", \"detail\": false}"
```


## Conclusion

aioCache makes it easy to add async caching to your Python applications, with powerful features and Redis support out of the box. It is a great choice for modern web APIs and microservices that need scalable, non-blocking caching.

For more details, visit the [aiocache documentation](https://aiocache.readthedocs.io/).

The example code for this guide can be found at:
- GitHub repository: [neural-engineer/example-projects](https://github.com/neural-engineer/example-projects)
- File path: `/redis/redis-cache.ipynb`

