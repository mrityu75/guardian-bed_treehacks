import time
from collections import deque
from typing import Dict, List, Optional
import threading
import logging

logger = logging.getLogger("TimeSeriesDB")

class TimeSeriesDB:
    """
    In-memory time-series database
    Stores all sensor data with timestamps
    Thread-safe
    """
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        
        # Separate deques for each source
        self.bed_data = deque(maxlen=max_points)
        self.hand_data = deque(maxlen=max_points)
        self.radar_data = deque(maxlen=max_points)
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Stats
        self.total_stored = 0
        
    def insert_bed(self, data: Dict):
        """Store bed module data"""
        with self.lock:
            self.bed_data.append(data)
            self.total_stored += 1
            
    def insert_hand(self, data: Dict):
        """Store hand module data"""
        with self.lock:
            self.hand_data.append(data)
            self.total_stored += 1
            
    def insert_radar(self, data: Dict):
        """Store radar data"""
        with self.lock:
            self.radar_data.append(data)
            self.total_stored += 1
            
    def get_latest_bed(self) -> Optional[Dict]:
        """Get most recent bed data"""
        with self.lock:
            return self.bed_data[-1] if self.bed_data else None
            
    def get_latest_hand(self) -> Optional[Dict]:
        """Get most recent hand data"""
        with self.lock:
            return self.hand_data[-1] if self.hand_data else None
            
    def get_latest_radar(self) -> Optional[Dict]:
        """Get most recent radar data"""
        with self.lock:
            return self.radar_data[-1] if self.radar_data else None
            
    def get_bed_history(self, seconds: float = 60) -> List[Dict]:
        """Get bed data from last N seconds"""
        cutoff = time.time() - seconds
        with self.lock:
            return [
                d for d in self.bed_data 
                if d.get('received_at', 0) > cutoff
            ]
            
    def get_hand_history(self, seconds: float = 60) -> List[Dict]:
        """Get hand data from last N seconds"""
        cutoff = time.time() - seconds
        with self.lock:
            return [
                d for d in self.hand_data 
                if d.get('received_at', 0) > cutoff
            ]
            
    def get_radar_history(self, seconds: float = 60) -> List[Dict]:
        """Get radar data from last N seconds"""
        cutoff = time.time() - seconds
        with self.lock:
            return [
                d for d in self.radar_data 
                if d.get('received_at', 0) > cutoff
            ]
            
    def get_all_latest(self) -> Dict:
        """Get latest from all sources"""
        with self.lock:
            return {
                'bed': self.bed_data[-1] if self.bed_data else None,
                'hand': self.hand_data[-1] if self.hand_data else None,
                'radar': self.radar_data[-1] if self.radar_data else None,
                'timestamp': time.time()
            }
            
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.lock:
            return {
                'total_stored': self.total_stored,
                'bed_points': len(self.bed_data),
                'hand_points': len(self.hand_data),
                'radar_points': len(self.radar_data),
                'max_points': self.max_points
            }
            
    def clear(self):
        """Clear all data"""
        with self.lock:
            self.bed_data.clear()
            self.hand_data.clear()
            self.radar_data.clear()
            logger.info("Database cleared")
