#!/usr/bin/env python3
"""
Guardian Bed - LD2410C Radar Monitor
Reads radar data and sends to API server
"""
import serial
import time
import requests
import struct

# Configuration
SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 115200
API_ENDPOINT = "http://172.30.202.252:8000/api/radar"

print("="*60)
print("GUARDIAN BED - RADAR MONITOR")
print("="*60)
print(f"Serial Port: {SERIAL_PORT}")
print(f"Baud Rate: {BAUD_RATE}")
print(f"API Endpoint: {API_ENDPOINT}")
print("="*60)
print()

# Open serial connection
try:
    radar = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print("✓ Radar connected")
except Exception as e:
    print(f"✗ Failed to connect to radar: {e}")
    print("Check wiring and serial port configuration")
    exit(1)

# Clear buffer
radar.reset_input_buffer()
time.sleep(0.5)

print("Starting radar monitoring...")
print()

def parse_radar_frame(data):
    """Parse LD2410C data frame"""
    try:
        if len(data) < 13:
            return None
        
        target_state = data[6] if len(data) > 6 else 0
        moving_distance = data[9] if len(data) > 9 else 0
        stationary_distance = data[12] if len(data) > 12 else 0
        
        presence = 0
        distance_cm = 0
        
        if target_state > 0:
            presence = target_state
            if moving_distance > 0 and stationary_distance > 0:
                distance_cm = min(moving_distance, stationary_distance) * 10
            elif moving_distance > 0:
                distance_cm = moving_distance * 10
            elif stationary_distance > 0:
                distance_cm = stationary_distance * 10
        
        return {
            'presence': presence,
            'distance_cm': distance_cm,
            'moving': presence in [1, 3],
            'stationary': presence in [2, 3]
        }
    except Exception as e:
        return None

# Main loop
packet_buffer = bytearray()
last_send_time = 0
SEND_INTERVAL = 1

while True:
    try:
        if radar.in_waiting > 0:
            chunk = radar.read(radar.in_waiting)
            packet_buffer.extend(chunk)
            
            if len(packet_buffer) >= 13:
                parsed = parse_radar_frame(packet_buffer)
                
                if parsed and time.time() - last_send_time >= SEND_INTERVAL:
                    parsed['timestamp'] = time.time()
                    
                    status = "No presence"
                    if parsed['presence'] == 1:
                        status = f"Moving target at {parsed['distance_cm']}cm"
                    elif parsed['presence'] == 2:
                        status = f"Stationary target at {parsed['distance_cm']}cm"
                    elif parsed['presence'] == 3:
                        status = f"Both targets at {parsed['distance_cm']}cm"
                    
                    print(f"[{time.strftime('%H:%M:%S')}] {status}")
                    
                    try:
                        response = requests.post(API_ENDPOINT, json=parsed, timeout=2)
                        if response.status_code == 200:
                            print("  ✓ Sent to API")
                        else:
                            print(f"  ✗ API error: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"  ✗ API send failed: {e}")
                    
                    last_send_time = time.time()
                
                packet_buffer = packet_buffer[-50:]
        
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        print("\n\nStopping radar monitor...")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)

radar.close()
print("Done!")
