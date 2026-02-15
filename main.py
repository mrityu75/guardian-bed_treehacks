#!/usr/bin/env python3
"""
Guardian Bed - Data Pipeline
Main entry point
"""

import time
import signal
import sys

from pipeline.pipeline import DataPipeline
from pipeline.config import Config

# Global pipeline instance
pipeline = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nShutting down...")
    if pipeline:
        pipeline.stop()
    sys.exit(0)

def main():
    global pipeline
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create config
    config = Config()
    
    # Create and start pipeline
    pipeline = DataPipeline(config)
    pipeline.start()
    
    print("\nPipeline running. Press Ctrl+C to stop.\n")
    print("Printing stats every 10 seconds...\n")
    
    # Main loop - print stats periodically
    try:
        while True:
            time.sleep(10)
            pipeline.print_stats()
            
            # Example: Access the database
            db = pipeline.get_database()
            latest = db.get_all_latest()
            
            print("\nLatest data snapshot:")
            print(f"  Bed: {latest['bed'] is not None}")
            print(f"  Hand: {latest['hand'] is not None}")
            print(f"  Radar: {latest['radar'] is not None}")
            
    except KeyboardInterrupt:
        print("\nStopping...")
        pipeline.stop()

if __name__ == "__main__":
    main()
