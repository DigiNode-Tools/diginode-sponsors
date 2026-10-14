#!/usr/bin/env python3
#
# Name:    dgbaddr.py
# Purpose: Work out the receive addresses of a DigiByte wallet account from its extended public key (xpub/zpub - as
#          shown by Ledger Live), with no extra libraries. Native SegWit (BIP84, dgb1q...) or legacy (BIP44, D...).
#          The extended public key can only list addresses - it can never spend anything - but it shows all of them,
#          so it's kept secret (the DGB_DONATION_XPUB repository secret) and never printed.
#
# Usage:   from dgbaddr import receive_address; receive_address(xpub, index)

import hashlib

# secp256k1
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        s = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        s = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (s * s - a[0] - b[0]) % P
    return x, (s * (a[0] - x) - a[1]) % P


def _mul(k, pt=G):
    out = None
    while k:
        if k & 1:
            out = _add(out, pt)
        pt = _add(pt, pt)
        k >>= 1
    return out


def _decompress(pub):
    x = int.from_bytes(pub[1:], "big")
    y = pow((x * x * x + 7) % P, (P + 1) // 4, P)
    if y % 2 != pub[0] % 2:
        y = P - y
    return x, y


def _compress(pt):
    return bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, "big")


# ------------------------------------------------------------------------------------------
# Hashes. RIPEMD-160 isn't always available in hashlib (OpenSSL 3), so there's a small pure Python one as a fallback.

def _ripemd160(data):
    try:
        return hashlib.new("ripemd160", data).digest()
    except (ValueError, TypeError):
        pass
    import struct
    r1 = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,7,4,13,1,10,6,15,3,12,0,9,5,2,14,11,8,3,10,14,4,9,15,8,1,2,7,0,6,13,11,5,12,
          1,9,11,10,0,8,12,4,13,3,7,15,14,5,6,2,4,0,5,9,7,12,2,10,14,1,3,8,11,6,15,13]
    r2 = [5,14,7,0,9,2,11,4,13,6,15,8,1,10,3,12,6,11,3,7,0,13,5,10,14,15,8,12,4,9,1,2,15,5,1,3,7,14,6,9,11,8,12,2,10,0,4,13,
          8,6,4,1,3,11,15,0,5,12,2,13,9,7,10,14,12,15,10,4,1,5,8,7,6,2,13,14,0,3,9,11]
    s1 = [11,14,15,12,5,8,7,9,11,13,14,15,6,7,9,8,7,6,8,13,11,9,7,15,7,12,15,9,11,7,13,12,11,13,6,7,14,9,13,15,14,8,13,6,5,12,
          7,5,11,12,14,15,14,15,9,8,9,14,5,6,8,6,5,12,9,15,5,11,6,8,13,12,5,12,13,14,11,8,5,6]
    s2 = [8,9,9,11,13,15,15,5,7,7,8,11,14,14,12,6,9,13,15,7,12,8,9,11,7,7,12,7,6,15,13,11,9,7,15,11,8,6,6,14,12,13,5,14,13,13,
          7,5,15,5,8,11,14,14,6,14,6,9,12,9,12,5,15,8,8,5,12,9,12,5,14,6,8,13,6,5,15,13,11,11]
    k1 = [0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E]
    k2 = [0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0x00000000]
    f = [lambda x, y, z: x ^ y ^ z, lambda x, y, z: (x & y) | (~x & z), lambda x, y, z: (x | ~y) ^ z,
         lambda x, y, z: (x & z) | (y & ~z), lambda x, y, z: x ^ (y | ~z)]
    rol = lambda x, n: ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF
    msg = data + b"\x80" + b"\x00" * ((55 - len(data)) % 64) + struct.pack("<Q", len(data) * 8)
    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    for i in range(0, len(msg), 64):
        x = struct.unpack("<16I", msg[i:i + 64])
        a1, b1, c1, d1, e1 = h
        a2, b2, c2, d2, e2 = h
        for j in range(80):
            r = j // 16
            t = (rol((a1 + (f[r](b1, c1, d1) & 0xFFFFFFFF) + x[r1[j]] + k1[r]) & 0xFFFFFFFF, s1[j]) + e1) & 0xFFFFFFFF
            a1, e1, d1, c1, b1 = e1, d1, rol(c1, 10), b1, t
            t = (rol((a2 + (f[4 - r](b2, c2, d2) & 0xFFFFFFFF) + x[r2[j]] + k2[r]) & 0xFFFFFFFF, s2[j]) + e2) & 0xFFFFFFFF
            a2, e2, d2, c2, b2 = e2, d2, rol(c2, 10), b2, t
        t = (h[1] + c1 + d2) & 0xFFFFFFFF
        h = [t, (h[2] + d1 + e2) & 0xFFFFFFFF, (h[3] + e1 + a2) & 0xFFFFFFFF, (h[4] + a1 + b2) & 0xFFFFFFFF,
             (h[0] + b1 + c2) & 0xFFFFFFFF]
    return struct.pack("<5I", *h)


