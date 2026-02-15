"""
All configuration in one place
"""

class Config:
    # ESP32 IPs (change these to your actual IPs)
    BED_ESP32_IP = "172.30.202.213"
    HAND_ESP32_IP = "172.30.202.194"
    BED2_ESP32_IP = "172.30.202.57"
    # Radar serial port
    RADAR_PORT = "/dev/ttyUSB0"  # or COM3 on Windows
    RADAR_BAUDRATE = 115200
    
    # Data collection rate (how often to poll)
    BED_POLL_RATE_HZ = 10      # 10 times per second
    HAND_POLL_RATE_HZ = 20     # 20 times per second (faster for PPG)
    RADAR_POLL_RATE_HZ = 10    # 10 times per second
    
    # Storage settings
    MAX_MEMORY_POINTS = 10000  # Keep last 10,000 data points in memory
    SAVE_TO_FILE = True        # Save to disk?
    FILE_LOG_DIR = "./data_logs"
    
    # Error handling
    MAX_RETRIES = 3
    RETRY_DELAY_SEC = 1
    ALERT_ON_DISCONNECT = True
