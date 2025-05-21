import os
import hashlib
import logging
import redis
import threading
from typing import List, Dict, Optional, Any, Union
from fastapi import HTTPException

# Import initialization module to load environment variables
from .init_application import initialization_result
# Import domain check and SSL checker for immediate notifications
from .domain_check import check_domains
from .ssl_check import SSLChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='notification_handler.log'
)

logger = logging.getLogger(__name__)
if initialization_result["debug_mode"]:
    logger.setLevel(logging.DEBUG)

class NotificationHandler:
    """
    A handler for managing domain notification subscriptions using GCP Memorystore for Redis.
    
    This class provides methods to register, unregister, and retrieve domains for notification
    subscriptions. It uses Redis as the backend storage, specifically designed to work with
    Google Cloud Memorystore for Redis.
    """
    
    def __init__(self,redis_client: Optional[redis.Redis] = None):
        """
        Initialize the Redis connection using environment variables.
        
        Environment Variables:
            REDIS_HOST: Redis server hostname (defaults to localhost)
            REDIS_PORT: Redis server port (defaults to 6379)
            REDIS_PASSWORD: Redis server password (optional)
        """
        try:
            # If a Redis client is provided, use it; otherwise, create a new one
            if not redis_client:
                # Get Redis connection info from environment variables
                redis_host = os.environ.get("REDIS_HOST", "localhost")
                redis_port = int(os.environ.get("REDIS_PORT", 6379))
                redis_password = os.environ.get("REDIS_PASSWORD", None)
                
                logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")
                
                # Create Redis connection
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True
                )
                logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
                # Test the connection
            else:
                self.redis_client= redis_client    
            self.redis_client.ping()
            logger.info(f"Successfully connected to Redis ")

            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Don't raise exception here, allow the application to start
            # even if Redis is not available
    
    def _hash_email(self, email: str) -> str:
        """
        Create a hash of the email address to use as the Redis key.
        
        Args:
            email: The email address to hash
            
        Returns:
            str: SHA-256 hash of the email
        """
        return hashlib.sha256(email.encode()).hexdigest()
    
    def register_domains(self, email: str, domains: List[str]) -> Dict[str, Any]:
        """
        Register domains for notification for a given email.
        
        Args:
            email: Email address for notifications
            domains: List of domain names to monitor
            
        Returns:
            Dict with registration status
        
        Raises:
            HTTPException: If Redis connection fails
        """
        try:
            # Create a hash of the email for the key
            email_hash = self._hash_email(email)
            
            # Check if the email already has domains registered
            existing_domains = self.get_domains(email)
            
            # Combine existing and new domains, removing duplicates
            all_domains = list(set(existing_domains + domains))
            
            # Store the domains in Redis with the email hash as the key
            # Format: key=email_hash, value={"domains": ["domain1", "domain2", ...], "status": "active"}
            domain_data = {
                "email": email,
                "domains": all_domains,
                "status": "active"
            }
            
            # Store as a hash in Redis
            for key, value in domain_data.items():
                if isinstance(value, list):
                    # Store lists as comma-separated strings
                    self.redis_client.hset(email_hash, key, ",".join(value))
                else:
                    self.redis_client.hset(email_hash, key, value)
            
            # Determine which domains are newly added
            new_domains = all_domains
            
            # Send immediate notification for newly registered domains in the background
            if new_domains:
                try:
                    logger.info(f"Triggering background notification check for {len(new_domains)} newly registered domains")
                    # Start a background thread to send the notification
                    notification_thread = threading.Thread(
                        target=self._send_notification_in_background,
                        args=(email, new_domains),
                        daemon=True  # Make it a daemon thread so it won't block application shutdown
                    )
                    notification_thread.start()
                    
                    return {
                        "status": "success",
                        "message": f"Registered {len(domains)} domains for {email}. Notification will be sent in background.",
                        "domains": all_domains,
                        "notification_sent_in_background": True
                    }
                except Exception as e:
                    logger.error(f"Error setting up background notification: {e}")
                    # Continue with success response even if notification setup fails
            
            return {
                "status": "success",
                "message": f"Registered {len(domains)} domains for {email}",
                "domains": all_domains
            }
        except redis.RedisError as e:
            logger.error(f"Redis error while registering domains: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to register domains: {str(e)}")
    
    def get_domains(self, email: str) -> List[str]:
        """
        Get all domains registered for a given email.
        
        Args:
            email: Email address to look up
            
        Returns:
            List of registered domains
        """
        try:
            email_hash = self._hash_email(email)
            
            # Get domain data from Redis
            domain_data = self.redis_client.hgetall(email_hash)
            
            if not domain_data:
                return []
            
            # Check if the subscription is active
            if domain_data.get("status") != "active":
                return []
            
            # Parse the comma-separated domains
            domains_str = domain_data.get("domains", "")
            domains = domains_str.split(",") if domains_str else []
            
            return domains
        except redis.RedisError as e:
            logger.error(f"Redis error while retrieving domains: {e}")
            return []
    
    def unregister_domains(self, email: str, domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Unregister domains for notification or mark the entire subscription as inactive.
        
        Args:
            email: Email address to unregister
            domains: Specific domains to unregister (if None, marks all as inactive)
            
        Returns:
            Dict with unregistration status
        """
        try:
            email_hash = self._hash_email(email)
            
            # Get current domain data
            domain_data = self.redis_client.hgetall(email_hash)
            
            if not domain_data:
                return {
                    "status": "warning",
                    "message": f"No subscriptions found for {email}"
                }
            
            # If specific domains are provided, remove only those domains
            if domains:
                current_domains = domain_data.get("domains", "").split(",")
                updated_domains = [d for d in current_domains if d not in domains]
                
                # Update Redis with the remaining domains
                self.redis_client.hset(email_hash, "domains", ",".join(updated_domains))
                
                return {
                    "status": "success",
                    "message": f"Unregistered {len(domains)} domains for {email}",
                    "remaining_domains": updated_domains
                }
            else:
                # Mark the entire subscription as inactive
                self.redis_client.hset(email_hash, "status", "inactive")
                
                return {
                    "status": "success",
                    "message": f"Marked all domain notifications as inactive for {email}"
                }
        except redis.RedisError as e:
            logger.error(f"Redis error while unregistering domains: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to unregister domains: {str(e)}")
    
    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Get all active domain subscriptions.
        
        Returns:
            List of subscription details (email, domains, status)
        """
        try:
            # Get all keys (email hashes)
            all_keys = self.redis_client.keys("*")
            subscriptions = []
            
            for key in all_keys:
                subscription_data = self.redis_client.hgetall(key)
                
                # Only include active subscriptions
                if subscription_data.get("status") == "active":
                    domains_str = subscription_data.get("domains", "")
                    subscription = {
                        "email": subscription_data.get("email", "unknown"),
                        "domains": domains_str.split(",") if domains_str else [],
                        "status": "active"
                    }
                    subscriptions.append(subscription)
            
            return subscriptions
        except redis.RedisError as e:
            logger.error(f"Redis error while retrieving all subscriptions: {e}")
            return []
    
    async def send_immediate_notification(self, email: str, domains: List[str]) -> Dict[str, Any]:
        """
        Send an immediate domain check notification for newly registered domains.
        
        Args:
            email: Email address for notifications
            domains: List of domain names to check
            
        Returns:
            Dict with notification status
        """
        try:
            logger.info(f"Sending immediate notification for {len(domains)} domains registered by {email}")
            
            # Default threshold from environment or use 30 days
            days_threshold = int(os.environ.get("NOTIFICATION_THRESHOLD_DAYS", 30))
            
            # We need to import here to avoid circular imports
            from .notification_scheduler import NotificationScheduler
            scheduler = NotificationScheduler()
            
            # Check domain expirations
            domain_results = await check_domains(domains, days_threshold)
            
            # Check SSL certificates
            ssl_checker = SSLChecker()
            ssl_results = []
            for domain in domains:
                try:
                    ssl_certificates = await ssl_checker.check_domain_certificates(domain, days_threshold)
                    ssl_results.extend(ssl_certificates)
                except Exception as e:
                    logger.error(f"Error checking SSL for {domain}: {e}")
            
            # Send notification with the results
            notification_result = scheduler._send_notification(
                email=email,
                expiring_domains=domain_results,
                expiring_certs=ssl_results,
                days_threshold=days_threshold
            )
            
            logger.info(f"Immediate notification result: {notification_result}")
            return notification_result
        except Exception as e:
            logger.error(f"Error sending immediate notification: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"Failed to send immediate notification: {str(e)}",
                "email": email
            }
    
    def _send_notification_in_background(self, email: str, domains: List[str]) -> None:
        """
        Helper method to send notifications in a background thread.
        
        Args:
            email: Email address for notifications
            domains: List of domain names to check
        """
        try:
            logger.info(f"Background thread: Sending notification for {len(domains)} domains to {email}")
            notification_result = self.send_immediate_notification(email, domains)
            logger.info(f"Background notification completed with status: {notification_result.get('status', 'unknown')}")
        except Exception as e:
            logger.error(f"Error in background notification thread: {e}")
            import traceback
            logger.error(traceback.format_exc())