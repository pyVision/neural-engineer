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

