import time
import threading
import logging
from typing import Dict

from .readers.bed_reader import BedReader
from pipeline.readers.hand_reader import HandReader
from .readers.radar_reader import RadarReader
from .storage.time_series_db import TimeSeriesDB
from .storage.file_logger import FileLogger
from .config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Pipeline")

class DataPipeline:
    """
    Main data pipeline coordinator
    
    Orchestrates:
    - All readers (bed, hand, radar)
    - Storage (time-series DB + file logging)
    - Data flow from readers → storage
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Create readers
        self.bed_reader = BedReader(config.BED_ESP32_IP, config.BED_POLL_RATE_HZ)
        self.hand_reader = HandReader(config.HAND_ESP32_IP, config.HAND_POLL_RATE_HZ)
        self.radar_reader = RadarReader(
            config.RADAR_PORT,
            config.RADAR_BAUDRATE,
            config.RADAR_POLL_RATE_HZ
        )
        
        # Create storage
        self.db = TimeSeriesDB(max_points=config.MAX_MEMORY_POINTS)
        
        if config.SAVE_TO_FILE:
            self.file_logger = FileLogger(log_dir=config.FILE_LOG_DIR)
        else:
            self.file_logger = None
            
        # Control
        self.running = False
        self.processor_thread = None
        
    def start(self):
        """Start the entire pipeline"""
        if self.running:
            logger.warning("Pipeline already running")
            return
            
        logger.info("=" * 60)
        logger.info("STARTING DATA PIPELINE")
        logger.info("=" * 60)
        
        # Start readers
        logger.info("Starting readers...")
        self.bed_reader.start()
        self.hand_reader.start()
        self.radar_reader.start()
        
        # Start file logger
        if self.file_logger:
            self.file_logger.start()
            
        # Start processor
        self.running = True
        self.processor_thread = threading.Thread(
            target=self._process_loop,
            daemon=True
        )
        self.processor_thread.start()
        
        logger.info("Pipeline started successfully")
        logger.info("=" * 60)
        
    def stop(self):
        """Stop the entire pipeline"""
        logger.info("Stopping pipeline...")
        
        self.running = False
        
        # Stop readers
        self.bed_reader.stop()
        self.hand_reader.stop()
        self.radar_reader.stop()
        
        # Stop file logger
        if self.file_logger:
            self.file_logger.stop()
            
        # Stop processor
        if self.processor_thread:
            self.processor_thread.join(timeout=3)
            
        logger.info("Pipeline stopped")
        
    def _process_loop(self):
        """
        Background thread that moves data from reader queues to storage
        """
        logger.info("Processor thread started")
        
        while self.running:
            try:
                # Process bed data
                bed_queue = self.bed_reader.get_queue()
                while not bed_queue.empty():
                    data = bed_queue.get_nowait()
                    self.db.insert_bed(data)
                    if self.file_logger:
                        self.file_logger.log(data)
                        
                # Process hand data
                hand_queue = self.hand_reader.get_queue()
                while not hand_queue.empty():
                    data = hand_queue.get_nowait()
                    self.db.insert_hand(data)
                    if self.file_logger:
                        self.file_logger.log(data)
                        
                # Process radar data
                radar_queue = self.radar_reader.get_queue()
                while not radar_queue.empty():
                    data = radar_queue.get_nowait()
                    self.db.insert_radar(data)
                    if self.file_logger:
                        self.file_logger.log(data)
                        
            except Exception as e:
                logger.error(f"Processor error: {e}")
                
            time.sleep(0.01)
            
        logger.info("Processor thread stopped")
        
    def get_database(self) -> TimeSeriesDB:
        """Get the time-series database for reading"""
        return self.db
        
    def get_stats(self) -> Dict:
        """Get statistics from all components"""
        stats = {
            'bed_reader': self.bed_reader.get_stats(),
            'hand_reader': self.hand_reader.get_stats(),
            'radar_reader': self.radar_reader.get_stats(),
            'database': self.db.get_stats()
        }
        
        if self.file_logger:
            stats['file_logger'] = self.file_logger.get_stats()
            
        return stats
        
    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("PIPELINE STATISTICS")
        print("=" * 60)
        
        print(f"\nBed Reader:")
        print(f"  Connected: {stats['bed_reader']['connected']}")
        print(f"  Total reads: {stats['bed_reader']['total_reads']}")
        print(f"  Errors: {stats['bed_reader']['error_count']}")
        print(f"  Queue size: {stats['bed_reader']['queue_size']}")
        
        print(f"\nHand Reader:")
        print(f"  Connected: {stats['hand_reader']['connected']}")
        print(f"  Total reads: {stats['hand_reader']['total_reads']}")
        print(f"  Errors: {stats['hand_reader']['error_count']}")
        print(f"  Queue size: {stats['hand_reader']['queue_size']}")
        
        print(f"\nRadar Reader:")
        print(f"  Connected: {stats['radar_reader']['connected']}")
        print(f"  Total reads: {stats['radar_reader']['total_reads']}")
        print(f"  Errors: {stats['radar_reader']['error_count']}")
        print(f"  Queue size: {stats['radar_reader']['queue_size']}")
        
        print(f"\nDatabase:")
        print(f"  Total stored: {stats['database']['total_stored']}")
        print(f"  Bed points: {stats['database']['bed_points']}")
        print(f"  Hand points: {stats['database']['hand_points']}")
        print(f"  Radar points: {stats['database']['radar_points']}")
        
        if 'file_logger' in stats:
            print(f"\nFile Logger:")
            print(f"  Total written: {stats['file_logger']['total_written']}")
            print(f"  Current file: {stats['file_logger']['current_file']}")
            
        print("=" * 60 + "\n")
