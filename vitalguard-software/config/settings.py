"""
VitalGuard Global Configuration
================================
Central configuration for thresholds, sensor specs, and system parameters.
All values calibrated to match real ESP32 hardware sensor outputs.
"""

# --- Sensor Hardware Specs ---
SENSOR_SAMPLING_RATE_HZ = 20  # 50ms intervals (hand module)
BED_SAMPLING_RATE_HZ = 10     # 100ms intervals (bed module)

# FSR pressure sensors: 12 zones mapped to body regions
FSR_ZONES = {
    0: "head",
    1: "left_shoulder",
    2: "right_shoulder",
    3: "upper_back_left",
    4: "upper_back_right",
    5: "mid_back_left",
    6: "mid_back_right",
    7: "sacrum_left",
    8: "sacrum_right",
    9: "left_thigh",
    10: "right_thigh",
    11: "heels",
}

# FSR ADC range (ESP32 12-bit)
FSR_ADC_MIN = 0
FSR_ADC_MAX = 4095

# MPU6050 accelerometer/gyroscope (2 units on bed module)
MPU_ACCEL_RANGE = 16.0   # +/- 16g
MPU_GYRO_RANGE = 2000.0  # +/- 2000 deg/s

# DS18B20 temperature probes (3 on bed module)
BED_TEMP_PROBES = 3

# Microphones (3 on bed module)
MIC_COUNT = 3

# --- Vital Signs Thresholds ---
VITALS = {
    "heart_rate": {
        "normal_min": 60,
        "normal_max": 90,
        "caution_max": 100,
        "critical_max": 120,
        "critical_min": 45,
        "unit": "bpm",
    },
    "temperature": {
        "normal_min": 36.0,
        "normal_max": 37.5,
        "caution_max": 38.0,
        "critical_max": 39.0,
        "unit": "°C",
    },
    "spo2": {
        "normal_min": 95,
        "normal_max": 100,
        "caution_min": 93,
        "critical_min": 90,
        "unit": "%",
    },
    "hrv": {
        "normal_min": 35,
        "caution_min": 25,
        "critical_min": 15,
        "unit": "ms",
    },
    "respiratory_rate": {
        "normal_min": 12,
        "normal_max": 20,
        "caution_max": 24,
        "critical_max": 30,
        "unit": "/min",
    },
}

# --- Pressure Ulcer Prevention ---
REPOSITIONING_INTERVAL_MIN = 90    # minutes before mandatory reposition
REPOSITIONING_WARNING_MIN = 75     # warning threshold
PRESSURE_RISK_THRESHOLD = 0.7      # 0-1 scale, above = high risk
SACRAL_WEIGHT_MULTIPLIER = 1.5     # sacrum gets extra risk weighting

# --- Risk Score Weights ---
RISK_WEIGHTS = {
    "vitals": 0.30,
    "pressure": 0.30,
    "repositioning": 0.20,
    "movement": 0.10,
    "sound": 0.10,
}

# --- Personalized Risk Adjustments ---
AGE_ELDERLY_THRESHOLD = 65
DIABETIC_PRESSURE_MULTIPLIER = 1.3
ELDERLY_PRESSURE_MULTIPLIER = 1.2
POST_SPINAL_MOVEMENT_SENSITIVITY = 0.8

# --- Alert Levels ---
ALERT_LEVELS = {
    "info": {"risk_min": 0, "risk_max": 20},
    "caution": {"risk_min": 20, "risk_max": 40},
    "warning": {"risk_min": 40, "risk_max": 55},
    "critical": {"risk_min": 55, "risk_max": 100},
}

# --- API / Server ---
API_HOST = "0.0.0.0"
API_PORT = 8000
WS_BROADCAST_INTERVAL_SEC = 2  # WebSocket push frequency

# --- Groq API ---
GROQ_MODEL = "llama-3.3-70b-versatile"  # free tier
GROQ_MAX_TOKENS = 2000
GROQ_TEMPERATURE = 0.3  # low temp for clinical accuracy

# --- Email Alerts ---
EMAIL_COOLDOWN_SEC = 30  # 30 sec for experiments (normally 300)