def _hash160(data):
    return _ripemd160(hashlib.sha256(data).digest())


# ------------------------------------------------------------------------------------------
# Base58Check and bech32

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58decode_check(s):
    n = 0
    for c in s:
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(s) - len(s.lstrip("1"))) + raw
    body, check = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4] != check:
        raise ValueError("bad checksum")
    return body


def _b58encode_check(body):
    raw = body + hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4]
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + out


BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if (b >> i) & 1 else 0
    return chk


def _bech32_encode(hrp, witver, prog):
    acc, bits, data = 0, 0, [witver]
    for b in prog:
        acc = (acc << 8) | b
        bits += 8
        while bits >= 5:
            bits -= 5
            data.append((acc >> bits) & 31)
    if bits:
        data.append((acc << (5 - bits)) & 31)
    values = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp] + data
    mod = _polymod(values + [0] * 6) ^ 1
    return hrp + "1" + "".join(BECH32[d] for d in data + [(mod >> 5 * (5 - i)) & 31 for i in range(6)])


# ------------------------------------------------------------------------------------------
# Extended public keys

def _parse_xpub(xpub):
    body = _b58decode_check(xpub.strip())
    if len(body) != 78:
        raise ValueError("not an extended public key")
    version, chain, key = body[:4], body[13:45], body[45:78]
    if key[0] not in (2, 3):
        raise ValueError("not a public key (is this a private key? never use one here)")
    return version, chain, key


def _child(chain, key, index):
    data = key + index.to_bytes(4, "big")
    i = hmac_sha512(chain, data)
    tweak = int.from_bytes(i[:32], "big")
    if tweak >= N:
        raise ValueError("invalid child")
    pt = _add(_mul(tweak), _decompress(key))
    return i[32:], _compress(pt)


def hmac_sha512(key, data):
    import hmac
    return hmac.new(key, data, hashlib.sha512).digest()


# Version bytes: zpub (BIP84) and xpub. Ledger Live shows an xpub even for Native SegWit accounts, so the address type
# is chosen separately.
ZPUB = bytes.fromhex("04b24746")


def receive_address(xpub, index, segwit=None, hrp="dgb"):
    """The receive address (chain 0) at this index. segwit: True for dgb1q..., False for legacy D..., None to decide
    from the key's version (zpub = SegWit, otherwise SegWit too - DigiByte donations use native SegWit)."""
    version, chain, key = _parse_xpub(xpub)
    if segwit is None:
        segwit = True
    chain, key = _child(chain, key, 0)          # External (receive) chain
    _, key = _child(chain, key, index)
    h = _hash160(key)
    if segwit:
        return _bech32_encode(hrp, 0, h)
    return _b58encode_check(bytes([0x1E]) + h)  # DigiByte legacy P2PKH (D...)


if __name__ == "__main__":
    # BIP84 test vector (mnemonic "abandon ... about"), first receive addresses on Bitcoin mainnet
    zpub = "zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xYYfG1m4wAcvPhXNfE3EfH1r1ADqtfSdVCToUG868RvUUkgDKf31mGDtKsAYz2oz2AGutZYs"
    assert receive_address(zpub, 0, hrp="bc") == "bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu", receive_address(zpub, 0, hrp="bc")
    assert receive_address(zpub, 1, hrp="bc") == "bc1qnjg0jd8228aq7egyzacy8cys3knf9xvrerkf9g"
    assert _ripemd160(b"") .hex() == "9c1185a5c5e9fc54612808977ee8f548b2258d31"
    print("dgbaddr: BIP84 test vectors pass")
