# GuardianBed - AI Patient Monitoring System

Real-time multi-modal sensor system for preventing pressure ulcers and detecting patient deterioration.

## 🎯 Current Status

✅ **Data Pipeline:** Fully operational
- ESP32 bed module collecting sensor data at 10Hz
- In-memory time-series database
- File logging system
- Stable, zero-error data collection

## 📊 Hardware Sensors

- **12 FSR pressure sensors** (4x3 grid - shoulders, back, sacrum, heels)
- **3 DS18B20 temperature sensors** (monitoring skin temperature)
- **2 MPU6050 accelerometers** (detecting movement/repositioning)
- **3 microphone sensors** (breathing/distress detection)

**Data format:** JSON at 10 samples/second

## 🚀 Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Update config with your ESP32 IP
# Edit pipeline/config.py

# Run pipeline
python main.py
```

## 🤖 For AI/ML Integration

Access real-time sensor data:
```python
from pipeline.pipeline import DataPipeline
from pipeline.config import Config

pipeline = DataPipeline(Config())
pipeline.start()

# Get database access
db = pipeline.get_database()

# Latest reading
latest = db.get_latest_bed()

# Historical data (last 60 seconds)
history = db.get_bed_history(seconds=60)
```

## 📁 Project Structure
```
guardian-bed/
├── main.py                    # Entry point
├── pipeline/
│   ├── config.py             # ESP32 IP & settings
│   ├── pipeline.py           # Main coordinator
│   ├── readers/              # Hardware communication
│   │   ├── bed_reader.py
│   │   ├── hand_reader.py
│   │   └── radar_reader.py
│   └── storage/              # Data storage
│       ├── time_series_db.py
│       └── file_logger.py
└── data_logs/                # Collected data (.jsonl)
```

## 📋 Next Steps

- [ ] Program hand module ESP32
- [ ] Implement AI/ML risk scoring models
- [ ] Build real-time dashboard
- [ ] Integrate mmWave radar (optional)

## 👥 Team

Built for TreeHacks 2026 - Healthcare Track
