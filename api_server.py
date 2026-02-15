from flask import Flask, jsonify, request
from flask_cors import CORS
from pipeline.pipeline import DataPipeline
from pipeline.config import Config
import threading
import time

app = Flask(__name__)
CORS(app)  # Allow frontend to access

# Storage for radar data
radar_data = {
    'presence': 0,
    'distance_cm': 0,
    'moving': False,
    'stationary': False,
    'timestamp': 0
}

# Start pipeline in background
config = Config()
pipeline = DataPipeline(config)

def start_pipeline():
    pipeline.start()
    print("Pipeline started in background")

# Start pipeline in separate thread
pipeline_thread = threading.Thread(target=start_pipeline, daemon=True)
pipeline_thread.start()
time.sleep(2)  # Wait for pipeline to initialize

@app.route('/api/latest', methods=['GET'])
def get_latest():
    """Get latest data from both modules"""
    db = pipeline.get_database()
    
    return jsonify({
        'bed': db.get_latest_bed(),
        'hand': db.get_latest_hand(),
        'timestamp': time.time()
    })

@app.route('/api/history/<int:seconds>', methods=['GET'])
def get_history(seconds):
    """Get historical data for last N seconds"""
    db = pipeline.get_database()
    
    return jsonify({
        'bed': db.get_bed_history(seconds=seconds),
        'hand': db.get_hand_history(seconds=seconds),
        'duration_seconds': seconds
    })

@app.route('/api/merged/<int:seconds>', methods=['GET'])
def get_merged(seconds):
    """Get merged data aligned by timestamp"""
    db = pipeline.get_database()
    
    bed_data = db.get_bed_history(seconds=seconds)
    hand_data = db.get_hand_history(seconds=seconds)
    
    # Merge by timestamp (simple approach - match closest timestamps)
    merged = []
    for bed_point in bed_data:
        # Find closest hand point
        bed_ts = bed_point.get('received_at', 0)
        closest_hand = min(hand_data, 
                          key=lambda h: abs(h.get('received_at', 0) - bed_ts),
                          default=None)
        
        merged.append({
            'timestamp': bed_ts,
            'bed': bed_point,
            'hand': closest_hand
        })
    
    return jsonify({
        'data': merged,
        'count': len(merged)
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get pipeline statistics"""
    return jsonify(pipeline.get_stats())

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    stats = pipeline.get_stats()
    return jsonify({
        'status': 'ok',
        'bed_connected': stats['bed_reader']['connected'],
        'hand_connected': stats['hand_reader']['connected']
    })

# Storage for transcripts (in-memory)
transcripts = []

@app.route('/api/transcript', methods=['POST'])
def add_transcript():
    """Receive transcript from Raspberry Pi"""
    data = request.json
    
    transcript = {
        'text': data.get('text', ''),
        'timestamp': data.get('timestamp', time.time()),
        'source': data.get('source', 'voice'),
        'id': len(transcripts) + 1
    }
    
    transcripts.append(transcript)
    
    # Keep only last 100 transcripts
    if len(transcripts) > 100:
        transcripts.pop(0)
    
    print(f"[TRANSCRIPT] {transcript['text']}")
    
    return jsonify({'status': 'ok', 'id': transcript['id']}), 200

@app.route('/api/transcripts/latest', methods=['GET'])
def get_latest_transcripts():
    """Get latest transcripts for AI team"""
    limit = request.args.get('limit', 10, type=int)
    return jsonify({
        'transcripts': transcripts[-limit:],
        'count': len(transcripts[-limit:])
    })

@app.route('/api/transcripts/all', methods=['GET'])
def get_all_transcripts():
    """Get all transcripts"""
    return jsonify({
        'transcripts': transcripts,
        'count': len(transcripts)
    })
@app.route('/api/radar', methods=['POST'])
def receive_radar():
    global radar_data
    try:
        radar_data = request.json
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/radar/latest', methods=['GET'])
def get_radar():
    return jsonify(radar_data)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GUARDIAN BED API SERVER")
    print("="*60)
    print("\nAPI Endpoints:")
    print("  GET /api/latest          - Latest data from both modules")
    print("  GET /api/history/<sec>   - Historical data (e.g., /api/history/60)")
    print("  GET /api/merged/<sec>    - Merged data by timestamp")
    print("  GET /api/stats           - Pipeline statistics")
    print("  GET /api/health          - Health check")
    print("\nStarting server on http://localhost:8000")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
