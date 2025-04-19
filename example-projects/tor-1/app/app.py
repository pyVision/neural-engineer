#!/usr/bin/env python3

from stem import Signal
from stem.control import Controller
import requests
import time
import logging
from datetime import datetime
import os

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )


# Option 2: Configure logging only for your logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.propagate = False  # Don't propagate to root logger


def get_current_ip():
    try:
        response = requests.get(
            'https://api.ipify.org?format=json',
            proxies={
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            },
            timeout=10
        )
        return response.json()['ip']
    except Exception as e:
        logger.error(f"Error getting IP: {str(e)}")
        return None

def renew_tor_ip():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            logger.info("Successfully requested new Tor circuit")
    except Exception as e:
        logger.error(f"Error rotating IP: {str(e)}")

def main():
    rotation_interval = 10  # seconds
    logger.info("Starting Tor IP rotation service")
    
    while True:
        try:
            current_ip = get_current_ip()
            if current_ip:
                logger.info(f"Current IP: {current_ip}")
            
            time.sleep(rotation_interval)
            logger.info("Rotating IP...")
            renew_tor_ip()
            time.sleep(5)  # Allow time for new circuit establishment
            
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()