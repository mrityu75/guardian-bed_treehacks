"""
BB84 QKD Tests
================
Tests BB84 protocol, eavesdropper detection, and integration
with VitalGuard encryption pipeline.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security.bb84_qkd import BB84KeyExchange, EveInterceptor, qkd_key_exchange
from security.quantum_crypto import QuantumCipher

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
print("TEST 1: BB84 Protocol — No Noise (Ideal Channel)")
print("=" * 60)

bb84 = BB84KeyExchange(n_qubits=128, noise_probability=0.0)
result = bb84.run_protocol()

check("Protocol completes", result is not None)
check("Sift rate ~50%", 0.35 < result["sift_rate"] < 0.65,
      f"sift_rate={result['sift_rate']}")
check("No eavesdropper detected", result["secure"])
check("Final key generated", result["final_key_hex"] is not None)
check("Key is 256 bits", result["final_key_bits"] == 256)
check("Low error rate (<5%)", result["error_estimation"]["error_rate"] < 0.05,
      f"QBER={result['error_estimation']['error_rate']}")
print(f"  \u2139\uFE0F  Sifted: {result['sifted_key_length']} bits, "
      f"QBER: {result['error_estimation']['error_rate']}, "
      f"Time: {result['elapsed_sec']}s")


# =========================================
print(f"\n{'=' * 60}")
print("TEST 2: BB84 Protocol — Noisy Channel (5%)")
print("=" * 60)

bb84_noisy = BB84KeyExchange(n_qubits=128, noise_probability=0.05)
result_noisy = bb84_noisy.run_protocol()

check("Noisy protocol completes", result_noisy is not None)
check("Still secure at 5% noise", result_noisy["secure"],
      f"QBER={result_noisy['error_estimation']['error_rate']}")
check("Error rate reflects noise", result_noisy["error_estimation"]["error_rate"] <= 0.15,
      f"QBER={result_noisy['error_estimation']['error_rate']}")
print(f"  \u2139\uFE0F  QBER: {result_noisy['error_estimation']['error_rate']}")


# =========================================
print(f"\n{'=' * 60}")
print("TEST 3: Eavesdropper Detection (Eve)")
print("=" * 60)

# Run with eavesdropper
bb84_eve = BB84KeyExchange(n_qubits=512, noise_probability=0.0)
circuits = bb84_eve.alice_prepare()

# Eve intercepts
eve = EveInterceptor()
tampered_circuits = eve.intercept(circuits)
check("Eve intercepted all qubits", len(eve.intercepted_bits) == 512)

# Bob measures Eve's re-prepared qubits
bb84_eve.bob_measure(tampered_circuits)
alice_sifted, bob_sifted = bb84_eve.sift_keys()
error_info = bb84_eve.estimate_error(alice_sifted, bob_sifted, sample_fraction=0.4)

check("Eve introduces high QBER (>11%)", error_info["error_rate"] > 0.11,
      f"QBER={error_info['error_rate']}")
check("Eavesdropper detected!", error_info["eavesdropper_detected"])
check("Protocol reports insecure", not error_info["secure"])
print(f"  \u2139\uFE0F  Eve's QBER: {error_info['error_rate']} (expected ~25%)")


# =========================================
print(f"\n{'=' * 60}")
print("TEST 4: QKD → Encryption Integration")
print("=" * 60)

# Generate key via BB84
key = qkd_key_exchange(n_qubits=128, noise=0.0)
check("QKD produced a key", key is not None)
check("Key is 32 bytes", len(key) == 32 if key else False)

# Use QKD key for VitalGuard encryption
if key:
    patient_data = b'{"patient_id":"PID-2406","risk_score":82.5,"hr":104,"spo2":92}'

    encrypted = QuantumCipher.encrypt(patient_data, key)
    check("Encrypted with QKD key", "ciphertext" in encrypted)

    decrypted = QuantumCipher.decrypt(encrypted, key)
    check("Decrypted matches original", decrypted == patient_data)

    # Wrong key fails
    wrong_key = os.urandom(32)
    failed_decrypt = QuantumCipher.decrypt(encrypted, wrong_key)
    check("Wrong key fails", failed_decrypt is None)


# =========================================
print(f"\n{'=' * 60}")
print("TEST 5: Key Uniqueness")
print("=" * 60)

# Multiple runs should produce different keys
keys = set()
for i in range(3):
    k = qkd_key_exchange(n_qubits=32, noise=0.0)
    if k:
        keys.add(k.hex())

check("Multiple runs produce unique keys", len(keys) >= 2,
      f"unique={len(keys)}/3")


print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)