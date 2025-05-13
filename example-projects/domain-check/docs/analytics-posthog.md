# Implementing API Analytics with PostHog in Domain Check Application

## Introduction

API analytics provide invaluable insights into how your services are being used, helping you make data-driven decisions to improve performance, user experience, and detect anomalies. In this technical blog post, we'll dive into integrating PostHog analytics with our Domain Check application, focusing specifically on tracking API usage patterns and errors.

PostHog is an open-source product analytics platform that provides event tracking, funnels, dashboards, and more. Unlike many analytics tools, PostHog can be self-hosted, giving you complete control over your data.


## Why PostHog for API Analytics?

- **Open Source**: Full access to the codebase and the option to self-host
- **Event-Based**: Perfect for tracking discrete API calls
- **Session Tracking**: Follows user journeys across multiple API endpoints
- **Error Monitoring**: Built-in capabilities for tracking failures
- **Robust Identity Management**: Easily tie events to specific users (emails in our case)
- **Real-Time Insights**: See analytics as they happen


## Setting Up PostHog in a FastAPI Application

### Installation

First, let's install the PostHog Python SDK:

```bash
poetry add posthog
```

## The Analytics Module Architecture

At the core of our implementation is a dedicated `analytics.py` file that encapsulates all PostHog functionality. This modular design ensures clean separation of concerns and makes maintenance easier.

### Structure of analytics.py

```python
"""
Analytics module for the Domain Check application.
This module contains functions for tracking events in PostHog.
"""
import os
import posthog
import logging
import datetime
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# PostHog configuration
analytics_enabled = False

def initialize_analytics(api_key=None, host=None):
    """
    Initialize PostHog analytics.
    
    Args:
        api_key (str): PostHog API key, defaults to env var POSTHOG_API_KEY
        host (str): PostHog host URL, defaults to env var POSTHOG_HOST
    
    Returns:
        bool: True if analytics was successfully initialized
    """
    global analytics_enabled
    
    # Get values from params or environment variables
    api_key = api_key or os.environ.get("POSTHOG_API_KEY", "your_api_key")
    host = host or os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
    
    # Initialize PostHog if key is available
    if api_key != "your_api_key":
        posthog.api_key = api_key
        posthog.host = host
        analytics_enabled = True
        return True
    else:
        analytics_enabled = False
        logging.warning("PostHog API key not found. Analytics tracking is disabled.")
        return False
```

### Tracking User Events

The module provides a simple interface for tracking events with the `track_event` function:

```python
def track_event(distinct_id, event_name, properties=None):
    """
    Track an event in PostHog if analytics is enabled.
    
    Args:
        distinct_id (str): Unique identifier for the user (email or 'anonymous' or 'system')
        event_name (str): Name of the event to track
        properties (dict): Properties to include with the event
    """
    if not analytics_enabled:
        return
    
    try:
        posthog.capture(
            distinct_id=distinct_id,
            event=event_name,
            properties=properties or {}
        )
    except Exception as e:
        logging.error(f"Error tracking event in PostHog: {e}")
```

### Managing User Properties

User properties help segment your analytics data. The module includes an `identify_user` function:

```python
def identify_user(distinct_id, properties=None):
    """
    Identify a user in PostHog with additional properties.
    
    Args:
        distinct_id (str): Unique identifier for the user (typically email)
        properties (dict): User properties to record
    """
    if not analytics_enabled:
        return
    
    try:
        posthog.identify(
            distinct_id=distinct_id,
            properties=properties or {}
        )
    except Exception as e:
        logging.error(f"Error identifying user in PostHog: {e}")
```

### Automated Request Tracking Middleware for FASTApi Application

A key feature is the `AnalyticsMiddleware` class that automatically tracks all API requests:

```python
class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking API requests in PostHog.
    """
    async def dispatch(self, request: Request, call_next):
        if not analytics_enabled:
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Try to get user email from request
        user_email = None
        if "email" in request.path_params:
            user_email = request.path_params["email"]
        
        # Process the request and track analytics data
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Track successful request
            track_event(
                distinct_id=user_email or 'anonymous',
                event_name='api_request',
                properties={
                    'endpoint': request.url.path,
                    'method': request.method,
                    'status_code': response.status_code,
                    'response_time': process_time,
                    'success': 200 <= response.status_code < 400
                }
            )
            
            return response
            
        except Exception as e:
            # Track error request
            process_time = time.time() - start_time
            track_event(
                distinct_id=user_email or 'anonymous',
                event_name='api_error',
                properties={
                    'endpoint': request.url.path,
                    'method': request.method,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'response_time': process_time
                }
            )
            raise e
```

