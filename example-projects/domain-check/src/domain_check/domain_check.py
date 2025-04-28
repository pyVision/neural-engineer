try:
    import whois 
    from whois import whois as whois2
    from whois.parser import WhoisEntry
except ImportError:
    print("Please install the python-whois package: pip install python-whois")
    raise

import ssl
import re
import socket
import datetime
import smtplib
import os
import logging
from email.mime.text import MIMEText
from typing import List
from dataclasses import dataclass
from typing import Any, Optional, Pattern,Dict

# Configure logging with log rotation
import logging.handlers

# Set up rotating file handler
log_file = 'domain_check.log'
max_bytes = 10 * 1024 * 1024  # 10 MB
backup_count = 1  # Number of backup files to keep

handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=max_bytes, backupCount=backup_count
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[handler, logging.StreamHandler()]  # Log to both file and console
)

# thanks to https://www.regextester.com/104038
IPV4_OR_V6: Pattern[str] = re.compile(
            r"((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\s*$)|(^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$))"  # noqa: E501
)

suffixes: Optional[set] = None



def is_valid_domain(domain: str) -> bool:
    """
    Check if a domain is valid by:
    1. Validating its format
    2. Checking if it has valid DNS records (A, AAAA, MX, or NS)
    
    Returns True if domain is valid, False otherwise
    """
    # Remove protocol and path if present
    domain = re.sub(r'^.*://', '', domain)
    domain = domain.split('/')[0].lower()
    
    # Check domain format using regex
    domain_pattern = re.compile(
        r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
    )
    
    # # Handle IP addresses separately
    # if IPV4_OR_V6.match(domain):
    #     try:
    #         socket.inet_aton(domain)  # For IPv4
    #         return True
    #     except:
    #         try:
    #             socket.inet_pton(socket.AF_INET6, domain)  # For IPv6
    #             return True
    #         except:
    #             return False
    
    # If not IP, check domain format
    if not domain_pattern.match(domain):
        logging.error(f"Invalid domain format: {domain}")
        return False
    
    # Try to resolve domain using DNS records
    try:
        # Check for A record
        try:
            socket.gethostbyname(domain)
            return True
        except socket.gaierror:
            pass

        # Check for various DNS record types
        import dns.resolver
        resolver = dns.resolver.Resolver()
        
        # Try different record types
        for record_type in ['A', 'AAAA', 'MX', 'NS']:
            try:
                answers = resolver.resolve(domain, record_type)
                if answers:
                    logging.info(f"Domain {domain} has valid {record_type} records")
                    return True
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
                continue
            except Exception as e:
                logging.debug(f"Error checking {record_type} records for {domain}: {e}")
                continue
        
        logging.error(f"No valid DNS records found for domain: {domain}")
        return False
        
    except Exception as e:
        logging.error(f"Error validating domain {domain}: {e}")
        return False
    
