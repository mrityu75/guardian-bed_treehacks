import json
import os
from datetime import datetime
import threading
from queue import Queue, Empty
import logging
import json
import os
from datetime import datetime
import threading
from queue import Queue, Empty
import logging
from typing import Dict  # ← ADD THIS LINE

logger = logging.getLogger("FileLogger")
logger = logging.getLogger("FileLogger")

class FileLogger:
    """
    Logs all data to disk files
    Runs in background thread
    Creates new file each hour
    """
    
    def __init__(self, log_dir: str = "./data_logs"):
        self.log_dir = log_dir
        
        # Create directory if doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Queue for async writing
        self.write_queue = Queue(maxsize=10000)
        
        # Control
        self.running = False
        self.thread = None
        
        # Current file
        self.current_file = None
        self.current_hour = None
        
        # Stats
        self.total_written = 0
        
    def start(self):
        """Start logging to files"""
        if self.running:
            logger.warning("Already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._write_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started file logger (dir: {self.log_dir})")
        
    def stop(self):
        """Stop logging"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        if self.current_file:
            self.current_file.close()
        logger.info("Stopped")
        
    def log(self, data: Dict):
        """
        Log data (non-blocking)
        Call this from main thread
        """
        try:
            self.write_queue.put_nowait(data)
        except:
            try:
                self.write_queue.get_nowait()
                self.write_queue.put_nowait(data)
            except:
                pass
                
    def _write_loop(self):
        """Background thread - writes to files"""
        while self.running:
            try:
                try:
                    data = self.write_queue.get(timeout=1)
                except Empty:
                    continue
                    
                # Check if we need new file (new hour)
                current_hour = datetime.now().strftime("%Y-%m-%d_%H")
                if current_hour != self.current_hour:
                    self._open_new_file(current_hour)
                    
                # Write to file
                if self.current_file:
                    json_line = json.dumps(data)
                    self.current_file.write(json_line + '\n')
                    self.current_file.flush()
                    self.total_written += 1
                    
                    if self.total_written % 1000 == 0:
                        logger.info(f"Logged {self.total_written} data points")
                        
            except Exception as e:
                logger.error(f"Write error: {e}")
                
    def _open_new_file(self, hour_str: str):
        """Open new file for this hour"""
        if self.current_file:
            self.current_file.close()
            
        filename = f"data_{hour_str}.jsonl"
        filepath = os.path.join(self.log_dir, filename)
        
        self.current_file = open(filepath, 'a')
        self.current_hour = hour_str
        
        logger.info(f"Opened new log file: {filepath}")
        
    def get_stats(self) -> Dict:
        """Get logger statistics"""
        return {
            'total_written': self.total_written,
            'queue_size': self.write_queue.qsize(),
            'current_file': self.current_hour
        }
