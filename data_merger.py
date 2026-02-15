#!/usr/bin/env python3
"""
Guardian Bed - Data Merger
Collects data from 3 ESP32s, merges by timestamp, saves every 30 seconds
"""
import requests
import json
import time
import threading
from datetime import datetime

# ====== CONFIGURATION ======
ESP32_BED1_IP = "172.30.202.213"  # Bed upper + temps + MPUs
ESP32_BED2_IP = "172.30.202.57"   # Bed lower
ESP32_HAND_IP = "172.30.202.194"  # Hand module

OUTPUT_FILE = "live_data/merged_data.json"
UPDATE_INTERVAL = 1  # seconds
# =========================

class DataMerger:
    def __init__(self):
        self.latest_data = {
            "last_update": None,
            "bed_esp1": {},
            "bed_esp2": {},
            "hand": {},
            "voice_latest": None
        }
        self.running = False
        self.thread = None
        
    def fetch_esp32(self, ip, name):
        """Fetch data from an ESP32"""
        try:
            response = requests.get(f"http://{ip}/data", timeout=2)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {name}: {data.get('module', 'unknown')}")
                return data
        except Exception as e:
            print(f"✗ {name}: {e}")
        return None
    
    def fetch_voice_transcripts(self):
        """Fetch latest voice transcript from API"""
        try:
            response = requests.get("http://localhost:8000/api/transcripts/latest?limit=1", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get('transcripts'):
                    return data['transcripts'][0]
        except:
            pass
        return None
    
    def fetch_radar_data(self):
        """Fetch latest radar data from API"""
        try:
            response = requests.get("http://localhost:8000/api/radar/latest", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get('timestamp', 0) > 0:  # Check if we have real data
                    status = "No presence"
                    if data.get('moving'):
                        status = f"Moving at {data.get('distance_cm')}cm"
                    elif data.get('stationary'):
                        status = f"Stationary at {data.get('distance_cm')}cm"
                    print(f"✓ Radar: {status}")
                    return data
        except:
            pass
        return None
    
    def merge_data(self):
        """Fetch all data and merge"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching data...")
        
        # Get unified timestamp FIRST (so all modules use the same time)
        unified_timestamp = time.time()
        
        # Fetch from all ESP32s
        bed1 = self.fetch_esp32(ESP32_BED1_IP, "Bed ESP32 #1")
        bed2 = self.fetch_esp32(ESP32_BED2_IP, "Bed ESP32 #2")
        hand = self.fetch_esp32(ESP32_HAND_IP, "Hand Module")
        voice = self.fetch_voice_transcripts()
        radar = self.fetch_radar_data()
        
        # Add unified timestamp to each module
        if bed1:
            bed1['timestamp_unified'] = unified_timestamp
            bed1['timestamp_esp'] = bed1.pop('timestamp')  # Rename original
            self.latest_data['bed_esp1'] = bed1
            
        if bed2:
            bed2['timestamp_unified'] = unified_timestamp
            bed2['timestamp_esp'] = bed2.pop('timestamp')  # Rename original
            self.latest_data['bed_esp2'] = bed2
            
        if hand:
            hand['timestamp_unified'] = unified_timestamp
            hand['timestamp_esp'] = hand.pop('timestamp')  # Rename original
            self.latest_data['hand'] = hand
            
        if voice:
            voice['timestamp_unified'] = unified_timestamp
            self.latest_data['voice_latest'] = voice
        
        if radar:
            radar['timestamp_unified'] = unified_timestamp
            self.latest_data['radar'] = radar
            
        self.latest_data['last_update'] = unified_timestamp
        self.latest_data['last_update_readable'] = datetime.fromtimestamp(unified_timestamp).isoformat()
    
    def save_to_file(self):
        """Save merged data to JSON file"""
        try:
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(self.latest_data, f, indent=2)
            print(f"💾 Saved to {OUTPUT_FILE}")
        except Exception as e:
            print(f"✗ Save failed: {e}")
    
    def run_loop(self):
        """Main loop - fetch and save every N seconds"""
        print("="*60)
        print("GUARDIAN BED - DATA MERGER")
        print("="*60)
        print(f"Bed ESP32 #1: {ESP32_BED1_IP}")
        print(f"Bed ESP32 #2: {ESP32_BED2_IP}")
        print(f"Hand Module:  {ESP32_HAND_IP}")
        print(f"Output file:  {OUTPUT_FILE}")
        print(f"Update every: {UPDATE_INTERVAL} seconds")
        print("="*60)
        print("\nPress Ctrl+C to stop\n")
        
        while self.running:
            try:
                # Fetch and merge
                self.merge_data()
                
                # Save to file
                self.save_to_file()
                
                # Wait
                print(f"Waiting {UPDATE_INTERVAL} seconds...\n")
                time.sleep(UPDATE_INTERVAL)
                
            except Exception as e:
                print(f"Error in loop: {e}")
                time.sleep(5)
    
    def start(self):
        """Start the merger in background thread"""
        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=False)
        self.thread.start()
    
    def stop(self):
        """Stop the merger"""
        self.running = False
        if self.thread:
            self.thread.join()

def main():
    import os
    
    # Create output directory
    os.makedirs("live_data", exist_ok=True)
    
    # Create and start merger
    merger = DataMerger()
    
    try:
        merger.start()
        merger.thread.join()  # Wait for thread
    except KeyboardInterrupt:
        print("\n\nStopping...")
        merger.stop()
        print("Done!")

if __name__ == "__main__":
    main()
