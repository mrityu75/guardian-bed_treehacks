import requests
import time
import threading
from queue import Queue, Full
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HandReader")

class HandReader:
    """
    Reads data from Hand ESP32 over HTTP
    Same pattern as BedReader
    """
    
    def __init__(self, esp32_ip: str, poll_rate_hz: float = 20):
        self.url = f"http://{esp32_ip}/data"
        self.poll_interval = 1.0 / poll_rate_hz
        
        self.data_queue = Queue(maxsize=1000)
        
        self.running = False
        self.thread = None
        
        self.last_data = None
        self.last_success_time = None
        self.error_count = 0
        self.total_reads = 0
        
    def start(self):
        if self.running:
            logger.warning("Already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started reading from {self.url}")
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        logger.info("Stopped")
        
    def _read_loop(self):
        while self.running:
            start_time = time.time()
            
            try:
                response = requests.get(self.url, timeout=2)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    data['source'] = 'hand'
                    data['received_at'] = time.time()
                    data['read_number'] = self.total_reads
                    
                    self.last_data = data
                    self.last_success_time = time.time()
                    self.total_reads += 1
                    self.error_count = 0
                    
                    try:
                        self.data_queue.put_nowait(data)
                    except Full:
                        try:
                            self.data_queue.get_nowait()
                            self.data_queue.put_nowait(data)
                        except:
                            pass
                            
                    if self.total_reads % 100 == 0:
                        logger.info(f"Read #{self.total_reads} successful")
                        
                else:
                    logger.warning(f"HTTP {response.status_code}")
                    self.error_count += 1
                    
            except Exception as e:
                self.error_count += 1
                if self.error_count % 10 == 0:
                    logger.error(f"Error (count={self.error_count}): {e}")
                    
            elapsed = time.time() - start_time
            sleep_time = max(0, self.poll_interval - elapsed)
            time.sleep(sleep_time)
            
    def get_queue(self) -> Queue:
        return self.data_queue
        
    def get_latest(self) -> Optional[Dict]:
        return self.last_data
        
    def is_connected(self) -> bool:
        if self.last_success_time is None:
            return False
        return (time.time() - self.last_success_time) < 5
        
    def get_stats(self) -> Dict:
        return {
            'total_reads': self.total_reads,
            'error_count': self.error_count,
            'connected': self.is_connected(),
            'last_success': self.last_success_time,
            'queue_size': self.data_queue.qsize()
        }
