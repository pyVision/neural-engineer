from fastapi import FastAPI, Request, Form, HTTPException, Cookie, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import uvicorn
import os
from typing import List, Dict, Any, Optional
import datetime
import logging
from pathlib import Path
import time
import posthog
from starlette.middleware.base import BaseHTTPMiddleware

from pydantic import BaseModel, EmailStr, Field

from .domain_check import check_domains  
from .ssl_check import SSLChecker
from .notification_handler import NotificationHandler
from .otp_handler import OTPHandler
from .init_application import initialization_result
import redis 
# PostHog configuration
POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY", "your_api_key")
POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")

# Initialize PostHog
posthog.api_key = POSTHOG_API_KEY
posthog.host = POSTHOG_HOST


redis_client = redis.Redis(
                    host=initialization_result["env_vars"]["REDIS_HOST"],
                    port=initialization_result["env_vars"]["REDIS_PORT"],
                    password=initialization_result["env_vars"]["REDIS_PASSWORD"],
                    decode_responses=True,
                    
            )

ssl_checker = SSLChecker()
notification_handler = NotificationHandler(redis_client=redis_client)
otp_handler = OTPHandler(redis_client=redis_client)

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
    otp: str  # Include OTP directly in the request

class DomainUnregistrationRequest(BaseModel):
    email: EmailStr
    domains: Optional[List[str]] = None
    otp: str  # Include OTP directly in the request for verification

class SubscriptionResponse(BaseModel):
    status: str
    message: str
    domains: Optional[List[str]] = None
    
class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp: str

class OTPVerificationResponse(BaseModel):
    status: str
    message: str
    
class OTPGenerationRequest(BaseModel):
    email: EmailStr
    operation: str  # 'register' or 'view'
    force_new: bool = False  # Optionally force generation of a new OTP even if one exists
    
class OTPGenerationResponse(BaseModel):
    status: str
    message: str
    email: EmailStr
    created_at: Optional[str] = None
    expires_in: Optional[str] = None
    existing_code: Optional[bool] = False

# Keep all your existing functions (check_domain_expiry, etc.)
# ... (all your existing functions remain the same)


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from multiprocessing import Process
import time
from .notification_scheduler import NotificationScheduler

# Create and run the scheduler
scheduler = NotificationScheduler()