def check_domain_expiry(domain: str) -> datetime.datetime:
    try:



        def extract_domain(url: str) -> str:
            """Extract the domain from the given URL

            >>> logger.info(extract_domain('http://www.google.com.au/tos.html'))
            google.com.au
            >>> logger.info(extract_domain('abc.def.com'))
            def.com
            >>> logger.info(extract_domain(u'www.公司.hk'))
            公司.hk
            >>> logger.info(extract_domain('chambagri.fr'))
            chambagri.fr
            >>> logger.info(extract_domain('www.webscraping.com'))
            webscraping.com
            >>> logger.info(extract_domain('198.252.206.140'))
            stackoverflow.com
            >>> logger.info(extract_domain('102.112.2O7.net'))
            2o7.net
            >>> logger.info(extract_domain('globoesporte.globo.com'))
            globo.com
            >>> logger.info(extract_domain('1-0-1-1-1-0-1-1-1-1-1-1-1-.0-0-0-0-0-0-0-0-0-0-0-0-0-10-0-0-0-0-0-0-0-0-0-0-0-0-0.info'))
            0-0-0-0-0-0-0-0-0-0-0-0-0-10-0-0-0-0-0-0-0-0-0-0-0-0-0.info
            >>> logger.info(extract_domain('2607:f8b0:4006:802::200e'))
            1e100.net
            >>> logger.info(extract_domain('172.217.3.110'))
            1e100.net
            """
            if IPV4_OR_V6.match(url):
                # this is an IP address
                return socket.gethostbyaddr(url)[0]

            # load known TLD suffixes
            global suffixes
            if not suffixes:
                # downloaded from https://publicsuffix.org/list/public_suffix_list.dat
                tlds_path = os.path.join(
                    os.getcwd(), os.path.dirname(__file__), "data", "public_suffix_list.dat"
                )
                print(f"Loading TLDs from {tlds_path}")
                with open(tlds_path, encoding="utf-8") as tlds_fp:
                    suffixes = set(
                        line.encode("utf-8")
                        for line in tlds_fp.read().splitlines()
                        if line and not line.startswith("//")
                    )

            if not isinstance(url, str):
                url = url.decode("utf-8")
            url = re.sub("^.*://", "", url)
            url = url.split("/")[0].lower()

            # find the longest suffix match
            domain = b""
            split_url = url.split(".")
            for section in reversed(split_url):
                if domain:
                    domain = b"." + domain
                domain = section.encode("utf-8") + domain
                if domain not in suffixes:
                    if b"." not in domain and len(split_url) >= 2:
                        # If this is the first section and there wasn't a match, try to
                        # match the first two sections - if that works, keep going
                        # See https://github.com/richardpenman/whois/issues/50
                        second_order_tld = ".".join([split_url[-2], split_url[-1]])
                        if not second_order_tld.encode("utf-8") in suffixes:
                            break
                    else:
                        break
            return domain.decode("utf-8")


        flags:int =0 
        url=domain
        quiet=False
        ip_match = IPV4_OR_V6.match(url)
        inc_raw = False 

        if ip_match:
            domain = url
            try:
                result = socket.gethostbyaddr(url)
            except socket.herror:
                pass
            else:
                domain = extract_domain(result[0])
        else:
            domain = extract_domain(url)


        domain = domain.encode("idna").decode("utf-8")


        # Try python-whois package
        nic_client = whois.NICClient()

        text = nic_client.whois_lookup(None, domain, flags, quiet=quiet)

        #print(text)
        w = WhoisEntry.load(domain, text)

        #print("AAA",w.expiration_date)
        if w.expiration_date is None:
            from whois.parser import WhoisCom,WhoisZa
            class WhoisEntry_new(WhoisEntry):

                @staticmethod
                def load(domain,text):
                    #print("processing who is com ",domain,text)
                    return WhoisZa(domain, text)
                
            
            w1=WhoisEntry_new.load(domain, text)
            #print("processing1",w1.expiration_date)
            w.expiration_date=w1.expiration_date
        
 

        return w
    except Exception as e:
        import traceback

        traceback.print_exc()
        logging.error(f"Error checking domain expiry for {domain}: {e}")
        raise


# def send_notification(domain_info: DomainInfo, email_to: str):
#     try:
#         msg = MIMEText(f"""
#         Domain Expiry Alert:
        
#         Domain: {domain_info.domain}
#         Domain Expiry: {domain_info.domain_expiry}
#         SSL Expiry: {domain_info.ssl_expiry}
        
#         Please take necessary action if expiration is approaching.
#         """)
        
#         msg['Subject'] = f'Domain/SSL Expiry Alert - {domain_info.domain}'
#         msg['From'] = os.environ.get('SMTP_USER')
#         msg['To'] = email_to
        
#         smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
#         smtp_port = int(os.environ.get('SMTP_PORT', '587'))
#         smtp_user = os.environ.get('SMTP_USER')
#         smtp_password = os.environ.get('SMTP_PASSWORD')

