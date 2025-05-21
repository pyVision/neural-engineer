try:
    import whois 
    from whois import whois as whois2
    from whois.parser import WhoisEntry
    import tldextract
    from .enhanced_cached import enhanced_cached,custom_key_builder
    from .enhanced_cached import Cache,RedisCache
    from .enhanced_cached import JsonSerializer
    from .init_application import initialization_result
    from dateutil import parser
    import asyncio
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

# Set up rotating file handler for logging
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

# Regex pattern to match IPv4 or IPv6 addresses
# thanks to https://www.regextester.com/104038
IPV4_OR_V6: Pattern[str] = re.compile(
            r"((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\s*$)|(^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$))"  # noqa: E501
)

suffixes: Optional[set] = None

def is_valid_domain(domain: str) -> bool:
    """
    Check if a domain is valid by:
    1. Validating its format using regex
    2. Checking if it has valid DNS records (A, AAAA, MX, or NS)
    
    Returns True if domain is valid, False otherwise.
    """
    # Remove protocol and path if present
    domain = re.sub(r'^.*://', '', domain)
    domain = domain.split('/')[0].lower()
    
    # Check domain format using regex
    domain_pattern = re.compile(
        r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
    )
    
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

        # Check for various DNS record types using dnspython
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


@enhanced_cached(    
    ttl=86400,  # 24 hours (60*60*24)
    cache=Cache.REDIS,
    track_stats=True,
    key_builder=custom_key_builder,
    serializer=JsonSerializer(),
    namespace=initialization_result["env_vars"]["REDIS_NAMESPACE"],
    endpoint=initialization_result["env_vars"]["REDIS_HOST"],
    port=initialization_result["env_vars"]["REDIS_PORT"],
    password=initialization_result["env_vars"]["REDIS_PASSWORD"],
    db=initialization_result["env_vars"]["REDIS_DB"],
    pool_max_size=2                 
                 )
async def check_domain_expiry(domain: str) -> WhoisEntry:
    """
    Check the expiry date and other WHOIS information for a given domain.
    Returns a WhoisEntry object containing parsed WHOIS data.
    """
    try:
        def extract_domain(url: str) -> str:
            """
            Extract the registrable domain from the given URL or IP address.

            Handles various cases including:
            - URLs with protocol and path
            - Internationalized domains
            - IP addresses (returns PTR record's domain)
            - Handles public suffixes using a suffix list

            Returns the registrable domain as a string.
            """
            if IPV4_OR_V6.match(url):
                # This is an IP address, get PTR record
                return socket.gethostbyaddr(url)[0]

            # Load known TLD suffixes if not already loaded
            global suffixes
            if not suffixes:
                # Downloaded from https://publicsuffix.org/list/public_suffix_list.dat
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

            # Find the longest suffix match
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

        # WHOIS lookup flags and options
        flags:int =0 
        url=domain
        quiet=False
        ip_match = IPV4_OR_V6.match(url)
        inc_raw = False 

        # If input is an IP, get its PTR record's domain
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

        # Convert to IDNA (punycode) for internationalized domains
        domain = domain.encode("idna").decode("utf-8")

        # Try python-whois package for WHOIS lookup
        nic_client = whois.NICClient()
        text = nic_client.whois_lookup(None, domain, flags, quiet=quiet)



        from typing import Any, Callable, Optional, Union
        from datetime import datetime

        class WhoisEntry_new1(WhoisEntry):
                """
                Extension of WhoisEntry class that provides custom preprocessing for WHOIS data.
                This class overrides the _preprocess method from the parent class to handle
                date formatting in a specific way.
                """
                """
                    Preprocess WHOIS data values before storing.
                    This method overrides the parent class's _preprocess method to provide
                    custom formatting for date values. It specifically handles datetime objects
                    by converting them to string format.
                    Args:
                        attr (str): The attribute name being processed
                        value (str): The value to process
                    Returns:
                        Union[str, datetime]: The processed value, formatted if it's a date
                    Overrides:
                        WhoisEntry._preprocess
                """
                
                
                def _preprocess(self, attr: str, value: str) -> Union[str, datetime]:
                    value = value.strip()
                    print("preprocess",attr,value)
                    if value and isinstance(value, str) and not value.isdigit() and "_date" in attr:
                        # try casting to date format
                        formatted_value = value
                        # if data_preprocessor is set, use it to preprocess the data string
                        if isinstance(value, datetime):
                            formatted_value=value.strftime("%Y-%m-%d %H:%M:%S")
                            print("formatted_dates2",formatted_value, attr)
                            setattr(w, date_attr, formatted_value)

                        return formatted_value
                    
                    return value
                
        w = WhoisEntry.load(domain, text)

        # Some TLDs may need special parsing
        if w.expiration_date is None:
            from whois.parser import WhoisCom,WhoisZa
            class WhoisEntry_new(WhoisEntry):
                    @staticmethod
                    def load(domain, text):
                        #print("AAAAA calling load",text)
                        return WhoisZa(domain, text)
                    
                    
                    # def _preprocess(self, attr: str, value: str) -> Union[str, datetime]:
                    #     value = value.strip()
                    #     print("preprocess",attr,value)
                    #     if value and isinstance(value, str) and not value.isdigit() and "_date" in attr:
                    #         # try casting to date format
                    #         formatted_value = value
                    #         # if data_preprocessor is set, use it to preprocess the data string
                    #         if isinstance(value, datetime):
                    #             formatted_value=value.strftime("%Y-%m-%d %H:%M:%S")
                    #             print("formatted_dates1",formatted_value, attr)
                    #             setattr(w, date_attr, formatted_value)

                    #         return formatted_value
                        
                    #     return value
                    
            w1=WhoisEntry_new.load(domain, text)
            setattr(w, 'expiration_date', w1.expiration_date)
            setattr(w, 'updated_date', w1.updated_date)
            setattr(w, 'creation_date', w1.creation_date)
            
            w.expiration_date = w1.expiration_date
            
            # Format date attributes if they exist and are datetime objects
        for date_attr in ['expiration_date', 'updated_date', 'creation_date']:
                if hasattr(w, date_attr) and getattr(w, date_attr):
                    date_value = getattr(w, date_attr)
                    if isinstance(date_value, datetime):
                        print("formatted_dates", date_value.strftime("%Y-%m-%d %H:%M:%S"), date_attr)
                        setattr(w, date_attr, date_value.strftime("%Y-%m-%d %H:%M:%S"))
        #print("AAAAA",w)

        import json
        def handler(e):
            if isinstance(e, datetime):
                return "AA",e
            return str(e)

        rstr=json.dumps(w, indent=2, default=handler, ensure_ascii=False)
    
        return rstr
    except Exception as e:
        import traceback


        traceback.print_exc()
        logging.error(f"Error checking domain expiry for {domain}: {e}")
        raise

