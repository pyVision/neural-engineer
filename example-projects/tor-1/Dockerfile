FROM alpine:latest
    

RUN mkdir -p /app
# Install Tor and Python
RUN apk add --no-cache tor python3 py3-pip
RUN python3 -m venv /app/v1 && source /app/v1/bin/activate && pip3 install requests stem pysocks
    
# Configure Tor
RUN mkdir -p /etc/tor

# Expose Tor ports
EXPOSE 9050 9051

ENTRYPOINT ["/app/start.sh"]