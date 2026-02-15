"""
BB84 Quantum Key Distribution for VitalGuard
==============================================
Simulates BB84 protocol for secure key exchange between
ESP32 sensor module and the monitoring server.

In a real deployment, this would use:
- Quantum optical channel (photon polarization states)
- Classical authenticated channel (for basis reconciliation)

Here we simulate using Qiskit's AerSimulator to demonstrate:
1. Alice (ESP32) prepares qubits in random bases
2. Bob (Server) measures in random bases
3. Sifting: keep only matching-basis results
4. Error estimation: detect eavesdropping
5. Privacy amplification: compress to final secure key
6. Key is used for AES-256 symmetric encryption of medical data

The simulation includes realistic quantum channel noise
to demonstrate robustness of the protocol.
"""

import random
import hashlib
import json
import time
from typing import Tuple, Optional, List

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# ============================================
# BB84 PROTOCOL IMPLEMENTATION
# ============================================

class BB84KeyExchange:
    """
    BB84 Quantum Key Distribution Protocol.

    Roles:
    - Alice (ESP32 bed/hand module): Prepares and sends qubits
    - Bob (VitalGuard server): Measures received qubits

    The protocol generates a shared secret key that is
    information-theoretically secure against quantum attacks.
    """

    def __init__(self, n_qubits: int = 256, noise_probability: float = 0.0):
        """
        Args:
            n_qubits: Number of qubits to exchange (more = longer key)
            noise_probability: Quantum channel noise (0.0 = ideal, 0.1 = 10% error)
        """
        self.n_qubits = n_qubits
        self.noise_prob = noise_probability
        self.backend = AerSimulator()

        # Protocol state
        self.alice_bits = []
        self.alice_bases = []
        self.bob_bases = []
        self.bob_results = []
        self.sifted_key = []
        self.final_key = None
        self.error_rate = 0.0
        self.eavesdropper_detected = False

    # --- Step 1: Alice prepares qubits ---
    def alice_prepare(self) -> List[QuantumCircuit]:
        """
        Alice generates random bits and encodes them in random bases.

        Bases:
        - Z basis: |0⟩ = bit 0, |1⟩ = bit 1
        - X basis: |+⟩ = bit 0, |−⟩ = bit 1

        Returns:
            List of quantum circuits (one per qubit)
        """
        self.alice_bits = [random.randint(0, 1) for _ in range(self.n_qubits)]
        self.alice_bases = [random.choice(["Z", "X"]) for _ in range(self.n_qubits)]

        circuits = []
        for i in range(self.n_qubits):
            qc = QuantumCircuit(1, 1)

            if self.alice_bases[i] == "Z":
                # Z basis: |0⟩ or |1⟩
                if self.alice_bits[i] == 1:
                    qc.x(0)
            else:
                # X basis: |+⟩ or |−⟩
                if self.alice_bits[i] == 0:
                    qc.h(0)  # |+⟩
                else:
                    qc.x(0)
                    qc.h(0)  # |−⟩

            # Simulate channel noise (bit-flip)
            if self.noise_prob > 0 and random.random() < self.noise_prob:
                qc.x(0)

            circuits.append(qc)

        return circuits

    # --- Step 2: Bob measures qubits ---
    def bob_measure(self, circuits: List[QuantumCircuit]) -> List[int]:
        """
        Bob randomly chooses measurement bases and measures each qubit.

        Args:
            circuits: Quantum circuits from Alice

        Returns:
            List of measurement results (0 or 1)
        """
        self.bob_bases = [random.choice(["Z", "X"]) for _ in range(self.n_qubits)]
        self.bob_results = []

        for i in range(self.n_qubits):
            qc = circuits[i].copy()

            # Apply basis transformation before measurement
            if self.bob_bases[i] == "X":
                qc.h(0)

            qc.measure(0, 0)

            # Run on simulator
            transpiled = transpile(qc, self.backend)
            job = self.backend.run(transpiled, shots=1)
            counts = job.result().get_counts()
            measured_bit = int(list(counts.keys())[0])
            self.bob_results.append(measured_bit)

        return self.bob_results

    # --- Step 3: Basis reconciliation (classical channel) ---
    def sift_keys(self) -> Tuple[List[int], List[int]]:
        """
        Alice and Bob compare bases over classical channel.
        Keep only bits where they used the same basis.

        Returns:
            (alice_sifted, bob_sifted) - matching key bits
        """
        alice_sifted = []
        bob_sifted = []

        for i in range(self.n_qubits):
            if self.alice_bases[i] == self.bob_bases[i]:
                alice_sifted.append(self.alice_bits[i])
                bob_sifted.append(self.bob_results[i])

        self.sifted_key = alice_sifted
        return alice_sifted, bob_sifted

    # --- Step 4: Error estimation ---
    def estimate_error(self, alice_sifted: List[int], bob_sifted: List[int],
                       sample_fraction: float = 0.2) -> dict:
        """
        Sacrifice a fraction of the sifted key to estimate error rate.
        High error rate (>11%) indicates eavesdropping.

        BB84 security threshold: QBER < 11% = secure

        Args:
            alice_sifted: Alice's sifted key bits
            bob_sifted: Bob's sifted key bits
            sample_fraction: Fraction of bits to check (these are discarded)

        Returns:
            dict with error_rate, eavesdropper_detected, remaining_bits
        """
        n = len(alice_sifted)
        sample_size = max(1, int(n * sample_fraction))

        # Randomly select bits to compare
        indices = random.sample(range(n), sample_size)
        errors = sum(1 for i in indices if alice_sifted[i] != bob_sifted[i])

        self.error_rate = errors / sample_size if sample_size > 0 else 0.0
        self.eavesdropper_detected = self.error_rate > 0.11  # BB84 threshold

        # Remove sampled bits from key
        remaining = [alice_sifted[i] for i in range(n) if i not in set(indices)]

        return {
            "error_rate": round(self.error_rate, 4),
            "sample_size": sample_size,
            "errors_found": errors,
            "eavesdropper_detected": self.eavesdropper_detected,
            "remaining_key_bits": len(remaining),
            "secure": not self.eavesdropper_detected,
        }

    # --- Step 5: Privacy amplification ---
    def privacy_amplification(self, key_bits: List[int], target_bytes: int = 32) -> bytes:
        """
        Compress the raw key into a shorter, more secure final key.
        Uses universal hashing (SHA-256) to remove any partial
        information an eavesdropper might have.

        Args:
            key_bits: Remaining sifted key bits after error estimation
            target_bytes: Desired key length in bytes (32 = 256-bit)

        Returns:
            Final cryptographic key (bytes)
        """
        # Convert bits to bytes
        bit_string = "".join(str(b) for b in key_bits)
        raw_bytes = bit_string.encode("utf-8")

        # Hash to target length (privacy amplification)
        self.final_key = hashlib.sha3_256(raw_bytes + b"vitalguard_qkd_pa").digest()
        return self.final_key

    # --- Full protocol run ---
    def run_protocol(self) -> dict:
        """
        Execute the complete BB84 protocol.

        Returns:
            dict with all protocol results
        """
        start = time.time()

        # Step 1: Alice prepares
        circuits = self.alice_prepare()

        # Step 2: Bob measures
        self.bob_measure(circuits)

        # Step 3: Sift
        alice_sifted, bob_sifted = self.sift_keys()

        # Step 4: Error estimation
        error_info = self.estimate_error(alice_sifted, bob_sifted)

        # Step 5: Privacy amplification (only if secure)
        final_key = None
        if not error_info["eavesdropper_detected"]:
            remaining = [alice_sifted[i] for i in range(len(alice_sifted))
                        if i not in set(random.sample(range(len(alice_sifted)),
                        max(1, int(len(alice_sifted) * 0.2))))]
            final_key = self.privacy_amplification(remaining)

        elapsed = time.time() - start

        return {
            "protocol": "BB84",
            "n_qubits": self.n_qubits,
            "noise_probability": self.noise_prob,
            "sifted_key_length": len(alice_sifted),
            "sift_rate": round(len(alice_sifted) / self.n_qubits, 4),
            "error_estimation": error_info,
            "final_key_hex": final_key.hex() if final_key else None,
            "final_key_bits": 256 if final_key else 0,
            "secure": not error_info["eavesdropper_detected"],
            "elapsed_sec": round(elapsed, 3),
        }


