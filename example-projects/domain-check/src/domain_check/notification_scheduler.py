import os
import logging
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any

# Import initialization module to load environment variables
from .init_application import initialization_result

from .notification_handler import NotificationHandler
from .domain_check import check_domains
from .ssl_check import SSLChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='notification_scheduler.log'
)

logger = logging.getLogger(__name__)
if initialization_result["debug_mode"]:
    logger.setLevel(logging.DEBUG)

class NotificationScheduler:
    """
    Scheduler for checking domain and SSL expiry dates and sending notification emails.
    
    This class manages the process of checking registered domains for expiry dates
    and sending email notifications when domains or SSL certificates are about to expire.
    """
    
    def __init__(self):
        """
        Initialize the notification scheduler.
        
        Sets up the notification handler, SSL checker, and email configuration.
        """
        self.notification_handler = NotificationHandler()
        self.ssl_checker = SSLChecker()
        
        # Email configuration from environment variables
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("FROM_EMAIL", "domaincheck@example.com")
        
        # Log SMTP configuration (excluding password)
        logger.info(f"SMTP Server: {self.smtp_server}:{self.smtp_port}")
        logger.info(f"From Email: {self.from_email}")
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email notifications will be logged but not sent.")
        
    def check_domains_and_notify(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        """
        Check all registered domains for expiry and send notifications if needed.
        
        Args:
            days_threshold: Number of days before expiry to send notifications
            
        Returns:
            List of notification results
        """
        logging.info(f"Starting domain expiry check with threshold of {days_threshold} days")
        
        # Get all active subscriptions
        subscriptions = self.notification_handler.get_all_subscriptions()
        notification_results = []
        
        for subscription in subscriptions:
            email = subscription["email"]
            domains = subscription["domains"]
            
            # Skip if no domains registered
            if not domains:
                continue
                
            logging.info(f"Checking {len(domains)} domains for {email}")
            
            # Check domain expirations
            domain_results = check_domains(domains, days_threshold)
            
            # Check SSL certificates for each domain
            ssl_results = []
            for domain in domains:
                ssl_certificates = self.ssl_checker.check_domain_certificates(domain, days_threshold)
                ssl_results.extend(ssl_certificates)
            
            # Filter domains that are expiring soon
            expiring_domains = []
            for result in domain_results:
                if result["days_left"] < days_threshold and result["days_left"] > 0:
                    result["status"] = "Expiring Soon"
                    expiring_domains.append(result)
            
            # Filter SSL certificates that are expiring soon
            expiring_certs = []
            for result in ssl_results:
                if result.get("days_to_expire", 0) < days_threshold and result.get("days_to_expire", 0) > 0:
                    result["status"] = "Expiring Soon"
                    expiring_certs.append(result)
            
            # Send notification if more than 1 domain OR more than 1 SSL certificate is expiring
            #if len(expiring_domains) > 1 or len(expiring_certs) > 1:
            result = self._send_notification(
                    email=email,
                    expiring_domains=domain_results,
                    expiring_certs=ssl_results,
                    days_threshold=days_threshold
                )
            notification_results.append(result)
        
        logging.info(f"Completed domain expiry checks. Sent {len(notification_results)} notifications.")
        return notification_results
        
    def _send_notification(self, email: str, expiring_domains: List[Dict[str, Any]], 
                          expiring_certs: List[Dict[str, Any]], days_threshold: int) -> Dict[str, Any]:
        """
        Send email notification for expiring domains and SSL certificates.
        
        Args:
            email: Recipient email address
            expiring_domains: List of domains expiring soon
            expiring_certs: List of SSL certificates expiring soon
            days_threshold: Days threshold used for checking
            
        Returns:
            Dict with notification status
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = f"ALERT: Domains and SSL Certificates Expiring Soon"
            
            # Create the email body
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    h1, h2 {{ color: #333; }}
                    .expiry-alert {{ color: #cc0000; font-weight: bold; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .alert {{ color: #cc0000; }}
                </style>
            </head>
            <body>
                <h1>Domain and SSL Certificate Expiry Alert</h1>
                <p>This is an automated notification about your domains and SSL certificates that will expire within the next {days_threshold} days.</p>
            """
            
            # Add domain expiry information
            if expiring_domains:
                body += """
                <h2>Domains Expiring Soon</h2>
                <table>
                    <tr>
                        <th>Domain</th>
                        <th>Expiry Date</th>
                        <th>Days Left</th>
                        <th>Registrar</th>
                    </tr>
                """
                
                for domain in expiring_domains:
                    body += f"""
                    <tr>
                        <td>{domain['domain']}</td>
                        <td>{domain['expiry_date']}</td>
                        <td class="alert">{domain['days_left']}</td>
                        <td>{domain['registrar']}</td>
                    </tr>
                    """
                
                body += """
                </table>
                <p>Please renew these domains soon to avoid service interruptions.</p>
                """
            
            # Add SSL certificate expiry information
            if expiring_certs:
                body += """
                <h2>SSL Certificates Expiring Soon</h2>
                <table>
                    <tr>
                        <th>Hostname</th>
                        <th>Issuer</th>
                        <th>Expiry Date</th>
                        <th>Days Left</th>
                    </tr>
                """
                
                for cert in expiring_certs:
                    body += f"""
                    <tr>
                        <td>{cert['hostname']}</td>
                        <td>{cert.get('cert_issuer',"")}</td>
                        <td>{cert.get('not_after',"")}</td>
                        <td class="alert">{cert.get('days_to_expire',-1)}</td>
                    </tr>
                    """
                
                body += """
                </table>
                <p>Please renew these SSL certificates soon to avoid security warnings and connection problems.</p>
                """
            
            # Add footer
            body += """
                <p>To manage your notification settings, visit our Domain & SSL Expiry Checker tool.</p>
                <p>If you no longer wish to receive these notifications, you can unregister your domains.</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email if SMTP credentials are configured
            if self.smtp_username and self.smtp_password:
                try:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    text = msg.as_string()
                    server.sendmail(self.from_email, email, text)
                    server.quit()
                    
                    logging.info(f"Notification email sent to {email}")
                    sent = True
                except Exception as e:
                    logging.error(f"Failed to send email to {email}: {e}")
                    sent = False
            else:
                # Log the email instead of sending if SMTP is not configured
                logging.info(f"SMTP not configured. Would send email to {email} with {len(expiring_domains)} domains and {len(expiring_certs)} certs")
                sent = False
            
            # Return result
            return {
                "email": email,
                "sent": sent,
                "expiring_domains_count": len(expiring_domains),
                "expiring_certs_count": len(expiring_certs),
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logging.error(f"Error sending notification to {email}: {e}")
            return {
                "email": email,
                "sent": False,
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def run_scheduled_check(self) -> Dict[str, Any]:
        """
        Run a scheduled check for domain and SSL expiry.
        This method is intended to be called by a scheduler (e.g., cron job).
        
        Returns:
            Dict with check results
        """
        start_time = datetime.datetime.now()
        
        # Use the environment variable for threshold or default to 30 days
        threshold = int(os.environ.get("NOTIFICATION_THRESHOLD_DAYS", 30))
        
        # Run the check and send notifications
        results = self.check_domains_and_notify(threshold)
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Return summary
        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "threshold_days": threshold,
            "notifications_sent": len(results),
            "details": results
        }