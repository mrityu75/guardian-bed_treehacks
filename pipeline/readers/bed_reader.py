import requests
import time
import threading
from queue import Queue, Full
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BedReader")

class BedReader:
    """
    Reads data from Bed ESP32 over HTTP
    Runs in background thread, puts data in queue
    """
    
    def __init__(self, esp32_ip: str, poll_rate_hz: float = 10):
        self.url = f"http://{esp32_ip}/data"
        self.poll_interval = 1.0 / poll_rate_hz
        
        # Thread-safe queue for data
        self.data_queue = Queue(maxsize=1000)
        
        # Control
        self.running = False
        self.thread = None
        
        # State
        self.last_data = None
        self.last_success_time = None
        self.error_count = 0
        self.total_reads = 0
        
    def start(self):
        """Start reading in background"""
        if self.running:
            logger.warning("Already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started reading from {self.url}")
        
    def stop(self):
        """Stop reading"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        logger.info("Stopped")
        
    def _read_loop(self):
        """Background thread - continuously reads"""
        while self.running:
            start_time = time.time()
            
            try:
                # Make HTTP request
                response = requests.get(self.url, timeout=2)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Add metadata
                    data['source'] = 'bed'
                    data['received_at'] = time.time()
                    data['read_number'] = self.total_reads
                    
                    # Store
                    self.last_data = data
                    self.last_success_time = time.time()
                    self.total_reads += 1
                    self.error_count = 0  # Reset on success
                    
                    # Put in queue (non-blocking)
                    try:
                        self.data_queue.put_nowait(data)
                    except Full:
                        # Queue full - remove oldest and try again
                        try:
                            self.data_queue.get_nowait()
                            self.data_queue.put_nowait(data)
                        except:
                            pass
                            
                    # Log occasionally
                    if self.total_reads % 100 == 0:
                        logger.info(f"Read #{self.total_reads} successful")
                        
                else:
                    logger.warning(f"HTTP {response.status_code}")
                    self.error_count += 1
                    
            except Exception as e:
                self.error_count += 1
                if self.error_count % 10 == 0:
                    logger.error(f"Error (count={self.error_count}): {e}")
                    
            # Sleep to maintain poll rate
            elapsed = time.time() - start_time
            sleep_time = max(0, self.poll_interval - elapsed)
            time.sleep(sleep_time)
            
    def get_queue(self) -> Queue:
        """Get the data queue for consumption"""
        return self.data_queue
        
    def get_latest(self) -> Optional[Dict]:
        """Get most recent data (or None)"""
        return self.last_data
        
    def is_connected(self) -> bool:
        """Check if getting data successfully"""
        if self.last_success_time is None:
            return False
        return (time.time() - self.last_success_time) < 5  # 5 sec timeout
        
    def get_stats(self) -> Dict:
        """Get reader statistics"""
        return {
            'total_reads': self.total_reads,
            'error_count': self.error_count,
            'connected': self.is_connected(),
            'last_success': self.last_success_time,
            'queue_size': self.data_queue.qsize()
        }
