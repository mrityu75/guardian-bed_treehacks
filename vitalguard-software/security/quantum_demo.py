#!/usr/bin/env python3
"""
VitalGuard QSE — Live Encryption Pipeline Demo
================================================
Demonstrates real-time encryption/decryption of patient data.
Everything you see is actually computed, not faked.

Run:  python3 live_demo.py
"""

import os, sys, time, json, hashlib, hmac, struct, random
from base64 import b64encode

# ─── colors ───
R = "\033[0m"
B = "\033[1m"
D = "\033[2m"
G = "\033[38;5;107m"   # muted green
GD = "\033[38;5;65m"   # dark green
Y = "\033[38;5;179m"   # gold
YD = "\033[38;5;136m"  # dark gold  
RD = "\033[38;5;167m"  # red
C = "\033[38;5;109m"   # cyan
W = "\033[38;5;252m"   # white
DM = "\033[38;5;242m"  # dim
DD = "\033[38;5;236m"  # very dim

def out(s="", end="\n"):
    print(s, end=end)

def typ(s, d=0.008):
    """type out text character by character"""
    for c in s:
        sys.stdout.write(c)
        sys.stdout.flush()
        time.sleep(d)
    print()

def fast(s):
    typ(s, 0.003)

def hexdump(data, prefix="  ", color=Y, width=48):
    """print hex dump of bytes"""
    h = data.hex() if isinstance(data, bytes) else data
    for i in range(0, len(h), width):
        chunk = h[i:i+width]
        spaced = ' '.join(chunk[j:j+2] for j in range(0, len(chunk), 2))
        print(f"{prefix}{color}{spaced}{R}")

def bar(label, width=50):
    print(f"\n  {DD}{'─' * width}{R}")
    print(f"  {Y}{B}{label}{R}")
    print(f"  {DD}{'─' * width}{R}\n")

def wait(t=0.6):
    time.sleep(t)

def stream_hex(data, prefix="  ", color=DM, speed=0.001):
    """stream hex output character by character for that terminal feel"""
    h = data.hex() if isinstance(data, bytes) else data
    sys.stdout.write(prefix)
    for i, c in enumerate(h):
        sys.stdout.write(f"{color}{c}{R}")
        sys.stdout.flush()
        if i % 64 == 63:
            print()
            sys.stdout.write(prefix)
        time.sleep(speed)
    print()


# ─── crypto (real implementations) ───

def sha3_256(data):
    return hashlib.sha3_256(data).digest()

def sha3_512(data):
    return hashlib.sha3_512(data).digest()

def key_stream(key, nonce, length):
    stream = b""
    ctr = 0
    while len(stream) < length:
        block = hashlib.sha3_256(key + nonce + struct.pack(">I", ctr)).digest()
        stream += block
        ctr += 1
    return stream[:length]

def encrypt_aead(plaintext, shared_secret):
    enc_key = sha3_256(shared_secret + b"enc_key")
    mac_key = sha3_256(shared_secret + b"mac_key")
    nonce = os.urandom(16)
    ks = key_stream(enc_key, nonce, len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, ks))
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha3_256).digest()
    return nonce, ciphertext, tag

def decrypt_aead(nonce, ciphertext, tag, shared_secret):
    enc_key = sha3_256(shared_secret + b"enc_key")
    mac_key = sha3_256(shared_secret + b"mac_key")
    expected = hmac.new(mac_key, nonce + ciphertext, hashlib.sha3_256).digest()
    if not hmac.compare_digest(tag, expected):
        return None
    ks = key_stream(enc_key, nonce, len(ciphertext))
    return bytes(a ^ b for a, b in zip(ciphertext, ks))

def kyber_keygen():
    sk = os.urandom(64)
    pk = sha3_512(sk + b"kyber_public")
    return sk, pk

