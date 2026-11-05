#!/usr/bin/env python3
"""
Self-test for snoopguard_decrypt.py.

Produces the SGK1 (wrapped key) and SGC1 (capture) formats exactly as the
Android app's KeyVault/FileCrypto do, then decrypts them back with the shipped
tool and checks the payload round-trips — including a payload larger than the
1 MB streaming segment (the video case) and a wrong-passphrase rejection.

This proves the Python side implements the documented container formats. It does
NOT by itself prove cross-language compatibility with Tink-Java; that rests on
Tink's wire-format compatibility across languages. (A future CI step could have
the Java build emit a vector for this test to consume.)

Run:  pip install -r requirements.txt && python selftest.py
"""
import io
import os
import struct
import tempfile

import tink
from tink import hybrid, streaming_aead, secret_key_access, proto_keyset_format

import snoopguard_decrypt as sg


def make_keypair():
    hybrid.register()
    streaming_aead.register()
    tmpl = hybrid.hybrid_key_templates.DHKEM_X25519_HKDF_SHA256_HKDF_SHA256_AES_256_GCM
    priv = tink.new_keyset_handle(tmpl)
    pub = priv.public_keyset_handle()
    priv_bytes = proto_keyset_format.serialize(priv, secret_key_access.TOKEN)
    pub_bytes = proto_keyset_format.serialize_without_secret(pub)
    return pub_bytes, priv_bytes


def wrap_private_key(private_keyset: bytes, passphrase: str) -> bytes:
    """Mirror of KeyVault.wrap."""
    import hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iterations = 210_000
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, iterations, dklen=32)
    ct = AESGCM(key).encrypt(nonce, private_keyset, None)
    return sg.SGK_MAGIC + struct.pack(">i", iterations) + bytes([len(salt)]) + salt + nonce + ct


def encrypt_capture(public_keyset: bytes, data: bytes, dest_path: str) -> None:
    """Mirror of FileCrypto.encrypt."""
    pub = proto_keyset_format.parse_without_secret(public_keyset)
    hybrid_enc = pub.primitive(hybrid.HybridEncrypt)
    stream_tmpl = streaming_aead.streaming_aead_key_templates.AES256_GCM_HKDF_1MB
    stream_handle = tink.new_keyset_handle(stream_tmpl)
    stream_keyset = proto_keyset_format.serialize(stream_handle, secret_key_access.TOKEN)
    sealed = hybrid_enc.encrypt(stream_keyset, sg.AD)
    saead = stream_handle.primitive(streaming_aead.StreamingAead)
    with open(dest_path, "wb") as out:
        out.write(sg.SGC_MAGIC)
        out.write(struct.pack(">i", len(sealed)))
        out.write(sealed)
        with saead.new_encrypting_stream(out, sg.AD) as es:
            es.write(data)


def main() -> int:
    hybrid.register()
    streaming_aead.register()
    pub, priv = make_keypair()
    passphrase = "correct horse battery staple"
    key_blob = wrap_private_key(priv, passphrase)

    payloads = {
        "small": b"a selfie's worth of bytes",
        "empty": b"",
        "large": os.urandom(5 * 1024 * 1024 + 123),  # crosses the 1 MB segment
    }

    with tempfile.TemporaryDirectory() as d:
        key_path = os.path.join(d, "key.sgk")
        with open(key_path, "wb") as f:
            f.write(key_blob)

        # unwrap round-trip
        assert sg.unwrap_private_key(key_blob, passphrase) == priv, "unwrap mismatch"
        try:
            sg.unwrap_private_key(key_blob, "wrong")
            return _fail("wrong passphrase was accepted")
        except ValueError:
            pass

        private_keyset = sg.unwrap_private_key(key_blob, passphrase)
        for name, data in payloads.items():
            enc = os.path.join(d, f"{name}.sgc")
            dec = os.path.join(d, f"{name}.out")
            encrypt_capture(pub, data, enc)
            sg.decrypt_capture(private_keyset, enc, dec)
            with open(dec, "rb") as f:
                got = f.read()
            if got != data:
                return _fail(f"{name}: payload mismatch ({len(got)} vs {len(data)} bytes)")
            print(f"ok:  {name} round-trip ({len(data)} bytes)")

        # wrong key cannot decrypt
        _, priv2 = make_keypair()
        try:
            sg.decrypt_capture(priv2, os.path.join(d, "small.sgc"), os.path.join(d, "x.out"))
            return _fail("wrong private key decrypted a capture")
        except Exception:
            print("ok:  wrong key rejected")

    print("\nALL SELFTESTS PASSED")
    return 0


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
