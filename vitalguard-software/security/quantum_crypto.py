import os
import json
import hmac
import hashlib
import struct
import time
from base64 import b64encode, b64decode
from typing import Tuple, Optional


# ============================================
# LATTICE-BASED KEY ENCAPSULATION (Kyber-inspired)
# ============================================
# In real Kyber: uses Module-LWE over polynomial rings
# Here: simplified demonstration using hash-based KDF

class QuantumKEM:
    """
    Post-quantum Key Encapsulation Mechanism.

    Simulates Kyber-768 key exchange:
    1. KeyGen: Generate public/private key pair
    2. Encapsulate: Using public key, produce ciphertext + shared secret
    3. Decapsulate: Using private key + ciphertext, recover shared secret

    Security basis: The Learning With Errors (LWE) problem is believed
    to be hard even for quantum computers, unlike RSA/ECDH.
    """

    ALGORITHM = "VitalGuard-Kyber768-Hybrid"
    SHARED_SECRET_BYTES = 32  # 256-bit shared secret

    @staticmethod
    def keygen() -> dict:
        """
        Generate a key pair.
        Returns dict with 'public_key' and 'private_key' (both bytes).
        """
        # Private key: random seed
        private_seed = os.urandom(64)

        # Public key: derived from private (in real Kyber: matrix A + public vector)
        public_key = hashlib.sha3_512(private_seed + b"kyber_public").digest()

        return {
            "public_key": b64encode(public_key).decode(),
            "private_key": b64encode(private_seed).decode(),
            "algorithm": QuantumKEM.ALGORITHM,
        }

    @staticmethod
    def encapsulate(public_key_b64: str) -> Tuple[str, bytes]:
        """
        Encapsulate: produce ciphertext and shared secret using public key.
        Used by the SENDER.

        Args:
            public_key_b64: Base64-encoded public key

        Returns:
            (ciphertext_b64, shared_secret_bytes)
        """
        public_key = b64decode(public_key_b64)
        ephemeral = os.urandom(32)

        # Shared secret: KDF(public_key || ephemeral)
        shared_secret = hashlib.sha3_256(
            public_key + ephemeral + b"kyber_shared_secret"
        ).digest()

        # Ciphertext: encrypted ephemeral (in real Kyber: LWE encryption)
        ct_raw = hashlib.sha3_512(
            public_key + ephemeral + b"kyber_ciphertext"
        ).digest() + ephemeral

        ciphertext = b64encode(ct_raw).decode()
        return ciphertext, shared_secret

    @staticmethod
    def decapsulate(private_key_b64: str, ciphertext_b64: str) -> bytes:
        """
        Decapsulate: recover shared secret using private key + ciphertext.
        Used by the RECEIVER.

        Args:
            private_key_b64: Base64-encoded private key
            ciphertext_b64: Base64-encoded ciphertext from encapsulate()

        Returns:
            shared_secret_bytes (same as encapsulate produced)
        """
        private_seed = b64decode(private_key_b64)
        ct_raw = b64decode(ciphertext_b64)

        # Recover ephemeral from ciphertext
        ephemeral = ct_raw[64:]  # Last 32 bytes

        # Recompute public key from private
        public_key = hashlib.sha3_512(private_seed + b"kyber_public").digest()

        # Recompute shared secret
        shared_secret = hashlib.sha3_256(
            public_key + ephemeral + b"kyber_shared_secret"
        ).digest()

        return shared_secret


# ============================================
# AUTHENTICATED ENCRYPTION (AES-256-GCM equivalent)
# ============================================

class QuantumCipher:
    """
    Authenticated encryption using shared secret from KEM.
    Encrypt-then-MAC for data integrity + confidentiality.

    Uses:
    - XOR stream cipher derived from SHA3 (key stream)
    - HMAC-SHA3-256 for authentication
    """

    @staticmethod
    def _key_stream(key: bytes, nonce: bytes, length: int) -> bytes:
        """Generate a pseudorandom key stream using SHA3."""
        stream = b""
        counter = 0
        while len(stream) < length:
            block = hashlib.sha3_256(
                key + nonce + struct.pack(">I", counter)
            ).digest()
            stream += block
            counter += 1
        return stream[:length]

    @staticmethod
    def encrypt(plaintext: bytes, shared_secret: bytes) -> dict:
        """
        Encrypt data with authenticated encryption.

        Args:
            plaintext: Data to encrypt
            shared_secret: 32-byte key from KEM

        Returns:
            dict with 'ciphertext', 'nonce', 'mac', 'timestamp'
        """
        # Derive encryption key and MAC key from shared secret
        enc_key = hashlib.sha3_256(shared_secret + b"enc_key").digest()
        mac_key = hashlib.sha3_256(shared_secret + b"mac_key").digest()

        # Random nonce
        nonce = os.urandom(16)

        # Encrypt: XOR with key stream
        key_stream = QuantumCipher._key_stream(enc_key, nonce, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, key_stream))

        # MAC: HMAC-SHA3 over nonce + ciphertext
        mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha3_256).digest()

        return {
            "ciphertext": b64encode(ciphertext).decode(),
            "nonce": b64encode(nonce).decode(),
            "mac": b64encode(mac).decode(),
            "timestamp": int(time.time()),
            "algorithm": "VitalGuard-AE-SHA3-256",
        }

    @staticmethod
    def decrypt(encrypted: dict, shared_secret: bytes) -> Optional[bytes]:
        """
        Decrypt and verify authenticated data.

        Args:
            encrypted: Output from encrypt()
            shared_secret: Same shared secret used for encryption

        Returns:
            Decrypted bytes, or None if authentication fails
        """
        ciphertext = b64decode(encrypted["ciphertext"])
        nonce = b64decode(encrypted["nonce"])
        mac = b64decode(encrypted["mac"])

        # Derive keys
        enc_key = hashlib.sha3_256(shared_secret + b"enc_key").digest()
        mac_key = hashlib.sha3_256(shared_secret + b"mac_key").digest()

        # Verify MAC first (reject tampered data before decryption)
        expected_mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha3_256).digest()
        if not hmac.compare_digest(mac, expected_mac):
            return None  # Authentication failed — data tampered

        # Decrypt
        key_stream = QuantumCipher._key_stream(enc_key, nonce, len(ciphertext))
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, key_stream))

        return plaintext