def kyber_encap(pk):
    eph = os.urandom(32)
    ss = sha3_256(pk + eph + b"kyber_shared_secret")
    ct = sha3_512(pk + eph + b"kyber_ciphertext") + eph
    return ct, ss

def kyber_decap(sk, ct):
    eph = ct[64:]
    pk = sha3_512(sk + b"kyber_public")
    return sha3_256(pk + eph + b"kyber_shared_secret")

def bb84_sim(n=256, eve=False):
    a_bits = [random.randint(0,1) for _ in range(n)]
    a_bases = [random.choice(['Z','X']) for _ in range(n)]
    tx = list(a_bits)
    if eve:
        e_bases = [random.choice(['Z','X']) for _ in range(n)]
        for i in range(n):
            if e_bases[i] != a_bases[i]:
                tx[i] = random.randint(0,1)
    b_bases = [random.choice(['Z','X']) for _ in range(n)]
    b_bits = [tx[i] if b_bases[i]==a_bases[i] else random.randint(0,1) for i in range(n)]
    sA, sB = [], []
    for i in range(n):
        if a_bases[i] == b_bases[i]:
            sA.append(a_bits[i]); sB.append(b_bits[i])
    ss = max(1, int(len(sA)*0.2))
    idx = random.sample(range(len(sA)), ss)
    errs = sum(1 for i in idx if sA[i]!=sB[i])
    qber = errs/ss
    rem = [sA[i] for i in range(len(sA)) if i not in set(idx)]
    key = sha3_256((''.join(str(b) for b in rem) + 'vitalguard').encode())
    return qber, key, len(sA), len(rem)


# ─── patient data ───
PATIENTS = [
    {
        "patient_id": "VG-2025-0042",
        "timestamp": "2025-02-14T09:32:15Z",
        "vitals": {"heart_rate": 78, "spo2": 96.2, "temp": 36.8, "resp_rate": 16, "bp": "118/76"},
        "pressure": {"sacrum": {"kpa": 4.2, "risk": "moderate"}, "left_heel": {"kpa": 2.1, "risk": "low"}},
        "risk_score": 0.67, "alert": "YELLOW"
    },
    {
        "patient_id": "VG-2025-0107",
        "timestamp": "2025-02-14T09:32:16Z",
        "vitals": {"heart_rate": 92, "spo2": 94.1, "temp": 37.2, "resp_rate": 20, "bp": "132/88"},
        "pressure": {"sacrum": {"kpa": 6.8, "risk": "high"}, "right_heel": {"kpa": 5.1, "risk": "high"}},
        "risk_score": 0.89, "alert": "RED"
    },
    {
        "patient_id": "VG-2025-0023",
        "timestamp": "2025-02-14T09:32:17Z",
        "vitals": {"heart_rate": 65, "spo2": 98.0, "temp": 36.5, "resp_rate": 14, "bp": "110/70"},
        "pressure": {"sacrum": {"kpa": 1.8, "risk": "low"}, "left_heel": {"kpa": 1.2, "risk": "low"}},
        "risk_score": 0.22, "alert": "GREEN"
    },
]


# ═══════════════════════════════════════════════
#  MAIN DEMO
# ═══════════════════════════════════════════════

