# Domain Expiry Checker

In this blog we will look at developing an tool that checks domain expiration dates and provides a simple web interface for users to view the results.

## Features
- Bulk domain checking (up to 5 domains at once)
- DNS record validation for domain existence
- Rate limiting to prevent abuse

## Technical Implementation


### Core Components

The application is built using these key technologies:
- FastAPI for the web framework
- python-whois for domain information
- dnspython for DNS record validation
- Jinja2 for HTML templating

### Code Walkthrough

### Repository Structure
```
domain-check/
├── main.py                 # FastAPI application
├── src/
│   └── domain_check/
│       └── domain_check.py # Core domain checking functionality
├── templates/
│   └── index.html         # Frontend template
├── requirements.txt       # Project dependencies
└── README.md             # Documentation
```

#### 1. Domain Validation (domain_check.py)
The core domain validation logic uses multiple layers of verification:

```python
def is_valid_domain(domain: str) -> bool:
    """
    Validate a domain through format checking and DNS record lookup.
    
    Args:
        domain: Domain name to validate
        
    Returns:
        bool: True if domain format is valid and has DNS records
    """
    # Remove protocol and path if present
    domain = re.sub(r'^.*://', '', domain)
    domain = domain.split('/')[0].lower()
    
    # Check domain format using regex
    domain_pattern = re.compile(
        r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
    )
    
    if not domain_pattern.match(domain):
        return False
    
    # Try DNS resolution with multiple record types
    try:
        resolver = dns.resolver.Resolver()
        for record_type in ['A', 'AAAA', 'MX', 'NS']:
            try:
                answers = resolver.resolve(domain, record_type)
                if answers:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False
```

This function implements a two-step validation:
1. Format validation using regex pattern matching
2. DNS record verification trying multiple record types (A, AAAA, MX, NS)

#### 2. Domain Expiry Checking (main.py)
The expiry checking function handles various edge cases and domain types:

```python
def check_domain_expiry(domain: str) -> dict:
    """
    Check domain expiry and return relevant information.
    
    Returns:
        dict: Domain information including expiry date, days left, 
              registrar, owner and status
    """
    try:
        if not is_valid_domain(domain):
            return {
                "domain": domain,
                "expiry_date": "Invalid domain",
                "days_left": -1,
                "registrar": "N/A",
                "owner": "N/A"
            }
            
        w = whois.whois(domain)
        expiry_date = w.expiration_date
        
        # Handle multiple expiry dates (some registrars return a list)
        if isinstance(expiry_date, list):
            expiry_date = expiry_date[0]
            
        # Special handling for .ai domains
        if expiry_date is None and domain.endswith('.ai'):
            return {
                "domain": domain,
                "expiry_date": "Not available for .ai domains",
                "days_left": -1,
                "registrar": w.registrar or "Unknown",
                "owner": w.name or "Unknown"
            }
```

Key features:
- Handles multiple expiry date formats
- Special case for .ai domains that don't return expiry dates by python-whois code
- Graceful error handling with informative messages

#### 3. Rate Limiting Implementation
The application implements IP-based rate limiting to prevent abuse:

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting based on client IP."""
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        
        # Reset counter if more than 1 second has passed
        if current_time - rate_limit_dict[client_ip]["last_request"] >= 1:
            rate_limit_dict[client_ip]["requests"] = 0
            rate_limit_dict[client_ip]["last_request"] = current_time
        
        if rate_limit_dict[client_ip]["requests"] >= RATE_LIMIT:
            return HTMLResponse(
                content="Rate limit exceeded. Please try again in a moment.",
                status_code=429
            )
```

### Source Code
The complete source code for this project is available on GitHub:
- Repository: https://github.com/pyVision/neural-engineer
- Project Path: `/example-projects/domain-check/`


## Installation and Setup

1. Create a Python virtual environment:
```bash
git clone https://github.com/pyVision/neural-engineer.git
cd example-projects/domain-check/
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
poetry install
```

3. Run the application:
```bash
uvicorn domain_check.main:app --reload
```

Alternatively you can create a Docker image by running the command

```bash
docker build -t domain-checker .
```

You can run the container with:
```bash
docker run -p 8000:8000 domain-checker
```


Visit http://localhost:8000 to use the domain checker.

The tool is hosted on 