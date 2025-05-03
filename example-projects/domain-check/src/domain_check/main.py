from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import os
from typing import List, Dict, Any, Optional
import datetime
import logging
from pathlib import Path

from pydantic import BaseModel, EmailStr, Field

from .domain_check import check_domains  
from .ssl_check import SSLChecker
from .notification_handler import NotificationHandler


ssl_checker = SSLChecker()
notification_handler = NotificationHandler()

# Keep the rest of your imports and functions
import ssl
import re
import socket
import datetime
import os
import logging
from typing import List, Pattern
from dataclasses import dataclass
import json

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

# Define Pydantic models for API requests and responses
class DomainRegistrationRequest(BaseModel):
    email: EmailStr
    domains: List[str] = Field(..., min_items=1, max_items=50)

class DomainUnregistrationRequest(BaseModel):
    email: EmailStr
    domains: Optional[List[str]] = None

class SubscriptionResponse(BaseModel):
    status: str
    message: str
    domains: Optional[List[str]] = None

# Keep all your existing functions (check_domain_expiry, etc.)
# ... (all your existing functions remain the same)


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from multiprocessing import Process
import time
from .notification_scheduler import NotificationScheduler

# Create and run the scheduler
scheduler = NotificationScheduler()

def scheduled_domain_check():
    """
    Run domain and SSL checks for all registered domains in the system.
    This function will be executed on a schedule.
    """
    logging.info("Running scheduled domain and SSL checks")
    try:
        # Use the existing method in NotificationHandler that already contains this logic
        results = scheduler.run_scheduled_check()

        # Print results summary
        logging.info(f"Check completed at {results['end_time']}")
        logging.info(f"Duration: {results['duration_seconds']:.2f} seconds")
        logging.info(f"Notifications sent: {results['notifications_sent']}")

        # Save results to a JSON file for record-keeping
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.environ.get("RESULTS_DIR", "results")
        
        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
        results_file = os.path.join(results_dir, f"notification_check_{timestamp}.json")
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logging.info(f"Results saved to {results_file}")
        print(f"Results saved to {results_file}")

        logging.info("Completed scheduled domain and SSL checks")
        return results
    except Exception as e:
        logging.error(f"Error in scheduled domain check: {str(e)}")
        return {"error": str(e)}

@app.post("/api/run-check", response_class=JSONResponse)
async def run_domain_check():
    """
    API endpoint to manually trigger the domain and SSL checks.
    Returns the results of the check operation.
    """
    try:
        results = scheduled_domain_check()
        if results and "error" in results:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": results["error"]}
            )
        return JSONResponse(
            content={"status": "success", "results": results}
        )
    except Exception as e:
        logging.error(f"Error in API domain check: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


def run_scheduler():
    """
    Start the background scheduler in a separate process.
    This function starts a scheduler that runs every day at 2 AM.
    """
    scheduler = BackgroundScheduler()
    
    # Run every day at 2 AM
    scheduler.add_job(
        scheduled_domain_check,
        trigger=CronTrigger(hour=2, minute=0),
        id="domain_check_job",
        name="Check domain and SSL expirations",
        replace_existing=True
    )
    
    scheduler.start()
    logging.info("Background scheduler started for domain checks")
    
    try:
        # Keep the process alive
        while True:
            time.sleep(3600)  # Sleep for 1 hour
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Background scheduler stopped")

# Start the scheduler in a separate process when the application starts
def start_background_scheduler():
    """
    Start the background scheduler in a separate process.
    """
    process = Process(target=run_scheduler)
    process.daemon = True  # Daemonize to ensure it exits when the main process exits
    process.start()
    logging.info(f"Background scheduler started in process {process.pid}")
    return process

# Add this to the startup events for the FastAPI app
@app.on_event("startup")
async def startup_event():
    logging.info("Starting up the application")
    start_background_scheduler()


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

# New notification API endpoints
@app.post("/api/notifications/register", response_model=SubscriptionResponse)
async def register_domain_notifications(request: DomainRegistrationRequest):
    """
    Register domains for notification emails.
    This endpoint allows users to register their email address to receive notifications
    about domain or SSL certificate expiry for specific domains.
    """
    result = notification_handler.register_domains(request.email, request.domains)
    return JSONResponse(content=result)

@app.get("/api/notifications/{email}/domains")
async def get_registered_domains(email: str):
    """
    Get all domains registered for notifications for a specific email.
    """
    domains = notification_handler.get_domains(email)
    return {"email": email, "domains": domains}

@app.post("/api/notifications/unregister", response_model=SubscriptionResponse)
async def unregister_domain_notifications(request: DomainUnregistrationRequest):
    """
    Unregister domains from notification service.
    If specific domains are provided, only those domains are unregistered.
    If no domains are provided, all domains for the email are marked as inactive.
    """
    result = notification_handler.unregister_domains(request.email, request.domains)
    return JSONResponse(content=result)

@app.get("/api/notifications/all")
async def get_all_subscriptions():
    """
    Get all active notification subscriptions.
    This endpoint is for administrative use only.
    """
    subscriptions = notification_handler.get_all_subscriptions()
    return {"subscriptions": subscriptions, "count": len(subscriptions)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
