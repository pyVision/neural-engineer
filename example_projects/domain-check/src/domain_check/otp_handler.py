from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import os
import smtplib
import redis
import logging
import secrets
import string
import datetime
from typing import Dict, Any, Optional, Tuple

from .init_application import initialization_result

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='otp_handler.log'
)

logger = logging.getLogger(__name__)
if initialization_result["debug_mode"]:
    logger.setLevel(logging.DEBUG)

class OTPHandler:
    """
    Handler for generating, storing, and verifying one-time passwords (OTPs)
    for email authentication during domain registration and viewing.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the OTP handler with Redis connection."""
        try:

            # Check if Redis is enabled in environment variables
            if not redis_client:
            # Connect to Redis based on environment variables
                # Connect to local Redis instance
                self.redis_client = redis.Redis(
                        host=initialization_result["env_vars"]["REDIS_HOST"],
                        port=initialization_result["env_vars"]["REDIS_PORT"],
                        password=initialization_result["env_vars"]["REDIS_PASSWORD"],
                        decode_responses=True,
                        pool_max_size=2
                    )
            else:
                self.redis_client = redis_client
                
            logger.info("Connected to local Redis")
                
            # Test the connection
            self.redis_client.ping()
            logger.info("Redis connection successful")
            
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Continue without Redis - will use in-memory storage
            self.redis_client = None
            
        # In-memory storage as fallback
        self.otp_store = {}
    
    def _hash_email(self, email: str) -> str:
        """
        Create a hash of the email address to use as the Redis key.
        
        Args:
            email: The email address to hash
            
        Returns:
            str: SHA-256 hash of the email
        """
        return hashlib.sha256(email.encode()).hexdigest()
    
    def check_existing_otp(self, email: str, operation: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if there's an existing valid OTP for the given email and operation.
        
        Args:
            email: Email address to check
            operation: Operation type ('register' or 'view')
            
        Returns:
            Tuple containing:
                - Exists (bool): True if a valid OTP exists
                - OTP (str or None): The existing OTP code if exists
                - Created time (str or None): ISO formatted creation timestamp
        """
        email_hash = self._hash_email(email)
        otp_key = f"otp:{email_hash}"
        
        try:
            # Get OTP data
            otp_data = None
            
            if self.redis_client:
                # Get from Redis
                redis_data = self.redis_client.hgetall(otp_key)
                
                if redis_data:
                    otp_data = {k: v for k, v in redis_data.items()}
            else:
                # Get from in-memory storage
                otp_data = self.otp_store.get(email_hash)
            
            if not otp_data:
                return False, None, None
            
            # Check if it's for the same operation and not expired
            if (
                datetime.datetime.now() < datetime.datetime.fromisoformat(otp_data.get("expiry"))):
                return True, otp_data.get("otp"), otp_data.get("created")
            
            return False, None, None
            
        except Exception as e:
            logger.error(f"Error checking existing OTP: {e}")
            return False, None, None
    
    def generate_otp(self, email: str, operation: str, force_new: bool = False) -> Tuple[str, str, bool]:
        """
        Generate a 12-digit alphanumeric OTP for the given email and operation.
        
        Args:
            email: Email address to generate OTP for
            operation: Operation type ('register' or 'view')
            force_new: If True, always generate a new OTP even if one exists
            
        Returns:
            Tuple containing:
                - OTP (str): The 12-digit alphanumeric OTP
                - Created time (str): ISO formatted creation timestamp
                - Is new (bool): True if a new OTP was generated, False if existing was returned
        """
        # Check if there's a valid existing OTP
        if not force_new:
            exists, existing_otp, created_time = self.check_existing_otp(email,operation)
            if exists:
                logger.info(f"Using existing OTP for {email} ")
                return existing_otp, created_time, False
        
        # Generate a secure 12-digit alphanumeric OTP
        alphabet = string.ascii_letters + string.digits
        otp = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        # Store the OTP with email 
        email_hash = self._hash_email(email)
        # Get expiry duration from env vars (default 30 days)
        expiry_days = int(initialization_result["env_vars"].get("OTP_EXPIRY_DAYS", 30))
        expiry_time = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
        created_time = datetime.datetime.now().isoformat()
        
        otp_data = {
            "email": email,
            "otp": otp,
        
            "created": created_time,
            "expiry": expiry_time.isoformat(),
            "verified": "false"
        }
        
        try:
            if self.redis_client:
                # Store in Redis
                otp_key = f"otp:{email_hash}"
                
                # Store as a hash in Redis
                for key, value in otp_data.items():
                    self.redis_client.hset(otp_key, key, value)
                
                # Set expiration in Redis based on the configuration
                expiry_seconds = int(initialization_result["env_vars"].get("OTP_EXPIRY_DAYS", 30)) * 24 * 60 * 60
                self.redis_client.expire(otp_key, expiry_seconds)
            else:
                # Use in-memory storage
                self.otp_store[email_hash] = otp_data
                
            logger.info(f"Generated OTP for {email} ")
            return otp, created_time, True
        except Exception as e:
            logger.error(f"Error generating OTP: {e}")
            # Return a valid OTP even if storage fails
            return otp, created_time, True
    
    def verify_otp(self, email: str, otp: str) -> Tuple[bool, str, Optional[str]]:
        """
        Verify the OTP for the given email.
        
        Args:
            email: Email address to verify OTP for
            otp: The OTP to verify
            
        Returns:
            Tuple containing:
                - Success (bool): True if verification was successful
                - Message (str): A message describing the result
        
        """
        email_hash = self._hash_email(email)
        otp_key = f"otp:{email_hash}"
        
        try:
            # Get OTP data
            otp_data = None
            
            if self.redis_client:
                # Get from Redis
                redis_data = self.redis_client.hgetall(otp_key)
                
                if redis_data:
                    # Convert bytes to string
                    otp_data = {k: v for k, v in redis_data.items()}
            else:
                # Get from in-memory storage
                otp_data = self.otp_store.get(email_hash)
            
            if not otp_data:
                return False, "No OTP found for this email address"
            
            # Check if OTP matches
            if otp_data.get("otp") != otp:
                return False, "Invalid OTP"
            
            # Check if OTP is expired
            expiry_time = datetime.datetime.fromisoformat(otp_data.get("expiry"))
            if datetime.datetime.now() > expiry_time:
                return False, "OTP has expired"
            
            # Check if already verified
            if otp_data.get("verified") == "true":
                #return False, "OTP has already been used", None
                return True, "OTP reverified successfully"
            # Mark as verified
            if self.redis_client:
                self.redis_client.hset(otp_key, "verified", "true")
            else:
                self.otp_store[email_hash]["verified"] = "true"
            
            # Return success with operation
            #operation = otp_data.get("operation")
            return True, "OTP verified successfully"
            
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"Error verifying OTP: {e}")
            return False, f"Error verifying OTP: {str(e)}"
    
    def send_otp_email(self, email: str, otp: str, operation: str, created_time: str) -> bool:
        """
        Send an email with the OTP to the user.
        
        Args:
            email: Recipient's email address
            otp: The OTP to be sent
            operation: The operation type ('register' or 'view')
            created_time: ISO formatted timestamp when the OTP was created
            
        Returns:
            bool: True if the email was sent successfully
        """
        try:
            # Email configuration from environment variables
            smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.environ.get("SMTP_PORT", 587))
            smtp_username = os.environ.get("SMTP_USERNAME", "")
            smtp_password = os.environ.get("SMTP_PASSWORD", "")
            from_email = os.environ.get("FROM_EMAIL", "domaincheck@example.com")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = email
            msg['Subject'] = "Domain Check - Your Verification Code"
            
            # Create email body with OTP
            operation_text = "registration" if operation == "register" else "viewing domain information"
            expiry_days = int(initialization_result["env_vars"].get("OTP_EXPIRY_DAYS", 30))
            created_date = datetime.datetime.fromisoformat(created_time).strftime("%Y-%m-%d %H:%M:%S")
            
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .otp-code {{ font-size: 24px; font-weight: bold; text-align: center; 
                                padding: 10px; background-color: #f0f0f0; margin: 20px 0; }}
                    .footer {{ font-size: 12px; color: #777; margin-top: 30px; }}
                    .date-info {{ font-size: 13px; color: #555; margin-bottom: 15px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Verification Required</h1>
                    <p>You recently requested to {operation_text} in the Domain Check system. To verify your email address, please use the following verification code:</p>
                    
                    <div class="otp-code">{otp}</div>
                    
                    <div class="date-info">
                        <p>Code generated on: {created_date}</p>
                        <p>This code will expire in {expiry_days} days for security reasons.</p>
                    </div>
                    
                    <p>If you didn't request this verification code, please ignore this email.</p>
                    
                    <div class="footer">
                        <p>This is an automated message from Domain Check. Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email if SMTP credentials are configured
            if smtp_username and smtp_password:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)
                text = msg.as_string()
                server.sendmail(from_email, email, text)
                server.quit()
                
                logger.info(f"OTP email sent to {email}")
                return True
            else:
                # Log the OTP instead of sending if SMTP is not configured
                logger.info(f"SMTP not configured. Would send OTP {otp} to {email} ")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {e}")
            return False
    
    def reset_otp(self, email: str) -> bool:
        """
        Reset (delete) the OTP for the given email after operation is complete.
        
        Args:
            email: Email address to reset OTP for
            
        Returns:
            bool: True if reset was successful
        """
        email_hash = self._hash_email(email)
        otp_key = f"otp:{email_hash}"
        
        try:
            if self.redis_client:
                # Delete from Redis
                self.redis_client.delete(otp_key)
            else:
                # Delete from in-memory storage
                if email_hash in self.otp_store:
                    del self.otp_store[email_hash]
            
            logger.info(f"Reset OTP for {email}")
            return True
        except Exception as e:
            logger.error(f"Error resetting OTP: {e}")
            return False
