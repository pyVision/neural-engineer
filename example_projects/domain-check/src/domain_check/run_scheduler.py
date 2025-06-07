#!/usr/bin/env python3
"""
Domain Expiry Notification Scheduler

This script runs the domain expiry notification scheduler to check domains
and send email notifications for domains that are about to expire.

Usage:
  python run_scheduler.py [--threshold DAYS]

Options:
  --threshold DAYS   Notification threshold in days (default: from .env file or 30)
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime

# Import initialization module first to load environment variables
from .init_application import initialization_result

from .notification_scheduler import NotificationScheduler

# Configure logging based on debug mode
logger = logging.getLogger(__name__)
if initialization_result["debug_mode"]:
    logger.setLevel(logging.DEBUG)

def main():
    """Run the domain expiry notification scheduler."""
    parser = argparse.ArgumentParser(description='Run the domain expiry notification scheduler.')
    
    # Get default threshold from environment variables
    default_threshold = int(os.environ.get("NOTIFICATION_THRESHOLD_DAYS", 30))
    
    parser.add_argument('--threshold', type=int, default=default_threshold,
                        help=f'Notification threshold in days (default: {default_threshold})')
    args = parser.parse_args()
    
    # Update environment variable if different from default
    if args.threshold != default_threshold:
        os.environ["NOTIFICATION_THRESHOLD_DAYS"] = str(args.threshold)
        logger.info(f"Updated notification threshold to {args.threshold} days")
    
    logger.info(f"Starting domain expiry check with threshold of {args.threshold} days at {datetime.now().isoformat()}")
    
    # Create and run the scheduler
    scheduler = NotificationScheduler()
    results = scheduler.run_scheduled_check()
    
    # Print results summary
    print(f"Check completed at {results['end_time']}")
    print(f"Duration: {results['duration_seconds']:.2f} seconds")
    print(f"Notifications sent: {results['notifications_sent']}")
    
    # Save results to a JSON file for record-keeping
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.environ.get("RESULTS_DIR", "results")
    
    # Create results directory if it doesn't exist
    os.makedirs(results_dir, exist_ok=True)
    
    results_file = os.path.join(results_dir, f"notification_check_{timestamp}.json")
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {results_file}")
    print(f"Results saved to {results_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())