# ============================================
# EAVESDROPPER SIMULATION (Eve)
# ============================================

class EveInterceptor:
    """
    Simulates an eavesdropper (Eve) performing intercept-resend attack.
    Eve measures Alice's qubits and re-prepares them for Bob.
    This introduces detectable errors (~25% QBER).
    """

    def __init__(self):
        self.backend = AerSimulator()
        self.intercepted_bits = []

    def intercept(self, circuits: List[QuantumCircuit]) -> List[QuantumCircuit]:
        """
        Eve intercepts, measures, and re-prepares qubits.

        Args:
            circuits: Original circuits from Alice

        Returns:
            New circuits re-prepared by Eve (with introduced errors)
        """
        new_circuits = []
        self.intercepted_bits = []

        for qc in circuits:
            # Eve measures in random basis
            eve_basis = random.choice(["Z", "X"])
            measure_qc = qc.copy()
            if eve_basis == "X":
                measure_qc.h(0)
            measure_qc.measure(0, 0)

            transpiled = transpile(measure_qc, self.backend)
            job = self.backend.run(transpiled, shots=1)
            counts = job.result().get_counts()
            eve_bit = int(list(counts.keys())[0])
            self.intercepted_bits.append(eve_bit)

            # Re-prepare qubit in Eve's basis
            new_qc = QuantumCircuit(1, 1)
            if eve_basis == "Z":
                if eve_bit == 1:
                    new_qc.x(0)
            else:
                if eve_bit == 0:
                    new_qc.h(0)
                else:
                    new_qc.x(0)
                    new_qc.h(0)

            new_circuits.append(new_qc)

        return new_circuits


# ============================================
# INTEGRATION WITH VITALGUARD
# ============================================

def qkd_key_exchange(n_qubits: int = 128, noise: float = 0.0) -> Optional[bytes]:
    """
    High-level function: run BB84 and return a shared key.
    Returns None if eavesdropper detected.

    Args:
        n_qubits: Number of qubits to use (128 = fast, 512 = more secure)
        noise: Channel noise probability

    Returns:
        32-byte shared secret key, or None if insecure
    """
    bb84 = BB84KeyExchange(n_qubits=n_qubits, noise_probability=noise)
    result = bb84.run_protocol()

    if result["secure"] and result["final_key_hex"]:
        return bytes.fromhex(result["final_key_hex"])
    return None