async def check_domains(domains_list: List[str], notification_threshold_days: int = 30) -> List[Dict]:
    """
    Check a list of domains for validity and expiry information.

    Args:
        domains_list: List of domain names to check.
        notification_threshold_days: Days before expiry to consider as "expiring soon".

    Returns:
        List of dictionaries with domain, expiry date, days left, registrar, owner, and status.
    """
    results = []
    rdict={}
    for domain in domains_list:
        try:
            logging.info(f"Checking domain: {domain}")
            
            # Use tldextract to properly handle domain extraction
            ext = tldextract.extract(domain)
            # Get the registered domain (domain name + TLD)
            main_domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else domain
            logging.info(f"Extracted main domain: {main_domain}")
            domain = main_domain
            # if len(domain_parts) > 2:
            #     # Handle potential subdomains by extracting the main domain
            #     # This is a simplistic approach; for more accurate parsing, consider using tldextract
            #     # Get the last two parts (example.com from subdomain.example.com)
            #     main_domain = '.'.join(domain_parts[-2:])
            #     logging.info(f"Detected subdomain. Using main domain: {main_domain}")
            #     domain = main_domain
            # Validate domain
            if not is_valid_domain(domain):
                logging.error(f"Invalid domain: {domain}")
                if domain not in rdict:
                    edict={
                        "domain": domain,
                        "expiry_date": "N/A",
                        "days_left": -1,
                        "registrar": "N/A",
                        "owner": "N/A",
                        "status": "Invalid domain"
                    }
                    rdict[domain]=edict
                    results.append(edict)
                continue

            if domain not in rdict:

                wstr = await check_domain_expiry(domain)
                import json
                w=json.loads(wstr)
                print("JSON",w)
                #print("FFFF",w)
                # Process expiry date
                domain_expiry = datetime.datetime.now()
                if isinstance(w.get("expiration_date"), list):
                    domain_expiry = min(w["expiration_date"])
                elif isinstance(w.get("expiration_date"), str):
                    try:
                        #print("string",w["expiration_date"])
                        # Attempt to parse the string into a datetime object
                        domain_expiry = datetime.datetime.strptime(w.get("expiration_date"), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # If standard ISO format fails, try a more flexible parsing approach
                        domain_expiry = parser.parse(w.get("expiration_date"))
                else:
                    print("------ ekse -----")
                    domain_expiry = w.get("expiration_date", datetime.datetime.now())
                
                # Calculate days until expiry
                now = datetime.datetime.now()
                domain_days = (domain_expiry - now).days
                
                # Get registrar and owner info
                registrar = w.get('registrar', 'Not available')
                owner = w.get('name', w.get('registrant', w.get('org', 'Not available')))
                
                if domain_days < 0:
                    status = "Expired"
                elif domain_days == 0:
                    status = "Expiring today!"
                elif domain_days < notification_threshold_days:
                    status = "Expiring soon!"
                elif domain_days > notification_threshold_days:
                    status = "Valid domain"

                edict={
                    "domain": domain,
                    "expiry_date": domain_expiry.strftime("%Y-%m-%d"),
                    "days_left": domain_days,
                    "registrar": registrar,
                    "owner": owner,
                    "status": status
                }
                rdict[domain]=edict
                # Add to results
                results.append(edict)

        except Exception as e:
            import traceback
            traceback.print_exc()
            logging.error(f"Error processing {domain}: {e}")
            edict={
                "domain": domain,
                "expiry_date": "Error",
                "days_left": 0,
                "registrar": "Error",
                "owner": "Error",
                "status": "Error"
            }
            rdict[domain]=edict
            results.append(edict)
            pass
    return results


