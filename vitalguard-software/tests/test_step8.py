"""
Step 8 Tests: Quantum-Safe Encryption
========================================
Tests KEM, authenticated encryption, signatures, and end-to-end secure channel.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security.quantum_crypto import (
    QuantumKEM, QuantumCipher, QuantumSignature, SecureChannel
)

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274C {name} \u2014 {detail}")
        failed += 1


# =========================================
print("=" * 60)
print("TEST 1: Quantum KEM (Key Encapsulation)")
print("=" * 60)

keys = QuantumKEM.keygen()
check("KeyGen produces public key", len(keys["public_key"]) > 20)
check("KeyGen produces private key", len(keys["private_key"]) > 20)
check("Algorithm labeled", keys["algorithm"] == "VitalGuard-Kyber768-Hybrid")

# Encapsulate + Decapsulate
ct, ss_sender = QuantumKEM.encapsulate(keys["public_key"])
check("Encapsulate produces ciphertext", len(ct) > 20)
check("Encapsulate produces shared secret", len(ss_sender) == 32)

ss_receiver = QuantumKEM.decapsulate(keys["private_key"], ct)
check("Decapsulate recovers same secret", ss_sender == ss_receiver)

# Different keys = different secrets
keys2 = QuantumKEM.keygen()
ss_wrong = QuantumKEM.decapsulate(keys2["private_key"], ct)
check("Wrong key = different secret", ss_wrong != ss_sender)


# =========================================
print(f"\n{'=' * 60}")
print("TEST 2: Authenticated Encryption")
print("=" * 60)

secret = os.urandom(32)
plaintext = b"Patient HR: 104 bpm, SpO2: 92%, CRITICAL"

enc = QuantumCipher.encrypt(plaintext, secret)
check("Encrypted has ciphertext", "ciphertext" in enc)
check("Encrypted has nonce", "nonce" in enc)
check("Encrypted has MAC", "mac" in enc)
check("Ciphertext != plaintext", enc["ciphertext"] != plaintext)

dec = QuantumCipher.decrypt(enc, secret)
check("Decrypt recovers plaintext", dec == plaintext)

# Tampered data should fail
tampered = dict(enc)
import base64
ct_bytes = bytearray(base64.b64decode(tampered["ciphertext"]))
ct_bytes[0] ^= 0xFF  # Flip one byte
tampered["ciphertext"] = base64.b64encode(ct_bytes).decode()
dec_tampered = QuantumCipher.decrypt(tampered, secret)
check("Tampered data rejected", dec_tampered is None)

# Wrong key should fail
wrong_secret = os.urandom(32)
dec_wrong = QuantumCipher.decrypt(enc, wrong_secret)
check("Wrong key rejected", dec_wrong is None)


# =========================================
print(f"\n{'=' * 60}")
print("TEST 3: Digital Signatures")
print("=" * 60)

sig_keys = QuantumSignature.keygen()
check("Sig keygen produces signing key", len(sig_keys["signing_key"]) > 20)
check("Sig keygen produces verify key", len(sig_keys["verify_key"]) > 20)

data = b"VitalGuard risk assessment: score 82/100"
sig = QuantumSignature.sign(data, sig_keys["signing_key"])
check("Signature produced", len(sig) > 20)

verified = QuantumSignature.verify(data, sig, sig_keys["verify_key"], sig_keys["signing_key"])
check("Valid signature verified", verified)

# Tampered data
verified_bad = QuantumSignature.verify(b"tampered data", sig, sig_keys["verify_key"], sig_keys["signing_key"])
check("Tampered data fails verification", not verified_bad)


# =========================================
print(f"\n{'=' * 60}")
print("TEST 4: Secure Channel (End-to-End)")
print("=" * 60)

# Simulate server (ESP32/bed module) and client (dashboard)
server = SecureChannel()
client = SecureChannel()

# Step 1: Server generates keys
server_info = server.init_server()
check("Server init: has public key", "public_key" in server_info)
check("Server init: has session ID", "session_id" in server_info)

# Step 2: Client encapsulates using server's public key
client_resp = client.init_client(server_info["public_key"])
check("Client init: has ciphertext", "ciphertext" in client_resp)

# Step 3: Server completes handshake
server.complete_handshake(client_resp["ciphertext"])
check("Handshake complete: secrets match",
      server.shared_secret == client.shared_secret)

# Step 4: Encrypt patient data (server → client)
patient_data = {
    "patient_id": "PID-2406",
    "risk_score": 82.5,
    "vitals": {"hr": 104, "spo2": 92, "temp": 38.4},
    "alerts": ["Tachycardia with hypoxemia"],
    "timestamp": 1234567890,
}

envelope = server.encrypt_patient_data(patient_data)
check("Envelope has encrypted data", "encrypted" in envelope)
check("Envelope has signature", envelope["signature"] is not None)
check("Envelope has PQC version", envelope["pqc_version"] == "1.0")

# Step 5: Client decrypts
decrypted = client.decrypt_patient_data(envelope)
check("Client decrypts successfully", decrypted is not None)
check("Decrypted matches original", decrypted == patient_data)
check("Risk score preserved", decrypted["risk_score"] == 82.5)
check("Vitals preserved", decrypted["vitals"]["hr"] == 104)


# =========================================
print(f"\n{'=' * 60}")
print("TEST 5: Performance Benchmark")
print("=" * 60)

import time

# Benchmark encryption of typical patient frame
large_data = {
    "patient_id": "PID-TEST",
    "vitals": {"hr": 72, "temp": 36.7, "spo2": 98, "hrv": 42, "rr": 16},
    "pressure_zones": {f"zone_{i}": {"pressure": 0.3, "risk": 0.2} for i in range(12)},
    "posture": {"current": "supine", "duration_min": 30},
    "risk_score": 25.4,
    "alerts": [],
}

# Encrypt 1000 times
start = time.time()
N = 1000
for _ in range(N):
    env = server.encrypt_patient_data(large_data)
enc_time = (time.time() - start) / N * 1000  # ms per encryption

# Decrypt 1000 times
start = time.time()
for _ in range(N):
    client.decrypt_patient_data(env)
dec_time = (time.time() - start) / N * 1000

check(f"Encryption < 5ms per frame", enc_time < 5, f"{enc_time:.2f}ms")
check(f"Decryption < 5ms per frame", dec_time < 5, f"{dec_time:.2f}ms")
print(f"  \u2139\uFE0F  Encrypt: {enc_time:.3f}ms | Decrypt: {dec_time:.3f}ms per frame")

# Data size overhead
plain_size = len(json.dumps(large_data))
enc_size = len(json.dumps(env))
overhead = (enc_size / plain_size - 1) * 100
print(f"  \u2139\uFE0F  Plain: {plain_size}B → Encrypted: {enc_size}B (overhead: {overhead:.0f}%)")


print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)