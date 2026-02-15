import serial
import json
import threading
import queue
import logging
import time

logger = logging.getLogger(__name__)

class HandReaderBluetooth:
    def __init__(self, bt_port, poll_rate=20):
        self.bt_port = bt_port
        self.poll_rate = poll_rate
        self.queue = queue.Queue(maxsize=1000)
        self.running = False
        self.thread = None
        self.ser = None
        self.connected = False
        self.total_reads = 0
        self.error_count = 0
        self.last_success = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started reading from {self.bt_port}")
        
    def _read_loop(self):
        while self.running:
            try:
                if self.ser is None or not self.ser.is_open:
                    try:
                        self.ser = serial.Serial(
                            self.bt_port,
                            baudrate=115200,
                            timeout=1
                        )
                        self.connected = True
                        logger.info(f"Connected to {self.bt_port}")
                    except Exception as e:
                        self.connected = False
                        self.error_count += 1
                        if self.error_count % 10 == 0:
                            logger.error(f"Failed to connect: {e}")
                        time.sleep(2)
                        continue
                
                line = self.ser.readline().decode('utf-8').strip()
                
                if line:
                    try:
                        data = json.loads(line)
                        data['source'] = 'hand'
                        data['received_at'] = time.time()
                        data['read_number'] = self.total_reads
                        
                        try:
                            self.queue.put_nowait(data)
                        except queue.Full:
                            try:
                                self.queue.get_nowait()
                                self.queue.put_nowait(data)
                            except:
                                pass
                        
                        self.total_reads += 1
                        self.last_success = time.time()
                        self.connected = True
                        
                        if self.total_reads % 100 == 0:
                            logger.info(f"Read #{self.total_reads} successful")
                    except json.JSONDecodeError:
                        pass
                        
            except serial.SerialException as e:
                self.connected = False
                self.error_count += 1
                if self.error_count % 10 == 0:
                    logger.error(f"Serial error: {e}")
                if self.ser:
                    try:
                        self.ser.close()
                    except:
                        pass
                self.ser = None
                time.sleep(1)
            except Exception as e:
                self.error_count += 1
                if self.error_count % 10 == 0:
                    logger.error(f"Error (count={self.error_count}): {e}")
                time.sleep(0.1)
    
    def get_data(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_queue(self):
        return self.queue
    
    def get_stats(self):
        return {
            'connected': self.connected,
            'total_reads': self.total_reads,
            'error_count': self.error_count,
            'queue_size': self.queue.qsize(),
            'last_success': self.last_success
        }
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.ser and self.ser.is_open:
            self.ser.close()
