# Python Request Optimization: Caching and Rate Limiting

## Introduction
In this technical blog, we'll explore two powerful Python packages: `requests_cache` (>=1.0) and `requests_ratelimiter` (>=0.3.1). These packages help optimize HTTP requests through caching and rate limiting, essential for building robust and efficient web scrapers or API clients.

## requests_cache: Intelligent HTTP Caching

### Overview
`requests_cache` is a transparent caching library that seamlessly integrates with the popular `requests` library, storing responses for later use and reducing unnecessary network calls.

### Key Features
- Multiple backend support (SQLite, Redis, MongoDB)
- Flexible cache expiration policies
- Conditional request handling (ETags, Last-Modified)
- Query parameter filtering

### Example Implementation
```python
import requests_cache
# Make requests and measure time
import time


print("--------------------- CACHING ---------------------")
# Initialize cached session
session = requests_cache.CachedSession(
    'my_cache',
    backend='sqlite',
    expire_after=3600  # Cache for 1 hour
)



# First request
start_time = time.time()
response = session.get('http://httpbin.org/get')
elapsed = time.time() - start_time
print(f"Time taken: {elapsed:.2f}s")
print(f"From cache: {response.from_cache}")

# Second request (cached)
start_time = time.time()
response = session.get('http://httpbin.org/get')
elapsed = time.time() - start_time
print(f"Time taken: {elapsed:.2f}s")
print(f"From cache: {response.from_cache}")

```

Below is the output of running the above script 


```
% python3 main.py
Time taken: 1.65s
From cache: False
Time taken: 0.01s
From cache: True

 % python3 main.py
Time taken: 0.01s
From cache: True
Time taken: 0.00s
From cache: True
```

The output demonstrates two important aspects of `requests_cache`:

1. **Initial Cache Creation**
    - First run: Initial request takes 1.65s (cache miss)
    - Second request is near-instant at 0.01s (cache hit)

2. **Persistent Storage**
    - Second script run: Both requests are instant (0.01s, 0.00s)
    - Cache persists between script executions
    - Demonstrates SQLite backend storing data on disk

This shows how `requests_cache` effectively reduces network calls and maintains cache across program restarts.



## requests_ratelimiter: Control Request Frequency

### Overview
`requests_ratelimiter` helps prevent API rate limit violations by controlling request frequency. It's particularly useful when working with APIs that have strict rate limits.

### Key Features
- Fixed and dynamic rate limiting
- Multiple rate limit rules
- Queue-based request management
- Integration with requests_cache

### Example Implementation
```python
print("--------------------- RATE LIMITING ---------------------")
from requests_ratelimiter import LimiterSession

# Create rate-limited session
session = LimiterSession(
    per_minute=2,  # 2 requests per minute
    burst_size=5   # Allow burst of 5 requests
)

# Requests are automatically rate-limited
for i in range(2):
    start_time = time.time()
    response = session.get('http://httpbin.org/get')
    elapsed = time.time() - start_time
    print(f"Response {i+1}, Time taken: {elapsed:.2f}s, Response: {response}")
```

Below is the output of the script

```
Response 1, Time taken: 3.19s, Response: <Response [200]>
Response 2, Time taken: 1.83s, Response: <Response [200]>
Response 3, Time taken: 58.86s, Response: <Response [200]>
Response 4, Time taken: 6.09s, Response: <Response [200]>
```

The code configures rate limiting with:

per_second=2: Maximum 2 requests per second
burst_size=5: Can burst up to 5 requests initially

- First two requests complete quickly (3.19s and 1.83s) .This is because they fall within the initial burst allowance
- The third request takes significantly longer (58.86s) . This dramatic increase in time indicates the rate limiter is actively throttling requests . The long delay ensures the code maintains the "2 requests per second" rule . 


## Combining Both Packages

### Best Practices
```python

print("--------------- CACHE AND RATE LIMITING ----------------- ")

# Create a cached session with rate limiting
cached_session = requests_cache.CachedSession(
    'combined_cache',
    backend='sqlite'
)

session = LimiterSession(
    per_minute=2,
    burst_size=5,
    session=cached_session
)

# Requests are cached and  rate-limited
for i in range(2):
    start_time = time.time()
    response = session.get('http://httpbin.org/get')
    elapsed = time.time() - start_time
    print(f"Response {i+1}, Time taken: {elapsed:.2f}s, Response: {response}")


```

Below is the output of the script

```
--------------------- RATE LIMITING ---------------------
Response 1, Time taken: 4.70s, Response: <Response [200]>
Response 2, Time taken: 1.77s, Response: <Response [200]>
--------------- CACHE AND RATE LIMITING ----------------- 
Response 1, Time taken: 4.25s, Response: <Response [200]>
Response 2, Time taken: 0.95s, Response: <Response [200]>
```

As we can see that second request is cached and response is returned within 0.95s


## Use Cases

   - Cache frequently accessed pages and API calls
   - Respect website rate limits and API rate limits 
   - Reduce bandwidth usage and improve application performance


## Conclusion
Combining `requests_cache` and `requests_ratelimiter` creates a robust foundation for web scraping and API integration projects. These tools help build more efficient and respectful web clients while reducing server load and improving application performance.