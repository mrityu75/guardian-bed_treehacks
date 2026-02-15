"""
Sensor Noise Models
====================
Adds realistic noise patterns to synthetic sensor data.
Models sensor drift, quantization, and random jitter
matching real ESP32 ADC + I2C sensor behaviors.
"""

import random
import math


def adc_noise(value: float, bits: int = 12, jitter: float = 0.02) -> int:
    """
    Simulate ESP32 ADC noise.
    Applies quantization + random jitter typical of 12-bit SAR ADC.

    Args:
        value: Normalized 0-1 input signal
        bits: ADC resolution (ESP32 = 12-bit)
        jitter: Random noise amplitude (fraction of full scale)
    """
    max_val = (2 ** bits) - 1
    noisy = value + random.gauss(0, jitter)
    noisy = max(0.0, min(1.0, noisy))
    return int(round(noisy * max_val))


def imu_noise(value: float, noise_std: float = 0.05) -> float:
    """
    Simulate MPU6050 accelerometer/gyroscope noise.
    Adds Gaussian noise + slight bias drift.

    Args:
        value: True sensor value
        noise_std: Standard deviation of noise
    """
    drift = random.gauss(0, noise_std * 0.3)
    jitter = random.gauss(0, noise_std)
    return round(value + drift + jitter, 6)


def temperature_noise(value: float, noise_std: float = 0.05) -> float:
    """
    Simulate DS18B20 / MAX30205 temperature sensor noise.
    DS18B20 has ~0.0625°C resolution, MAX30205 ~0.00390625°C.

    Args:
        value: True temperature in °C
        noise_std: Standard deviation (~0.05°C for DS18B20)
    """
    noisy = value + random.gauss(0, noise_std)
    # Quantize to DS18B20 resolution
    resolution = 0.0625
    return round(round(noisy / resolution) * resolution, 4)


def heart_rate_noise(value: float, noise_std: float = 1.5) -> dict:
    """
    Simulate MAX30102 IR/RED sensor output.
    Returns raw IR and RED values that correlate with heart rate.

    Args:
        value: Target heart rate in bpm
        noise_std: Beat-to-beat variability
    """
    noisy_hr = value + random.gauss(0, noise_std)
    noisy_hr = max(30, min(200, noisy_hr))

    # Simulate raw IR/RED values (arbitrary units, typical range 50k-120k)
    base_ir = 80000 + random.gauss(0, 5000)
    base_red = 75000 + random.gauss(0, 4000)

    # SpO2 correlation: higher SpO2 -> higher IR/RED ratio
    ir_val = int(base_ir + noisy_hr * 100)
    red_val = int(base_red + noisy_hr * 80)

    return {"ir": ir_val, "red": red_val, "estimated_hr": round(noisy_hr, 1)}


def microphone_noise(
    is_vocalization: bool = False,
    ambient_db: float = 35.0,
) -> int:
    """
    Simulate microphone ADC output.
    Normal ambient ~35-45dB, vocalization peaks ~60-80dB.

    Args:
        is_vocalization: Whether patient is vocalizing
        ambient_db: Background noise level
    """
    if is_vocalization:
        db = random.gauss(70, 8)
    else:
        db = random.gauss(ambient_db, 3)

    db = max(20, min(100, db))
    # Convert to ADC value (rough mapping: 0dB=0, 100dB=4095)
    adc_val = int((db / 100) * 4095)
    return max(0, min(4095, adc_val + random.randint(-50, 50)))


def pressure_drift(base_value: float, elapsed_min: float, rate: float = 0.002) -> float:
    """
    Simulate gradual pressure increase from tissue compression over time.
    Pressure naturally increases as tissue is compressed longer.

    Args:
        base_value: Initial pressure reading (0-1 normalized)
        elapsed_min: Minutes in current position
        rate: Drift rate per minute
    """
    drift = rate * elapsed_min * (1 + random.gauss(0, 0.1))
    return min(1.0, base_value + drift)
