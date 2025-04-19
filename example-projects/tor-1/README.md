# Auto-rotating IPs with Tor: A Technical Guide

## Introduction
This guide demonstrates how to implement automatic IP rotation using the Tor network, providing enhanced anonymity for your applications.

## Prerequisites
- Tor service installed
- Python 3.x
- `requests` library
- `stem` library for Tor control

## Understanding Tor Ports

When working with Tor, two essential ports are used for different purposes:

### SOCKS Port (Default: 9050)
The SOCKS port is how your applications connect to the Tor network. When you configure an application to use Tor, you point it to this port. It acts as a proxy that:
- Receives requests from your applications
- Routes these requests through the Tor network
- Returns responses while preserving anonymity
- Handles the actual data transmission through the encrypted Tor circuits

### Control Port (Default: 9051)
The Control port provides programmatic access to control and monitor the Tor process. This port allows you to:
- Request new Tor circuits (effectively changing your IP address)
- Monitor Tor's status
- Configure Tor settings during runtime
- Authenticate using passwords or cookie authentication
- Send signals like NEWNYM to request identity rotation

The distinction is important: your data travels through the SOCKS port, while control commands go through the Control port.

## Ensuring Tor Service Is Running

Before implementing IP rotation, you need to ensure that both the SOCKS and Control ports are active . This is done by addting the below lines in tor configuration file 

### TORRC File

```
ControlPort 9051
CookieAuthentication 1
# Or use password authentication instead:
# HashedControlPassword YOUR_HASHED_PASSWORD
```

### Check Tor Status

Once the tor process is up and running you can check that socks and control port are active 

```bash

# Check if SOCKS port (9050) is listening
sudo netstat -tulpn | grep 9050

# Check if Control port (9051) is listening
sudo netstat -tulpn | grep 9051
```

## Docker Implementation

The Docker implementation allows for a clean, isolated environment to run your Tor-based IP rotation setup. By containerizing the application, you can:

1. Ensure consistent behavior across different systems
2. Isolate the Tor process from your host machine
3. Easily deploy the solution to various environments
4. Maintain separation of concerns between networking and application logic

### Docker File

The following Dockerfile sets up a lightweight Alpine Linux container with all dependencies needed to run the IP rotation service:

```

    # Use Alpine Linux as base image (lightweight)
    FROM alpine:latest
        
    # Install required packages:
    # - tor: The Tor anonymity network
    # - python3: For running the control script
    # - py3-pip: Python package manager
    RUN apk add --no-cache tor python3 py3-pip

    # Install Python libraries:
    # - requests: For making HTTP requests
    # - stem: For controlling Tor via its control port
    # - pysocks: For SOCKS proxy support
    RUN pip3 install requests stem pysocks

    # Make Tor SOCKS port (9050) and Control port (9051) available
    EXPOSE 9050 9051
        
    # Set the entry point to our startup script that will
    # initialize Tor and run the Python application
    ENTRYPOINT ["/app/start.sh"]

```

## Build the docker container image

```bash
# Build the Docker image with the tag 'tor-rotator'
docker build -t tor-rotator .
```

## Run the docker container 


 ```bash
    # Run the Docker container with a specific name 'tor-rotation-container'
    docker run -it --rm \
        --name tor-rotation-container \
        -v $(pwd)/app:/app \
        -p 9050:9050 -p 9051:9051 \
        tor-rotator
```


## Implementation

Here's a Python script that rotates your IP address every few seconds using Tor:

```python
from stem import Signal  # Import Signal from the stem library for sending signals to Tor
from stem.control import Controller  # Import Controller to interface with Tor's control port
import requests  # Library for making HTTP requests
import time  # Library for adding time delays

def get_current_ip():
    """Get the current public IP address using the Tor network"""
    try:
        # Make a request to ipify API through the Tor SOCKS proxy
        response = requests.get('https://api.ipify.org?format=json',
                              proxies={'http': 'socks5h://127.0.0.1:9050',
                                     'https': 'socks5h://127.0.0.1:9050'})
        # Return the IP address from the JSON response
        return response.json()['ip']
    except Exception as e:
        # Return error message if request fails
        return f"Error: {str(e)}"

def renew_tor_ip():
    """Request a new Tor circuit, effectively changing the IP address"""
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()  # Authenticate to the Tor control port
        controller.signal(Signal.NEWNYM)  # Send NEWNYM signal to request new Tor circuit

def main():
    """Main function to continuously rotate IP addresses"""
    while True:
        # Display current IP address
        print(f"Current IP: {get_current_ip()}")
        time.sleep(10)  # Wait 10 seconds before rotating
        print("Rotating IP...")
        renew_tor_ip()  # Request a new Tor circuit
        time.sleep(5)   # Wait 5 seconds for the new circuit to be established

# Call the main function when the script is executed
if __name__ == "__main__":
    main()
```