## Tracking Specific API Endpoints

While the middleware handles general tracking, we'll also add specific tracking for important endpoints. Here's how we'll enhance our API endpoints with PostHog analytics:

### Domain Check API

```python
@app.post("/check-domains", response_class=HTMLResponse)
async def check_domains_form(request: Request, domains: str = Form(...), threshold: int = Form(30)):
    # Parse domains from input
    domains_list = []
    for domain in re.split(r'[,\n]', domains):
        domain = domain.strip()
        if domain:
            domains_list.append(domain)
    
    # Track domain check request
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
    results = check_domains(domains_list, threshold)
    
     expired_count = sum(1 for r in ssl_results if r.get('status') == "Expired" or r.get('status') == "Expiring today!")
    warning_count = sum(1 for r in ssl_results if r.get('status') == "Expiring soon!")
    valid_count = sum(1 for r in ssl_results if r.get('status') == "Valid SSL")
        
    
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
```

### OTP Generation and Verification

Let's add analytics to our OTP endpoints to track verification flows:

```python
@app.post("/api/otp/generate", response_model=OTPGenerationResponse)
async def generate_otp(request: OTPGenerationRequest):
    try:
        force_new = request.force_new if hasattr(request, 'force_new') else False
        
        # Generate the OTP
        otp, created_time, is_new = otp_handler.generate_otp(request.email, request.operation, force_new)
        
        # Track OTP generation in PostHog
        posthog.capture(
            distinct_id=request.email,  # Use email as distinct_id
            event='otp_generated',
            properties={
                'operation': request.operation,
                'force_new': force_new,
                'is_new_otp': is_new
            }
        )
        
        # Only send email if we generated a new OTP or specifically requested resend
        if is_new or force_new:
            # Send the OTP email
            email_sent = otp_handler.send_otp_email(request.email, otp, request.operation, created_time)
            
            # Track email delivery attempt
            posthog.capture(
                distinct_id=request.email,
                event='otp_email_sent',
                properties={
                    'success': email_sent,
                    'operation': request.operation
                }
            )
            
            if email_sent:
                # ... rest of the code
                # Track in funnel: OTP generated → Email sent
                posthog.capture(
                    distinct_id=request.email,
                    event='otp_flow_email_delivered',
                    properties={
                        'operation': request.operation
                    }
                )
                
                return JSONResponse(content={
                    # ... existing response
                })
            else:
                # Track email failure
                posthog.capture(
                    distinct_id=request.email,
                    event='otp_email_failed',
                    properties={
                        'operation': request.operation
                    }
                )
                
                return JSONResponse(content={
                    # ... existing response
                })
        else:
            # ... existing code for returning existing OTP info
    except Exception as e:
        # Track exception in PostHog
        posthog.capture(
            distinct_id=request.email,
            event='error',
            properties={
                'error_type': 'otp_generation_error',
                'error_message': str(e),
                'endpoint': '/api/otp/generate'
            }
        )
        
        logging.error(f"Error generating OTP: {e}")
        return JSONResponse(content={
            "status": "error",
            "message": "Failed to generate OTP",
            "email": request.email
        }, status_code=500)
```

## Error Tracking in Domain Registration

Error tracking is crucial for identifying issues in your API. Here's how to enhance the domain registration endpoint:

```python
@app.post("/api/notifications/register", response_model=SubscriptionResponse)
async def register_domain_notifications(request: DomainRegistrationRequest):
    """
    Register domains for notification emails.
    """
    # Start tracking this operation in PostHog
    posthog.capture(
        distinct_id=request.email,
        event='domain_registration_started',
        properties={
            'domain_count': len(request.domains),
            'domains': request.domains
        }
    )
    
    # Check if OTP was provided
    if not request.otp:
        # Track missing OTP
        posthog.capture(
            distinct_id=request.email,
            event='domain_registration_error',
            properties={
                'error_type': 'missing_otp',
                'domain_count': len(request.domains)
            }
        )
        
        return JSONResponse(content={
            "status": "error",
            "message": "Verification code required. Please provide a verification code.",
            "require_otp": True
        }, status_code=403)
    
    # Verify the OTP directly
    success, message = otp_handler.verify_otp(request.email, request.otp)
    logging.info(f"OTP verification for registration: {success}, message: {message}")

    # Track OTP verification step
    posthog.capture(
        distinct_id=request.email,
        event='otp_verification_attempted',
        properties={
            'success': success,
            'message': message,
            'operation': 'domain_registration'
        }
    )

    if not success:
        # Track failed verification
        posthog.capture(
            distinct_id=request.email,
            event='domain_registration_error',
            properties={
                'error_type': 'invalid_otp',
                'message': message
            }
        )
        
        return JSONResponse(content={
            "status": "error",
            "message": f"Verification failed: {message}",
            "require_otp": True
        }, status_code=403)
    
    try:
        # Process the registration
        result = notification_handler.register_domains(request.email, request.domains)
        
        # Track successful registration
        posthog.capture(
            distinct_id=request.email,
            event='domain_registration_completed',
            properties={
                'domain_count': len(request.domains),
                'success': result.get('status') == 'success',
                'domains': request.domains
            }
        )
        
        return JSONResponse(content=result)
    except Exception as e:
        # Track registration exception
        posthog.capture(
            distinct_id=request.email,
            event='domain_registration_error',
            properties={
                'error_type': 'registration_exception',
                'error_message': str(e),
                'domains': request.domains
            }
        )
        
        logging.error(f"Error registering domains: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Failed to register domains: {str(e)}"
        }, status_code=500)
```

## Tracking API Usage Patterns with Funnels

PostHog allows you to create funnels to track user journeys through your API. Here's a typical funnel for the domain registration process:

1. OTP Generation
2. OTP Verification
3. Domain Registration Attempt
4. Domain Registration Success/Failure

This funnel can be visualized in the PostHog dashboard to identify drop-off points in your API flow.

## Monitoring Scheduled Tasks

Let's add analytics to our scheduled domain check task:

```python
def scheduled_domain_check():
    """
    Run domain and SSL checks for all registered domains in the system.
    This function will be executed on a schedule.
    """
    start_time = time.time()
    logging.info("Running scheduled domain and SSL checks")
    
    # Track start of scheduled check
    posthog.capture(
        distinct_id='system',
        event='scheduled_check_started',
        properties={
            'timestamp': datetime.datetime.now().isoformat()
        }
    )
    
    try:
        # Use the existing method in NotificationHandler that already contains this logic
        results = scheduler.run_scheduled_check()
        
        # Track successful completion
        posthog.capture(
            distinct_id='system',
            event='scheduled_check_completed',
            properties={
                'duration_seconds': results['duration_seconds'],
                'notifications_sent': results['notifications_sent'],
                'domains_checked': results.get('domains_checked', 0),
                'success': True
            }
        )

        # ... rest of the function
        return results
    except Exception as e:
        # Track error in scheduled check
        posthog.capture(
            distinct_id='system',
            event='scheduled_check_error',
            properties={
                'error_message': str(e),
                'duration_seconds': time.time() - start_time
            }
        )
        
        logging.error(f"Error in scheduled domain check: {str(e)}")
        return {"error": str(e)}
```

## Tracking User Demographics

Using email as the distinct ID gives us the ability to track user demographics. We can enhance our analytics by identifying email domains:

```python
def get_email_domain(email):
    """Extract domain from email address"""
    try:
        return email.split('@')[1]
    except (IndexError, AttributeError):
        return "unknown"

# Then in your API endpoint:
@app.post("/api/otp/generate")
async def generate_otp(request: OTPGenerationRequest):
    # ... existing code
    
    # Add demographics to user profile
    posthog.identify(
        distinct_id=request.email,
        properties={
            'email_domain': get_email_domain(request.email),
            'first_seen_at': datetime.datetime.now().isoformat(),
            'last_operation': request.operation
        }
    )
    
    # ... rest of the function
```

## Conclusion

Implementing PostHog analytics in your Domain Check application provides deep insights into API usage patterns, error rates, and user behavior. By tracking events at key points in your API flows and using email addresses as distinct IDs, you can:

1. Identify and fix errors quickly
2. Understand how users interact with your API
3. Monitor performance metrics
4. Make data-driven decisions about new features
5. Track the effectiveness of changes over time

The examples in this blog demonstrate how to implement comprehensive analytics across your FastAPI application, from middleware that tracks all requests to specific event tracking at key points in your business logic.


## Next Steps

1. Set up custom dashboards in PostHog to visualize your API metrics
2. Create funnels to track user journeys through your API
3. Implement cohort analysis to understand different user segments
4. Use A/B testing with feature flags to optimize your API
5. Set up alerts for unusual error rates or performance issues

By following these practices, you'll have a comprehensive analytics system that provides valuable insights into your API's usage and performance.