#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             server.starttls()
#             server.login(smtp_user, smtp_password)
#             server.send_message(msg)
#             logging.info(f"Notification sent successfully for {domain_info.domain}")
#     except Exception as e:
#         logging.error(f"Error sending notification for {domain_info.domain}: {e}")
#         raise

def check_domains(domains_list: List[str], notification_threshold_days: int = 30) -> List[Dict]:
    results = []
    for domain in domains_list:
        try:
            logging.info(f"Checking domain: {domain}")
            # Validate domain
            if not is_valid_domain(domain):
                logging.error(f"Invalid domain: {domain}")
                results.append({
                    "domain": domain,
                    "expiry_date": "N/A",
                    "days_left": -1,
                    "registrar": "N/A",
                    "owner": "N/A",
                    "status": "Invalid domain"
                })
                continue
            w = check_domain_expiry(domain)
            
            # Process expiry date
            domain_expiry = datetime.datetime.now()
            if isinstance(w.expiration_date, list):
                domain_expiry = min(w.expiration_date)
            else:
                domain_expiry = w.expiration_date
            
            # Calculate days until expiry
            now = datetime.datetime.now()
            domain_days = (domain_expiry - now).days
            
            # Get registrar and owner info
            registrar = getattr(w, 'registrar', 'Not available')
            owner = getattr(w, 'name', getattr(w, 'registrant', getattr(w, 'org', 'Not available')))
            
            # Add to results
            results.append({
                "domain": domain,
                "expiry_date": domain_expiry.strftime("%Y-%m-%d"),
                "days_left": domain_days,
                "registrar": registrar,
                "owner": owner,
                "status": "Valid domain"
            })
        except Exception as e:
            logging.error(f"Error processing {domain}: {e}")
            results.append({
                "domain": domain,
                "expiry_date": "Error",
                "days_left": 0,
                "registrar": "Error",
                "owner": "Error",
                "status": "Error"
            })
            pass
    return results

def check_ssl_certificates(domains_list: List[str], notification_threshold_days: int = 30) -> List[Dict]:
    """
    Check SSL certificate details for a list of domains
    Returns a list of dictionaries with SSL certificate information
    """
    results = []
    for domain in domains_list:
        try:
            logging.info(f"Checking SSL certificate for: {domain}")
            
            # Validate domain
            if not is_valid_domain(domain):
                logging.error(f"Invalid domain: {domain}")
                results.append({
                    "domain": domain,
                    "issued_to": "N/A",
                    "issued_by": "N/A",
                    "expiry_date": "N/A",
                    "days_left": -1,
                    "status": "Invalid domain"
                })
                continue
                
            # Remove protocol and path if present
            clean_domain = re.sub(r'^.*://', '', domain)
            clean_domain = clean_domain.split('/')[0].lower()
            
            # Connect to the domain on port 443 (HTTPS)
            context = ssl.create_default_context()
            with socket.create_connection((clean_domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=clean_domain) as ssock:
                    cert = ssock.getpeercert()
            
            # Extract certificate details
            issued_to = dict(x[0] for x in cert['subject']).get('commonName', 'N/A')
            issued_by = dict(x[0] for x in cert['issuer']).get('commonName', 'N/A')
            
            # Parse expiry date
            expiry_date = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
            
            # Calculate days until expiry
            now = datetime.datetime.now()
            days_left = (expiry_date - now).days
            
            # Add to results
            results.append({
                "domain": domain,
                "issued_to": issued_to,
                "issued_by": issued_by,
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "days_left": days_left,
                "status": "Valid SSL" if days_left >= notification_threshold_days else "Expiring soon!"
            })
        except Exception as e:
            logging.error(f"Error checking SSL for {domain}: {e}")
            results.append({
                "domain": domain,
                "issued_to": "Error",
                "issued_by": "Error",
                "expiry_date": "Error",
                "days_left": 0,
                "status": "Error"
            })
    
    return results

