"""SSL Certificate checker module to validate SSL certificates for domains and subdomains."""

import socket
import ssl
import dns.resolver
import OpenSSL
import datetime
from typing import List, Dict, Optional
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import idna

# Configure logging for the module
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SSLChecker:
    """
    A class to check SSL certificates for a domain and its subdomains.
    Provides methods to discover subdomains, retrieve SSL certificate details,
    and check certificate validity/expiration.
    """
    def __init__(self, verify_ssl: bool = True, timeout: int = 10):
        """
        Initialize SSL Checker with configuration options.

        Args:
            verify_ssl (bool): Whether to verify SSL certificates.
            timeout (int): Connection timeout in seconds.
        """
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.context = ssl.create_default_context()
        if not verify_ssl:
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE

    def get_subdomains(self, domain: str) -> List[str]:
        """
        Find subdomains using DNS records and common subdomain prefixes.

        Args:
            domain (str): Root domain to check.

        Returns:
            List[str]: List of discovered subdomains.
        """
        subdomains = set()
        try:
            # Create a DNS resolver instance
            resolver = dns.resolver.Resolver()
            
            # Fetch all DNS records for the domain
            record_types = ['A', 'AAAA', 'CNAME']
            for record_type in record_types:
                try:
                    # Fetch A records for the domain itself
                    answers = resolver.resolve(domain, record_type)
                    print("AAA",len(answers))
                    for rdata in answers:
                        if record_type in ['A', 'AAAA']:
                            # Add the domain itself (if it resolves)
                            subdomains.add(domain)
                        elif record_type == 'CNAME':
                            cname_target = str(rdata.target).rstrip('.')
                            subdomains.add(cname_target)
                except Exception as e:
                    logging.debug(f"Error checking {record_type} records for {domain}: {e}")
                    continue

            # Try to find subdomains by brute-forcing common prefixes
            common_subdomains = [
                'www', 'mail', 'webmail', 'blog', 'shop', 
                'dev', 'api', 'admin', 'portal', 'staging'
            ]
            for subdomain in common_subdomains:
                try:
                    full_domain = f"{subdomain}.{domain}"
                    for record_type in record_types:
                        try:
                            answers = resolver.resolve(full_domain, record_type)
                            subdomains.add(full_domain)
                        except Exception:
                            continue
                except Exception:
                    continue


                    
        except Exception as e:
            logging.error(f"Error finding subdomains for {domain}: {e}")
            
        return list(subdomains)

    def get_certificate_info(self, hostname: str, port: int = 443) -> Optional[Dict]:
        """
        Get SSL certificate information for a given hostname.

        Args:
            hostname (str): Domain to check.
            port (int): SSL port (default 443).

        Returns:
            Optional[Dict]: Dictionary containing certificate information or None on error.
        """
        try:
            # Handle Internationalized Domain Names (IDN)
            # Extract the host part for IDN encoding, but keep the original hostname for SSL connection
            parsed_url = urlparse(f'https://{hostname}')
            host_for_connection = hostname
            
            # Only apply IDN encoding for valid hostnames without underscores
            if '_' not in parsed_url.netloc:
                try:
                    host_for_connection = idna.encode(parsed_url.netloc).decode('ascii')
                except Exception as e:
                    logging.warning(f"IDN encoding failed for {hostname}: {e}, using original hostname")
            
            # Create a socket connection and wrap it with SSL
            with socket.create_connection((host_for_connection, port), timeout=self.timeout) as sock:
                with self.context.wrap_socket(sock, server_hostname=host_for_connection) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Get certificate in binary form for additional details
                    cert_binary = ssock.getpeercert(binary_form=True)
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_binary)
                    
                    # Parse certificate expiration date
                    not_after = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y GMT')
                    days_to_expire = (not_after - datetime.datetime.utcnow()).days
                    
                    # Extract issuer and subject as dictionaries
                    issuer_dict = {}
                    for issuer_part in cert['issuer']:
                        for key, value in issuer_part:
                            issuer_dict[key] = value
                    
                    subject_dict = {}
                    for subject_part in cert['subject']:
                        for key, value in subject_part:
                            subject_dict[key] = value
                            
                    return {
                        'hostname': hostname,
                        'issuer': issuer_dict,
                        'subject': subject_dict,
                        'version': x509.get_version(),
                        'serial_number': format(x509.get_serial_number(), 'x'),
                        'not_before': cert['notBefore'],
                        'not_after': cert['notAfter'],
                        'days_to_expire': days_to_expire,
                        'expired': days_to_expire < 0,
                        'cert_issuer': issuer_dict.get('organizationName', 'Unknown'),
                        'cert_organization': subject_dict.get('commonName', 'Unknown'),
                    }
                    
        except (socket.gaierror, socket.timeout) as e:
            logging.error(f"Network error checking {hostname}: {e}")
            return {
            'hostname': hostname,
            'status': f"Connection error: {str(e)}",
            'error_type': 'network',
            'error_details': str(e),
            'days_to_expire': -1,
            'expired': True
            }
        except ssl.SSLError as e:
            logging.error(f"SSL error checking {hostname}: {e}")
            return {
            'hostname': hostname,
            'status': f"SSL error: {str(e)}",
            'error_type': 'ssl',
            'error_details': str(e),
            'days_to_expire': -1,
            'expired': True
            }
        except Exception as e:
            logging.error(f"Error checking certificate for {hostname}: {e}")
            import traceback
            traceback.print_exc()
            return {
            'hostname': hostname,
            'status': f"Certificate check failed: {str(e)}",
            'error_type': 'unknown',
            'error_details': str(e),
            'days_to_expire': -1,
            'expired': True
            }

    def check_domain_certificates(self, domain: str, notification_threshold_days=30) -> List[Dict]:
        """
        Check SSL certificates for a domain and all its discovered subdomains.

        Args:
            domain (str): Root domain to check.
            notification_threshold_days (int): Days before expiration to trigger warning.

        Returns:
            List[Dict]: List of dictionaries containing certificate information for each domain/subdomain.
        """
        results = []
        try:
            # Get list of subdomains to check
            domains_to_check = set(self.get_subdomains(domain))
            print(f"Domains to check: {domains_to_check}")
            domains_to_check.add(domain)  # Add root domain
            
            # Check certificates for each domain/subdomain
            for d in domains_to_check:
                print("getting the certificate info for ", d)
                r1 = self.get_certificate_info(d)
                print(r1)
                if r1:
                    days_left = r1["days_to_expire"]
                    r1["domain"] = domain
                    # Set status based on expiration threshold
                    if days_left < 0:
                        r1["status"] = "Expired"
                    elif days_left == 0:
                        r1["status"] = "Expiring today!"
                    elif days_left < notification_threshold_days:
                        r1["status"] = "Expiring soon!"
                    elif days_left > notification_threshold_days:
                        r1["status"] = "Valid SSL"
                    
                    if r1.get("error_type",None):
                        r1["status"] = f"Error: {r1['error_details']}"
                    
                    
                    #else:
                    #r1["status"] = "Valid SSL" if days_left >= notification_threshold_days else "Expiring soon!"
                    results.append(r1)
                        
        except Exception as e:
            logging.error(f"Error checking certificates for {domain}: {e}")
            
        return results
