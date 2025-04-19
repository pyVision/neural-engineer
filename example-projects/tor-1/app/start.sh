#!/bin/sh


mkdir -p /etc/tor
cp /app/torrc /etc/tor/torrc
chmod 644 /etc/tor/torrc

tor -f /etc/tor/torrc &
sleep 5


source /app/v1/bin/activate && pip3 install pysocks && python3 /app/app.py