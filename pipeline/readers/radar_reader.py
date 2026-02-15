import serial
import time
import threading
from queue import Queue, Full
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RadarReader")

class RadarReader:
    """
    Reads data from mmWave Radar over Serial (USB)
    """
    
    def __init__(self, port: str, baudrate: int = 115200, poll_rate_hz: float = 10):
        self.port = port
        self.baudrate = baudrate
        self.poll_interval = 1.0 / poll_rate_hz
        
        self.ser = None
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
            
        try:
            # Open serial port
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            logger.info(f"Opened serial port {self.port}")
            
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            logger.info("Started radar reader")
            
        except Exception as e:
            logger.error(f"Failed to start: {e}")
            
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        if self.ser:
            self.ser.close()
        logger.info("Stopped")
        
    def _read_loop(self):
        while self.running:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    line = self.ser.readline()
                    data = self._parse_line(line)
                    
                    if data:
                        data['source'] = 'radar'
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
                            
            except Exception as e:
                self.error_count += 1
                if self.error_count % 10 == 0:
                    logger.error(f"Error (count={self.error_count}): {e}")
                    
            time.sleep(0.01)
            
    def _parse_line(self, line: bytes) -> Optional[Dict]:
        """Parse DFRobot mmWave radar format"""
        try:
            decoded = line.decode('utf-8').strip()
            
            # Format: $JYBSS,presence,movement,hr,rr,distance*checksum
            if decoded.startswith('$JYBSS'):
                parts = decoded.split(',')
                
                if len(parts) >= 6:
                    return {
                        'timestamp': time.time(),
                        'presence': bool(int(parts[1])),
                        'movement': int(parts[2]),
                        'heart_rate': int(parts[3]),
                        'respiration_rate': int(parts[4]),
                        'distance_cm': int(parts[5].split('*')[0])
                    }
                    
        except Exception as e:
            pass
            
        return None
        
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
