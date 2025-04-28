# SSL Certificate Expiry Checker

In this article we will look at adding more capabilities to domain expiry tool we had looked at in the previous article . We will be looking at augmenting tool with capabilities to check certificate validity across domains and their associated subdomains automatically . 

You can try out the tool at https://domain-check-long-river-5458.fly.dev/

 You can find the link to the previous blog article at  https://medium.com/neural-engineer/domain-expiry-checker-752ecdd1d0b5


### SSL Certificate Check

The SSL certificate validation component :
- Performs subdomain discovery and validation
- It extract Certificate expiration dates and issuer details for domains and subdomains


### Code WalkThough

The SSL Certificate checker is implemented in the `ssl_check.py` module, which contains the `SSLChecker` class with several key functions:


####  `get_subdomains(self, domain)`
- Discovers subdomains associated with a root domain using multiple methods:
  - DNS record lookups (A, AAAA, CNAME records)
  - Checking common subdomain prefixes (www, mail, blog, etc.)
- Returns a list of discovered subdomains for comprehensive scanning

####  `get_certificate_info(self, hostname, port=443)`
- Establishes a secure connection to retrieve SSL certificate information
- Handles IDN (Internationalized Domain Names) encoding
- Extracts detailed certificate data including:
  - Issuer organization
  - Certificate subject
  - Valid dates (not before, not after)
  - Expiration information (days remaining)
  - Serial number and version
- Returns a structured dictionary with all certificate details or None on error

####  `check_domain_certificates(self, domain, notification_threshold_days=30)`
- Orchestrates the complete SSL validation process:
  1. Retrieves all subdomains for the given domain
  2. For each subdomain, fetches SSL certificate information
  3. Analyzes expiration dates against the notification threshold
  4. Adds status information (Valid or Expiring soon)
- Returns a consolidated list of certificate information for all domains and subdomains

This implementation uses Python's SSL libraries (`ssl`, `OpenSSL`) for certificate validation and `dnspython` for DNS lookups. The code handles various error conditions gracefully, with comprehensive logging for troubleshooting.

The modular design allows for easy integration into web applications or automation scripts, making it versatile for different deployment scenarios.


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
poetry run uvicorn domain_check.main:app --reload
```

Alternatively you can create a Docker image by running the command

```bash
docker build -t domain-checker .
```

You can run the container locally with:
```bash
docker run -p 8000:8000 domain-checker
```

Visit http://localhost:8000 to use the SSL certificate checker checker.

## Upcoming Features

- Email Security Verification
- Domain Health Score
- Advance Notifications 


## Conclusion

The Domain and SSL Certificate Expiry Checker provides essential monitoring capabilities for organizations managing multiple domains and SSL certificates. 

Future development will focus on scalability improvements, API integrations with popular domain registrars, and customizable alerting mechanisms to provide advance notification before critical expirations occur.
