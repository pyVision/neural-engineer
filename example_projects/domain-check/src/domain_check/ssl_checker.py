import ssl
import socket
import datetime
import logging
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

@dataclass
class CertificateInfo:
    domain: str
    expiry_date: datetime.datetime
    days_to_expiry: int
    issuer: str
    subject: str
    altnames: List[str]
    serial_number: str
    version: int

def get_certificate_info(hostname: str, port: int = 443) -> Optional[CertificateInfo]:
    """
    Fetch SSL certificate information for a given hostname.
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                
                # Extract certificate details
                not_after = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                days_to_expiry = (not_after - datetime.datetime.now()).days
                
                # Get issuer details
                issuer = dict(x[0] for x in cert['issuer'])
                issuer_str = f"{issuer.get('O', 'Unknown')}"
                
                # Get subject details
                subject = dict(x[0] for x in cert['subject'])
                subject_str = f"{subject.get('CN', 'Unknown')}"
                
                # Get alternative names
                altnames = []
                if 'subjectAltName' in cert:
                    altnames = [x[1] for x in cert['subjectAltName'] if x[0] == 'DNS']
                
                return CertificateInfo(
                    domain=hostname,
                    expiry_date=not_after,
                    days_to_expiry=days_to_expiry,
                    issuer=issuer_str,
                    subject=subject_str,
                    altnames=altnames,
                    serial_number=cert.get('serialNumber', 'Unknown'),
                    version=cert.get('version', 0)
                )
    except (socket.gaierror, socket.timeout, ssl.SSLError, ConnectionRefusedError) as e:
        logging.error(f"Error checking SSL certificate for {hostname}: {str(e)}")
        return None

def get_domain_records(domain: str) -> Set[str]:
    """
    Get all A and CNAME records for a domain including subdomains from DNS.
    """
    domains = set()
    try:
        # Get A records
        try:
            answers = dns.resolver.resolve(domain, 'A')
            domains.add(domain)
        except Exception:
            pass
        
        # Get CNAME records
        try:
            answers = dns.resolver.resolve(domain, 'CNAME')
            for rdata in answers:
                domains.add(str(rdata.target).rstrip('.'))
        except Exception:
            pass
            
        # Try to get common subdomains
        common_subdomains = ['www', 'mail', 'api', 'blog', 'app', 'dev']
        for subdomain in common_subdomains:
            full_domain = f"{subdomain}.{domain}"
            try:
                # Check both A and CNAME records for each subdomain
                try:
                    answers = dns.resolver.resolve(full_domain, 'A')
                    domains.add(full_domain)
                except Exception:
                    pass
                    
                try:
                    answers = dns.resolver.resolve(full_domain, 'CNAME')
                    for rdata in answers:
                        domains.add(str(rdata.target).rstrip('.'))
                except Exception:
                    pass
            except Exception:
                continue
                
    except Exception as e:
        logging.error(f"Error getting DNS records for {domain}: {str(e)}")
    
    return domains

def check_ssl_certificates(domain: str) -> List[CertificateInfo]:
    """
    Check SSL certificates for a domain and all its subdomains.
    Returns a list of CertificateInfo objects.
    """
    results = []
    
    # Get all domain records
    domains = get_domain_records(domain)
    logging.info(f"Found {len(domains)} domains/subdomains for {domain}")
    
    # Check certificates in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        cert_infos = list(executor.map(get_certificate_info, domains))
        
    # Filter out None results and sort by days to expiry
    cert_infos = [info for info in cert_infos if info is not None]
    cert_infos.sort(key=lambda x: x.days_to_expiry)
    
    return cert_infos