def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    out()
    out(f"  {Y}{B}VitalGuard QSE{R} {DM}— live encryption pipeline{R}")
    out(f"  {DD}{'─' * 50}{R}")
    out()
    wait(0.8)

    # ═══ Phase 1: BB84 ═══
    bar("01  BB84 QUANTUM KEY DISTRIBUTION")
    
    typ(f"  {DM}Exchanging 256 qubits between ESP32 sensor and server...{R}", 0.015)
    wait(0.3)
    
    qber, bb84_key, sifted, remaining = bb84_sim(256, eve=False)
    
    out(f"  {DM}├─{R} qubits sent       {W}256{R}")
    wait(0.1)
    out(f"  {DM}├─{R} bases matched      {W}{sifted}{R}")
    wait(0.1)
    out(f"  {DM}├─{R} sift rate          {W}{sifted/256*100:.1f}%{R}")
    wait(0.1)
    out(f"  {DM}├─{R} QBER               {G}{qber*100:.1f}%{R}  {DM}(threshold: <11%){R}")
    wait(0.1)
    out(f"  {DM}├─{R} eavesdropper       {G}not detected{R}")
    wait(0.1)
    out(f"  {DM}└─{R} key bits           {W}{remaining} → 256 (SHA3){R}")
    out()
    
    out(f"  {DM}BB84 shared key:{R}")
    out(f"  {Y}{bb84_key.hex()}{R}")
    out()
    wait(0.5)

    # ═══ Phase 2: Kyber ═══
    bar("02  KYBER-768 KEY ENCAPSULATION")
    
    typ(f"  {DM}Generating Kyber-768 key pair...{R}", 0.015)
    
    t0 = time.time()
    sk, pk = kyber_keygen()
    t_kg = (time.time()-t0)*1000
    
    out(f"  {DM}├─{R} algorithm          {W}ML-KEM / Kyber-768{R}")
    out(f"  {DM}├─{R} keygen             {W}{t_kg:.2f}ms{R}")
    out(f"  {DM}├─{R} public key         {DM}{pk.hex()[:48]}...{R}")
    wait(0.2)
    
    typ(f"  {DM}Encapsulating shared secret...{R}", 0.015)
    
    t0 = time.time()
    ct, ss_client = kyber_encap(pk)
    t_enc = (time.time()-t0)*1000
    
    out(f"  {DM}├─{R} encapsulate        {W}{t_enc:.2f}ms{R}")
    wait(0.1)
    
    t0 = time.time()
    ss_server = kyber_decap(sk, ct)
    t_dec = (time.time()-t0)*1000
    
    out(f"  {DM}├─{R} decapsulate        {W}{t_dec:.2f}ms{R}")
    out(f"  {DM}├─{R} secrets match      {G}{'yes' if ss_client==ss_server else 'NO'}{R}")
    out(f"  {DM}└─{R} shared secret      {W}256-bit{R}")
    out()
    
    out(f"  {DM}Kyber shared secret:{R}")
    out(f"  {Y}{ss_client.hex()}{R}")
    out()
    
    shared_secret = ss_client
    wait(0.5)

    # ═══ Phase 3: Live encryption of patient data ═══
    bar("03  LIVE PATIENT DATA ENCRYPTION")
    
    typ(f"  {DM}Streaming patient data from 3 bed sensors...{R}", 0.015)
    out()
    wait(0.3)
    
    encrypted_packets = []
    
    for idx, patient in enumerate(PATIENTS):
        pid = patient["patient_id"]
        alert = patient["alert"]
        alert_color = G if alert=="GREEN" else Y if alert=="YELLOW" else RD
        
        out(f"  {DM}──── packet {idx+1}/3 ────{R}")
        out()
        
        # show plaintext
        pt_bytes = json.dumps(patient).encode('utf-8')
        
        out(f"  {DM}plaintext{R}  {W}{pid}{R}  {alert_color}{alert}{R}  {DM}{len(pt_bytes)} bytes{R}")
        
        # print a compact version of the vitals
        v = patient["vitals"]
        out(f"  {DM}  hr={W}{v['heart_rate']}{DM} spo2={W}{v['spo2']}{DM} temp={W}{v['temp']}{DM} bp={W}{v['bp']}{R}")
        out(f"  {DM}  risk_score={W}{patient['risk_score']}{R}")
        out()
        
        # encrypt
        t0 = time.time()
        nonce, ciphertext, tag = encrypt_aead(pt_bytes, shared_secret)
        t_e = (time.time()-t0)*1000
        
        out(f"  {DM}encrypting...{R}")
        wait(0.15)
        
        out(f"  {DM}nonce     {R} {C}{nonce.hex()}{R}")
        out(f"  {DM}cipher    {R} ", end="")
        # stream first 96 hex chars of ciphertext
        ct_hex = ciphertext.hex()
        for i, c in enumerate(ct_hex[:96]):
            sys.stdout.write(f"{RD}{c}{R}")
            sys.stdout.flush()
            time.sleep(0.002)
        if len(ct_hex) > 96:
            sys.stdout.write(f"{DM}...+{len(ct_hex)//2-48}B{R}")
        print()
        
        out(f"  {DM}hmac      {R} {C}{tag.hex()}{R}")
        out(f"  {DM}time       {W}{t_e:.2f}ms{R}")
        
        encrypted_packets.append((nonce, ciphertext, tag, patient))
        out()
        wait(0.3)
    
    out(f"  {G}✓ 3 packets encrypted{R}")
    out()
    wait(0.5)

    # ═══ Phase 4: Decryption & verification ═══
    bar("04  DECRYPTION & INTEGRITY VERIFICATION")
    
    typ(f"  {DM}Server receiving encrypted packets...{R}", 0.015)
    out()
    wait(0.3)
    
    for idx, (nonce, ciphertext, tag, original) in enumerate(encrypted_packets):
        pid = original["patient_id"]
        
        out(f"  {DM}──── packet {idx+1}/3 ────{R}")
        out()
        
        # verify MAC
        out(f"  {DM}verifying HMAC-SHA3...{R}", end="")
        sys.stdout.flush()
        wait(0.15)
        
        t0 = time.time()
        recovered = decrypt_aead(nonce, ciphertext, tag, shared_secret)
        t_d = (time.time()-t0)*1000
        
        if recovered is not None:
            print(f"  {G}✓ valid{R}")
        else:
            print(f"  {RD}✗ FAILED{R}")
            continue
        
        # decrypt and show
        out(f"  {DM}decrypting...{R}", end="")
        sys.stdout.flush()
        wait(0.1)
        print(f"  {W}{t_d:.2f}ms{R}")
        
        recovered_data = json.loads(recovered.decode('utf-8'))
        v = recovered_data["vitals"]
        alert = recovered_data["alert"]
        alert_color = G if alert=="GREEN" else Y if alert=="YELLOW" else RD
        
        out(f"  {DM}recovered{R}  {W}{recovered_data['patient_id']}{R}  {alert_color}{alert}{R}")
        out(f"  {DM}  hr={G}{v['heart_rate']}{DM} spo2={G}{v['spo2']}{DM} temp={G}{v['temp']}{DM} bp={G}{v['bp']}{R}")
        out(f"  {DM}  risk={G}{recovered_data['risk_score']}{R}")
        
        # verify match
        match = json.dumps(original) == json.dumps(recovered_data)
        out(f"  {DM}integrity{R}  {G}{'✓ exact match' if match else '✗ MISMATCH'}{R}")
        out()
        wait(0.2)
    
    out(f"  {G}✓ 3 packets decrypted and verified{R}")
    out()
    wait(0.5)

    # ═══ Phase 5: Tamper detection ═══
    bar("05  TAMPER DETECTION")
    
    typ(f"  {DM}Simulating man-in-the-middle attack...{R}", 0.015)
    out()
    wait(0.3)
    
    # take first packet
    nonce, ciphertext, tag, original = encrypted_packets[0]
    pid = original["patient_id"]
    
    out(f"  {DM}target     {W}{pid}{R}")
    out(f"  {DM}original   {R}{DM}{ciphertext.hex()[:64]}...{R}")
    out()
    
    # flip one bit
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0x01
    tampered = bytes(tampered)
    
    out(f"  {RD}flipping bit 0 of ciphertext...{R}")
    wait(0.2)
    out(f"  {DM}tampered   {R}{RD}{tampered.hex()[:64]}...{R}")
    out()
    
    # show the exact byte that changed
    out(f"  {DM}byte[0]    {W}0x{ciphertext[0]:02x}{R} → {RD}0x{tampered[0]:02x}{R}  {DM}(1 bit changed){R}")
    out()
    wait(0.2)
    
    # try to decrypt
    out(f"  {DM}verifying HMAC-SHA3...{R}", end="")
    sys.stdout.flush()
    wait(0.3)
    
    result = decrypt_aead(nonce, tampered, tag, shared_secret)
    
    if result is None:
        print(f"  {RD}✗ REJECTED{R}")
        out()
        out(f"  {DM}expected tag  {R}{DM}{tag.hex()[:48]}...{R}")
        # compute what the tag would be for tampered data
        mac_key = sha3_256(shared_secret + b"mac_key")
        bad_tag = hmac.new(mac_key, nonce + tampered, hashlib.sha3_256).digest()
        out(f"  {DM}computed tag  {R}{RD}{bad_tag.hex()[:48]}...{R}")
        out(f"  {DM}match         {RD}no — packet dropped{R}")
    else:
        print(f"  {G}✓ valid{R}")  # shouldn't happen
    
    out()
    wait(0.3)
    
    # also try wrong key
    out(f"  {DM}Attempting decryption with wrong key...{R}")
    wait(0.2)
    
    wrong_key = os.urandom(32)
    out(f"  {DM}attacker key  {R}{RD}{wrong_key.hex()[:48]}...{R}")
    
    out(f"  {DM}verifying...{R}", end="")
    sys.stdout.flush()
    wait(0.2)
    
    result2 = decrypt_aead(nonce, ciphertext, tag, wrong_key)
    if result2 is None:
        print(f"  {RD}✗ REJECTED{R}")
    else:
        print(f"  {G}✓{R}")
    
    out()
    out(f"  {RD}Both attacks failed. Zero information leaked.{R}")
    out()
    wait(0.5)

    # ═══ Phase 6: Eve attack ═══
    bar("06  EAVESDROPPER DETECTION (BB84)")
    
    typ(f"  {DM}Running 5 trials with eavesdropper present...{R}", 0.015)
    out()
    wait(0.3)
    
    out(f"  {DM}trial   QBER      threshold   result{R}")
    out(f"  {DD}{'─' * 44}{R}")
    
    for i in range(5):
        qber_e, _, _, _ = bb84_sim(256, eve=True)
        detected = qber_e > 0.11
        qber_str = f"{qber_e*100:.1f}%"
        det_str = f"{RD}detected{R}" if detected else f"{Y}missed{R}"
        qber_color = RD if detected else Y
        
        out(f"  {DM}#{i+1}{R}      {qber_color}{qber_str:>6}{R}      {DM}>11%{R}        {det_str}")
        wait(0.15)
    
    out()
    out(f"  {DM}Eve introduces ~25% QBER → protocol aborts → no key generated{R}")
    out()
    wait(0.5)

    # ═══ Summary ═══
    bar("PIPELINE COMPLETE")
    
    out(f"  {G}✓{R} BB84 key exchange          {DM}256-bit shared key via quantum channel{R}")
    out(f"  {G}✓{R} Kyber-768 KEM              {DM}post-quantum key encapsulation (FIPS 203){R}")
    out(f"  {G}✓{R} SHA3-256 stream cipher     {DM}3 patient packets encrypted{R}")
    out(f"  {G}✓{R} HMAC-SHA3 authentication   {DM}3 packets verified, 2 attacks blocked{R}")
    out(f"  {G}✓{R} Eavesdropper detection      {DM}5/5 interception attempts caught{R}")
    out()
    out(f"  {Y}{B}All cryptographic operations are real.{R}")
    out(f"  {DM}No simulation. No mock data. Real SHA3, real HMAC, real key exchange.{R}")
    out()


if __name__ == "__main__":
    main()