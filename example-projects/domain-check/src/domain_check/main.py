from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from typing import List, Dict, Any, Optional
import datetime
import logging
from pathlib import Path


from .domain_check import check_domains  
from .ssl_check import SSLChecker


ssl_checker=SSLChecker()

# Keep the rest of your imports and functions
import ssl
import re
import socket
import datetime
import os
import logging
from typing import List, Pattern
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='domain_check.log'
)

# Create FastAPI app
app = FastAPI(title="Domain Expiry Checker")

# Set up templates directory
templates = Jinja2Templates(directory="templates")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Keep your existing dataclass and functions
suffixes: Optional[set] = None
@dataclass
class DomainInfo:
    domain: str
    domain_expiry: datetime.datetime
    ssl_expiry: Optional[datetime.datetime] = None

# Keep all your existing functions (check_domain_expiry, etc.)
# ... (all your existing functions remain the same)

# Create new functions for the FastAPI routes
@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "domains": "", 
        "threshold": 30,
        "results": None,
        "active_tab": "domain"
    })

@app.post("/check-domains", response_class=HTMLResponse)
async def check_domains_form(request: Request, domains: str = Form(...), threshold: int = Form(30)):
    # Parse domains from input (support both comma-separated and newline-separated)
    domains_list = []
    for domain in re.split(r'[,\n]', domains):
        domain = domain.strip()
        if domain:
            domains_list.append(domain)
    
    # Process domains and collect results
    results = check_domains(domains_list, threshold)

    # Return the template with results
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "domains": domains, 
        "threshold": threshold,
        "results": results,
        "active_tab": "domain"
    })

@app.post("/check-ssl", response_class=HTMLResponse)
async def check_ssl_form(request: Request, domains: str = Form(...), threshold: int = Form(30)):
    # Parse domains from input (support both comma-separated and newline-separated)
    domains_list = []
    for domain in re.split(r'[,\n]', domains):
        domain = domain.strip()
        if domain:
            domains_list.append(domain)
    
    ssl_results=[]
    # Process domains and collect SSL certificate results
    for d in domains_list:
        ss = ssl_checker.check_domain_certificates(d,threshold)

 
        
        ssl_results.extend(ss)
    # Return the template with results
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "domains": domains, 
        "threshold": threshold,
        "ssl_results": ssl_results,
        "active_tab": "ssl"
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