async def scheduled_domain_check():
    """
    Run domain and SSL checks for all registered domains in the system.
    This function will be executed on a schedule.
    """
    start_time = time.time()
    logging.info("Running scheduled domain and SSL checks")
    
    # Track start of scheduled check
    try:
        from .analytics import track_event
        track_event(
            distinct_id='system',
            event_name='scheduled_check_started',
            properties={
                'timestamp': datetime.datetime.now().isoformat()
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track scheduled check start: {e}")
    
    try:
        # Use the existing method in NotificationHandler that already contains this logic
        results = await scheduler.run_scheduled_check()

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

        # Track successful completion
        try:
            from .analytics import track_event
            track_event(
                distinct_id='system',
                event_name='scheduled_check_completed',
                properties={
                    'duration_seconds': results['duration_seconds'],
                    'notifications_sent': results['notifications_sent'],
                    'domains_checked': results.get('domains_checked', 0),
                    'success': True
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track scheduled check completion: {e}")

        logging.info("Completed scheduled domain and SSL checks")
        return results
    except Exception as e:
        # Track error in scheduled check
        try:
            from .analytics import track_event
            track_event(
                distinct_id='system',
                event_name='scheduled_check_error',
                properties={
                    'error_message': str(e),
                    'error_type': type(e).__name__,
                    'duration_seconds': time.time() - start_time
                }
            )
        except Exception as analytics_error:
            logging.warning(f"Failed to track scheduled check error: {analytics_error}")
            
        logging.error(f"Error in scheduled domain check: {str(e)}")
        return {"error": str(e)}

@app.post("/api/run-check", response_class=JSONResponse)
async def run_domain_check():
    """
    API endpoint to manually trigger the domain and SSL checks.
    Returns the results of the check operation.
    """
    try:
        results = await scheduled_domain_check()
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
    while True:

        scheduler = BackgroundScheduler()
        
        # Run every day at 2 AM
        scheduler.add_job(
            scheduled_domain_check,
            trigger=CronTrigger(hour=2, minute=0),
            id="domain_check_job",
            name="Check domain and SSL expirations",
            replace_existing=True,
            misfire_grace_time=3600  # Allow jobs to be executed up to 1 hour late
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
            continue

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
    
    # Initialize PostHog analytics with values from initialization_result
    try:
        from .analytics import initialize_analytics, track_event
        
        # Get PostHog config from initialization_result
        posthog_api_key = initialization_result.get("env_vars", {}).get("POSTHOG_API_KEY")
        posthog_host = initialization_result.get("env_vars", {}).get("POSTHOG_HOST")
        
        # Initialize analytics with values from initialization_result
        analytics_initialized = initialize_analytics(api_key=posthog_api_key, host=posthog_host)
        if analytics_initialized:
            logging.info("PostHog analytics initialized successfully")
        else:
            logging.warning("PostHog analytics initialization failed or disabled")
        
        # Track application startup in PostHog
        track_event(
            'system', 
            'application_started',
            {
                'version': initialization_result.get("version", "unknown"),
                'environment': initialization_result.get("environment", "production"),
                'debug_mode': initialization_result.get("debug_mode", False)
            }
        )
    except Exception as e:
        logging.warning(f"Failed to initialize analytics: {e}")

# Register the analytics middleware
try:
    from .analytics import AnalyticsMiddleware
    app.add_middleware(AnalyticsMiddleware)
    logging.info("Analytics middleware registered")
except Exception as e:
    logging.warning(f"Failed to register analytics middleware: {e}")


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
    
    posthog.capture(
        'anonymous',  # We don't have user email in this endpoint
        'domain_check',
        {
            'domain_count': len(domains_list),
            'threshold_days': threshold,
            'domains': domains_list  # List of domains being checked
        }
    )

    # Process domains and collect results
    results = await check_domains(domains_list, threshold)

    # Track results
    valid_count = len(results)
    # Count domains by status
    warning_count = sum(1 for r in results if r.get('days_left') is not None and 0 <= r.get('days_left') < 30 )
    valid_count = sum(1 for r in results if r.get('status') == "Valid domain")
    warning_count = sum(1 for r in results if r.get('status') == "Expiring soon!")
    expired_count = sum(1 for r in results if r.get('status') != "Invalid domain" or r.get('status') == "Expired" or r.get('status') == "Expiring today!")

    

    posthog.capture(
        'anonymous',
        'domain_check_results',
        {
            'domain_count': len(domains_list),
            'expired_count': expired_count,
            'warning_count': warning_count,
            'valid_count': valid_count
        }
    )

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
    
    # Track SSL check request in PostHog
    try:
        from .analytics import track_event
        track_event(
            distinct_id='anonymous',  # We don't have user email in this endpoint
            event_name='ssl_check',
            properties={
                'domain_count': len(domains_list),
                'threshold_days': threshold,
                'domains': domains_list
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track SSL check request: {e}")
    
    ssl_results=[]
    # Process domains and collect SSL certificate results
    for d in domains_list:
        ss = await ssl_checker.check_domain_certificates(d,threshold)
        ssl_results.extend(ss)
    
    # Track results: count certificates by status
    try:
        # Count certificates by status
        expired_count = sum(1 for r in ssl_results if r.get('status') == "Expired" or r.get('status') == "today!")
        warning_count = sum(1 for r in ssl_results if r.get('status') == "Expiring soon!")
        valid_count = sum(1 for r in ssl_results if r.get('status') == "Valid SSL")
        
        from .analytics import track_event
        track_event(
            distinct_id='anonymous',
            event_name='ssl_check_results',
            properties={
                'domain_count': len(domains_list),
                'certificate_count': len(ssl_results),
                'expired_count': expired_count,
                'warning_count': warning_count,
                'valid_count': valid_count,
                'threshold_days': threshold
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track SSL check results: {e}")
    
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
    
    Requires OTP passed directly in the request for verification.
    """
    # Start tracking this operation in PostHog
    try:
        from .analytics import track_event
        track_event(
            distinct_id=request.email,
            event_name='domain_registration_started',
            properties={
                'domain_count': len(request.domains),
                'domains': request.domains
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track domain registration start: {e}")
    
    # Check if OTP was provided
    if not request.otp:
        # Track missing OTP
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='domain_registration_error',
                properties={
                    'error_type': 'missing_otp',
                    'domain_count': len(request.domains)
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track missing OTP error: {e}")
            
        return JSONResponse(content={
            "status": "error",
            "message": "Verification code required. Please provide a verification code.",
            "require_otp": True
        }, status_code=403)
    
    # Verify the OTP directly
    success, message = otp_handler.verify_otp(request.email, request.otp)
    logging.info(f"OTP verification for registration: {success}, message: {message}")

    # Track OTP verification step
    try:
        from .analytics import track_event
        track_event(
            distinct_id=request.email,
            event_name='otp_verification_attempted',
            properties={
                'success': success,
                'message': message,
                'operation': 'domain_registration'
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track OTP verification attempt: {e}")

    if not success:
        # Track failed verification
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='domain_registration_error',
                properties={
                    'error_type': 'invalid_otp',
                    'message': message
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track failed verification: {e}")
            
        return JSONResponse(content={
            "status": "error",
            "message": f"Verification failed: {message}",
            "require_otp": True
        }, status_code=403)
    
    try:
        # Process the registration
        result = notification_handler.register_domains(request.email, request.domains)
        
        # Track successful registration
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='domain_registration_completed',
                properties={
                    'domain_count': len(request.domains),
                    'success': result.get('status') == 'success',
                    'domains': request.domains
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track successful registration: {e}")
        
        # Reset the OTP after successful registration
        #otp_handler.reset_otp(request.email)
        
        return JSONResponse(content=result)
    except Exception as e:
        # Track registration exception
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='domain_registration_error',
                properties={
                    'error_type': 'registration_exception',
                    'error_message': str(e),
                    'domains': request.domains
                }
            )
        except Exception as analytics_error:
            logging.warning(f"Failed to track registration exception: {analytics_error}")
            
        logging.error(f"Error registering domains: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Failed to register domains: {str(e)}"
        }, status_code=500)

@app.get("/api/notifications/{email}/domains")
async def get_registered_domains(email: str, otp: str = None):
    """
    Get all domains registered for notifications for a specific email.
    
    Requires OTP passed as a query parameter for verification.
    """
    # Track domain retrieval request in PostHog
    try:
        from .analytics import track_event
        track_event(
            distinct_id=email,
            event_name='domain_retrieval_started',
            properties={
                'timestamp': datetime.datetime.now().isoformat()
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track domain retrieval start: {e}")
    
    # Check if OTP was provided
    if not otp:
        # Track missing OTP error
        try:
            from .analytics import track_event
            track_event(
                distinct_id=email,
                event_name='domain_retrieval_error',
                properties={
                    'error_type': 'missing_otp',
                    'timestamp': datetime.datetime.now().isoformat()
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track domain retrieval error (missing OTP): {e}")
            
        return JSONResponse(content={
            "status": "error",
            "message": "Verification code required. Please provide a verification code.",
            "require_otp": True
        }, status_code=403)
    
    # Verify the OTP directly
    success, message = otp_handler.verify_otp(email, otp)
    logging.info(f"OTP verification for domain retrieval: {success}, message: {message}")
    
    # Track OTP verification result
    try:
        from .analytics import track_event
        track_event(
            distinct_id=email,
            event_name='otp_verification_attempted',
            properties={
                'success': success,
                'message': message,
                'operation': 'domain_retrieval'
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track OTP verification for domain retrieval: {e}")
    
    if not success:
        # Track verification failure
        try:
            from .analytics import track_event
            track_event(
                distinct_id=email,
                event_name='domain_retrieval_error',
                properties={
                    'error_type': 'invalid_otp',
                    'message': message,
                    'timestamp': datetime.datetime.now().isoformat()
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track domain retrieval error (invalid OTP): {e}")
            
        return JSONResponse(content={
            "status": "error",
            "message": f"Verification failed: {message}",
            "require_otp": True
        }, status_code=403)
    
    # Verify operation matches
    # if operation != "view":
    #     return JSONResponse(content={
    #         "status": "error",
    #         "message": "This verification code cannot be used for viewing domains.",
    #         "require_otp": True
    #     }, status_code=403)
    
    try:
        # Get the domains
        domains = notification_handler.get_domains(email)
        
        # Track successful domain retrieval
        try:
            from .analytics import track_event
            track_event(
                distinct_id=email,
                event_name='domain_retrieval_completed',
                properties={
                    'domain_count': len(domains),
                    'has_domains': len(domains) > 0,
                    'timestamp': datetime.datetime.now().isoformat()
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track successful domain retrieval: {e}")
        
        # Reset the OTP after successfully retrieving domains
        #otp_handler.reset_otp(email)
        
        return {"email": email, "domains": domains}
    except Exception as e:
        # Track domain retrieval exception
        try:
            from .analytics import track_event
            track_event(
                distinct_id=email,
                event_name='domain_retrieval_error',
                properties={
                    'error_type': 'retrieval_exception',
                    'error_message': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                }
            )
        except Exception as analytics_error:
            logging.warning(f"Failed to track domain retrieval exception: {analytics_error}")
        
        logging.error(f"Error retrieving domains for {email}: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Failed to retrieve domains: {str(e)}"
        }, status_code=500)

@app.post("/api/notifications/unregister", response_model=SubscriptionResponse)
async def unregister_domain_notifications(request: DomainUnregistrationRequest):
    """
    Unregister domains from notification service.
    If specific domains are provided, only those domains are unregistered.
    If no domains are provided, all domains for the email are marked as inactive.
    
    Requires OTP verification to ensure only authorized users can unregister domains.
    """
    # Track domain unregistration attempt
    try:
        from .analytics import track_event
        track_event(
            distinct_id=request.email,
            event_name='domain_unregistration_started',
            properties={
                'domain_count': len(request.domains) if request.domains else 0,
                'domains': request.domains,
                'unregister_all': request.domains is None or len(request.domains) == 0,
                'timestamp': datetime.datetime.now().isoformat()
            }
        )
    except Exception as e:
        logging.warning(f"Failed to track domain unregistration start: {e}")
        
    try:
        # Check if OTP was provided
        if not request.otp:
            # Track missing OTP error
            try:
                from .analytics import track_event
                track_event(
                    distinct_id=request.email,
                    event_name='domain_unregistration_error',
                    properties={
                        'error_type': 'missing_otp',
                        'domain_count': len(request.domains) if request.domains else 0,
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logging.warning(f"Failed to track missing OTP error: {e}")
                
            return JSONResponse(content={
                "status": "error",
                "message": "Verification code required. Please provide a verification code to unregister domains.",
                "require_otp": True
            }, status_code=403)
        
        # Verify the OTP directly
        success, message = otp_handler.verify_otp(request.email, request.otp)
        logging.info(f"OTP verification for domain unregistration: {success}, message: {message}")
        
        # Track OTP verification attempt
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='otp_verification_attempted',
                properties={
                    'success': success,
                    'message': message,
                    'operation': 'domain_unregistration'
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track OTP verification attempt: {e}")
        
        if not success:
            # Track failed verification
            try:
                from .analytics import track_event
                track_event(
                    distinct_id=request.email,
                    event_name='domain_unregistration_error',
                    properties={
                        'error_type': 'invalid_otp',
                        'message': message,
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logging.warning(f"Failed to track failed verification: {e}")
                
            return JSONResponse(content={
                "status": "error",
                "message": f"Verification failed: {message}",
                "require_otp": True
            }, status_code=403)
        
        try:
            # Process the unregistration
            result = notification_handler.unregister_domains(request.email, request.domains)
            
            # Track successful unregistration
            try:
                from .analytics import track_event
                track_event(
                    distinct_id=request.email,
                    event_name='domain_unregistration_completed',
                    properties={
                        'domain_count': len(request.domains) if request.domains else 0,
                        'unregistered_count': len(result.get("domains", [])) if "domains" in result else 0,
                        'unregister_all': request.domains is None or len(request.domains) == 0,
                        'success': result.get('status') == 'success',
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logging.warning(f"Failed to track successful unregistration: {e}")
            
            # Reset the OTP after successful unregistration
            #otp_handler.reset_otp(request.email)
            
            return JSONResponse(content=result)
        except Exception as domain_error:
            # Track domain unregistration failure
            try:
                from .analytics import track_event
                track_event(
                    distinct_id=request.email,
                    event_name='domain_unregistration_error',
                    properties={
                        'error_type': 'unregistration_exception',
                        'error_message': str(domain_error),
                        'domain_count': len(request.domains) if request.domains else 0,
                        'domains': request.domains,
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                )
            except Exception as analytics_error:
                logging.warning(f"Failed to track domain unregistration error: {analytics_error}")
            
            # Log and handle domain unregistration errors
            logging.error(f"Error unregistering domains for {request.email}: {str(domain_error)}")
            return JSONResponse(content={
                "status": "error",
                "message": f"Failed to unregister domains: {str(domain_error)}"
            }, status_code=500)
            
    except Exception as e:
        # Track general error
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='domain_unregistration_error',
                properties={
                    'error_type': 'general_exception',
                    'error_message': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                }
            )
        except Exception as analytics_error:
            logging.warning(f"Failed to track general unregistration error: {analytics_error}")
            
        # Log and handle general endpoint errors
        logging.error(f"Unhandled exception in unregister_domain_notifications: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return JSONResponse(content={
            "status": "error",
            "message": "An unexpected error occurred while processing your request. Please try again later."
        }, status_code=500)

@app.get("/api/notifications/all")
async def get_all_subscriptions():
    """
    Get all active notification subscriptions.
    This endpoint is for administrative use only.
    """
    subscriptions = notification_handler.get_all_subscriptions()
    return {"subscriptions": subscriptions, "count": len(subscriptions)}

# Add after the existing API endpoints

@app.post("/api/otp/generate", response_model=OTPGenerationResponse)
async def generate_otp(request: OTPGenerationRequest):
    """
    Generate a 12-digit alphanumeric OTP for email verification.
    
    This endpoint generates a one-time password that will be sent to the provided email address.
    The OTP is required before domain registration or viewing can proceed.
    
    If a valid unexpired OTP already exists, it won't generate a new one unless force_new=True.
    """
    try:
        # Track OTP generation request in PostHog
        try:
            from .analytics import track_event, identify_user, get_email_domain
            
            # Identify user with email domain for demographic analysis
            identify_user(
                distinct_id=request.email,
                properties={
                    'email_domain': get_email_domain(request.email),
                    'first_seen_at': datetime.datetime.now().isoformat(),
                    'last_operation': request.operation
                }
            )
        except Exception as e:
            logging.warning(f"Failed to identify user: {e}")
        
        # Get force_new parameter from query or default to False
        force_new = request.force_new if hasattr(request, 'force_new') else False
        
        # Generate the OTP (or get existing one)
        otp, created_time, is_new = otp_handler.generate_otp(request.email, request.operation, force_new)
        
        # Track OTP generation in PostHog
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='otp_generated',
                properties={
                    'operation': request.operation,
                    'force_new': force_new,
                    'is_new_otp': is_new
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track OTP generation: {e}")
        
        # Only send email if we generated a new OTP or specifically requested resend
        if is_new or force_new:
            # Send the OTP email
            email_sent = otp_handler.send_otp_email(request.email, otp, request.operation, created_time)
            
            # Track email delivery attempt
            try:
                from .analytics import track_event
                track_event(
                    distinct_id=request.email,
                    event_name='otp_email_sent',
                    properties={
                        'success': email_sent,
                        'operation': request.operation
                    }
                )
            except Exception as e:
                logging.warning(f"Failed to track OTP email sending: {e}")
            
            if email_sent:
                # Format creation time for display
                creation_date = datetime.datetime.fromisoformat(created_time).strftime("%Y-%m-%d %H:%M:%S")
                expiry_days = int(initialization_result["env_vars"].get("OTP_EXPIRY_DAYS", 30))
                
                # In production, don't include the OTP in the response
                # For development/testing, we'll include it to make testing easier
                debug_info = f" For testing: {otp}" if initialization_result["debug_mode"] else ""
                
                # Track in funnel: OTP generated → Email sent
                try:
                    from .analytics import track_event
                    track_event(
                        distinct_id=request.email,
                        event_name='otp_flow_email_delivered',
                        properties={
                            'operation': request.operation
                        }
                    )
                except Exception as e:
                    logging.warning(f"Failed to track OTP flow: {e}")
                
                return JSONResponse(content={
                    "status": "success",
                    "message": f"Verification code has been sent to {request.email}.{debug_info} Please check your email and enter the code to continue.",
                    "email": request.email,
                    "created_at": creation_date,
                    "expires_in": f"{expiry_days} days"
                })
            else:
                # Track email failure
                try:
                    from .analytics import track_event
                    track_event(
                        distinct_id=request.email,
                        event_name='otp_email_failed',
                        properties={
                            'operation': request.operation
                        }
                    )
                except Exception as e:
                    logging.warning(f"Failed to track OTP email failure: {e}")
                
                return JSONResponse(content={
                    "status": "warning",
                    "message": f"OTP generated, but there was an issue sending the email. Please try again or contact support.",
                    "email": request.email
                })
        else:
            # Return existing OTP info without sending a new email
            creation_date = datetime.datetime.fromisoformat(created_time).strftime("%Y-%m-%d %H:%M:%S")
            expiry_days = int(initialization_result["env_vars"].get("OTP_EXPIRY_DAYS", 30))
            
            return JSONResponse(content={
                "status": "info",
                "message": f"A verification code was already sent to {request.email} on {creation_date}. It remains valid for {expiry_days} days. Please check your email or request a new code if needed.",
                "email": request.email,
                "created_at": creation_date,
                "expires_in": f"{expiry_days} days",
                "existing_code": True
            })
    except Exception as e:
        # Track exception in PostHog
        try:
            from .analytics import track_event
            track_event(
                distinct_id=request.email,
                event_name='error',
                properties={
                    'error_type': 'otp_generation_error',
                    'error_message': str(e),
                    'endpoint': '/api/otp/generate'
                }
            )
        except Exception as analytics_error:
            logging.warning(f"Failed to track OTP generation error: {analytics_error}")
            
        logging.error(f"Error generating OTP: {e}")
        return JSONResponse(content={
            "status": "error",
            "message": "Failed to generate OTP",
            "email": request.email
        }, status_code=500)

@app.post("/api/otp/verify", response_model=OTPVerificationResponse)
async def verify_otp(request: OTPVerificationRequest, response: Response):
    """
    Verify an OTP for email verification.
    
    This endpoint verifies the OTP provided by the user against the one stored in the system.
    If verified, the user can proceed with domain registration or viewing.
    """
    try:
        # Verify the OTP
        from .analytics import track_event, identify_user, get_email_domain
        identify_user(
                distinct_id=request.email,
                properties={
                    'email_domain': get_email_domain(request.email),
                    'first_seen_at': datetime.datetime.now().isoformat(),
                    'last_operation': request.operation
                }
            )

        success, message = otp_handler.verify_otp(request.email, request.otp)
        logging.info(f"OTP verification for {request.email}: {success}, message: {message}")
        if success:
            # Set a cookie to indicate the user is verified for the operation
            return JSONResponse(content={
                "status": "success",
                "message": message
            })
        else:
            return JSONResponse(content={
                "status": "error",
                "message": message
            }, status_code=400)
    except Exception as e:
        logging.error(f"Error verifying OTP: {e}")
        return JSONResponse(content={
            "status": "error",
            "message": "Failed to verify OTP"
        }, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