## Security Considerations and Best Practices 

- **Always use SOCKS5 proxy configuration**: SOCKS5 provides proper DNS resolution through the Tor network, preventing DNS leaks that could expose your actual IP address and compromise anonymity.

- **Implement proper error handling**: Network issues are common when using Tor due to its nature. Robust error handling ensures your application can gracefully recover from connection failures, timeouts, or circuit build failures.

- **Be aware of Tor exit node limitations**: Some Tor exit nodes are blocked by services, others may have limited bandwidth, and a few might be monitored. This can affect the reliability and security of your connection depending on which exit node you're assigned.


## Limitations of Tor IP Rotation

- **Rate Limiting**: Requesting new circuits too frequently (faster than every 10 seconds) may be throttled by Tor . Consider implementing rate limiting to avoid overloading the Tor network
- **Exit Node Pool Size**: The total number of distinct IPs available is limited by the number of exit nodes in the Tor network (approximately 900-1000 exit nodes)
- **Performance Impact**: Each rotation requires building a new circuit, which introduces latency (5-10 seconds) . Allow sufficient time between rotations (30-60 seconds recommended)
- **Exit Node Blocking**: Many websites and services actively block or require CAPTCHAs from Tor exit nodes
- **Circuit Reuse**: Requesting a new identity doesn't guarantee a completely different path through the network, as some relay selections may overlap

## Alternatives to Tor for IP Rotation

In the future article we will explore the various alternative methods to Tor to rotate IPs automatically while maintaining anonymity . While Tor provides a reliable method for IP rotation, several alternatives may offer better performance, reliability, or specific features:

Some of alternatives include 

### 1. Commercial Proxy Services
- **Rotating Proxy APIs**: Services like Bright Data, Oxylabs, or SmartProxy provide REST APIs for rotating IPs
- **Advantages**: Higher reliability, faster connection speeds, lower block rates, geographic targeting options
- **Use Case**: High-volume web scraping or applications requiring predictable performance

### 2. VPN Services with API Control
- **Programmable VPNs**: NordVPN, ExpressVPN, and others offer APIs for programmatic server switching
- **Advantages**: Better speeds than Tor, wider acceptance by websites, fewer CAPTCHAs
- **Use Case**: Applications needing consistent bandwidth with moderate IP rotation frequency

### 3. Residential Proxy Networks
- **P2P-based proxy networks**: Services like Bright Data (Luminati), Smartproxy, NetNut, or GeoSurf offering access to residential IPs
- **Advantages**: IPs appear as regular consumers rather than datacenter addresses, lower detection rates
- **Use Case**: Applications requiring high anonymity without Tor's stigma

### 4. Mobile Proxy Networks
- **4G/5G proxy solutions**: Services like Rayobyte (PacketStream), IPRoyal, or Shifter.io that rotate through mobile network IPs
- **Advantages**: Residential-quality IPs with built-in rotation (changing cell towers)
- **Use Case**: Applications mimicking mobile user behavior

Each alternative presents different trade-offs between cost, ease of implementation, performance, and detection risk compared to Tor's free but sometimes limited approach.


## Conclusion
This implementation provides a robust way to rotate IPs automatically while maintaining anonymity through the Tor network.

Note: Use this responsibly and in compliance with applicable laws and service terms.

## Source Code
The complete source code for this project is available at:
- GitHub Repository: [github.com/pyVision/neural-engineer/tor-ip-rotation](https://github.com/pyVision/neural-engineer/tree/main/example-projects/tor-1
- Implementation Files: 
    - `/app/app.py` - Main Python script for IP rotation
    - `/app/start.sh` - Container startup script
    - `Dockerfile` - Container definition
    - `docker-compose.yml` - Deployment configuration

## Cin