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

def get_email_domain(email):
    """Extract domain from email address"""
    try:
        return email.split('@')[1]
    except (IndexError, AttributeError):
        return "unknown"

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
        properties['name'] = distinct_id
        posthog.identify(
            distinct_id=distinct_id,
            properties=properties or {}
        )
    except Exception as e:
        logging.error(f"Error identifying user in PostHog: {e}")

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
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Track successful request in PostHog
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
            # Calculate processing time until error
            process_time = time.time() - start_time
            
            # Track error in PostHog
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
            
            # Re-raise the exception
            raise e