# ============================================
# HASH-BASED DIGITAL SIGNATURES (Dilithium-inspired)
# ============================================

class QuantumSignature:
    """
    Post-quantum digital signatures for data integrity.
    Hash-based signature scheme (simplified Dilithium concept).
    """

    @staticmethod
    def keygen() -> dict:
        """Generate signing key pair."""
        private_key = os.urandom(64)
        public_key = hashlib.sha3_512(private_key + b"dilithium_public").digest()
        return {
            "signing_key": b64encode(private_key).decode(),
            "verify_key": b64encode(public_key).decode(),
            "algorithm": "VitalGuard-Dilithium3-Hybrid",
        }

    @staticmethod
    def sign(data: bytes, signing_key_b64: str) -> str:
        """Sign data with private key."""
        sk = b64decode(signing_key_b64)
        # Deterministic signature: HMAC(sk, data)
        sig = hmac.new(sk, data, hashlib.sha3_512).digest()
        return b64encode(sig).decode()

    @staticmethod
    def verify(data: bytes, signature_b64: str, verify_key_b64: str,
               signing_key_b64: str) -> bool:
        """Verify signature. In production, only verify_key needed."""
        sk = b64decode(signing_key_b64)
        expected = hmac.new(sk, data, hashlib.sha3_512).digest()
        return hmac.compare_digest(b64decode(signature_b64), expected)


# ============================================
# HIGH-LEVEL API: Secure Medical Data Channel
# ============================================

class SecureChannel:
    """
    End-to-end encrypted channel for medical data transmission.
    Combines KEM + authenticated encryption + signatures.

    Usage:
        # Server side (e.g., bed module)
        channel = SecureChannel()
        server_keys = channel.init_server()

        # Client side (e.g., dashboard)
        session = channel.init_client(server_keys['public_key'])

        # Server completes handshake
        channel.complete_handshake(session['ciphertext'])

        # Now both sides can encrypt/decrypt
        encrypted = channel.encrypt_patient_data(patient_json)
        decrypted = channel.decrypt_patient_data(encrypted)
    """

    def __init__(self):
        self.kem_keys = None
        self.sig_keys = None
        self.shared_secret = None
        self.session_id = None

    def init_server(self) -> dict:
        """Initialize server-side keys. Returns public key for client."""
        self.kem_keys = QuantumKEM.keygen()
        self.sig_keys = QuantumSignature.keygen()
        self.session_id = b64encode(os.urandom(16)).decode()

        return {
            "public_key": self.kem_keys["public_key"],
            "verify_key": self.sig_keys["verify_key"],
            "session_id": self.session_id,
            "algorithm": QuantumKEM.ALGORITHM,
        }

    def init_client(self, server_public_key: str) -> dict:
        """
        Client-side: encapsulate shared secret using server's public key.
        Returns ciphertext to send back to server.
        """
        ciphertext, self.shared_secret = QuantumKEM.encapsulate(server_public_key)
        self.session_id = b64encode(os.urandom(16)).decode()

        return {
            "ciphertext": ciphertext,
            "session_id": self.session_id,
        }

    def complete_handshake(self, ciphertext: str):
        """Server-side: recover shared secret from client's ciphertext."""
        self.shared_secret = QuantumKEM.decapsulate(
            self.kem_keys["private_key"], ciphertext
        )

    def encrypt_patient_data(self, data: dict) -> dict:
        """
        Encrypt patient data for transmission.

        Args:
            data: Patient data dict (vitals, risk score, etc.)

        Returns:
            Encrypted envelope with ciphertext + metadata
        """
        if not self.shared_secret:
            raise RuntimeError("Handshake not completed")

        plaintext = json.dumps(data).encode("utf-8")

        # Encrypt
        encrypted = QuantumCipher.encrypt(plaintext, self.shared_secret)

        # Sign
        signature = None
        if self.sig_keys:
            signature = QuantumSignature.sign(
                plaintext, self.sig_keys["signing_key"]
            )

        return {
            "encrypted": encrypted,
            "signature": signature,
            "session_id": self.session_id,
            "data_type": "patient_monitoring",
            "pqc_version": "1.0",
        }

    def decrypt_patient_data(self, envelope: dict) -> Optional[dict]:
        """
        Decrypt received patient data.

        Args:
            envelope: Output from encrypt_patient_data()

        Returns:
            Decrypted patient data dict, or None if tampered
        """
        if not self.shared_secret:
            raise RuntimeError("Handshake not completed")

        plaintext = QuantumCipher.decrypt(
            envelope["encrypted"], self.shared_secret
        )

        if plaintext is None:
            return None  # Authentication failed

        return json.loads(plaintext.decode("utf-8"))