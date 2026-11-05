#!/usr/bin/env python3
"""
SnoopGuard laptop decryptor (Viewer 2).

Decrypts SnoopGuard captures/imports (.sgc) on a computer that is NOT the
watched phone, using the exported wrapped private key (.sgk) and your passphrase.
The private key never has to touch the phone.

This mirrors, byte for byte, the formats the Android app writes:

  KeyVault blob (.sgk, "SGK1"):
    "SGK1" | int32-BE iterations | uint8 saltLen | salt | 12B nonce | AES-256-GCM(ct+tag)
    key = PBKDF2-HMAC-SHA256(passphrase, salt, iterations, dklen=32)

  Capture file (.sgc, "SGC1"):
    "SGC1" | int32-BE sealedLen | sealedKey | StreamingAead ciphertext
    sealedKey = HPKE(public key).encrypt(serialized per-file StreamingAead keyset, AD)

Associated data is the constant b"snoopguard-v1" for both HPKE and the stream.

Usage:
    python snoopguard_decrypt.py --key snoopguard-private-key.sgk CAP1.sgc CAP2.sgc ...
    python snoopguard_decrypt.py --key key.sgk --out-dir ./decrypted ./captures/*.sgc

Each output is written next to its input (or into --out-dir) with the ".sgc"
suffix removed; a magic-byte sniff adds .jpg/.png/.mp4 when the name has no
extension. You are prompted for the passphrase (or set SNOOPGUARD_PASSPHRASE).
"""
import argparse
import getpass
import hashlib
import io
import os
import struct
import sys

import tink
from tink import hybrid, streaming_aead, secret_key_access, proto_keyset_format
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AD = b"snoopguard-v1"
SGK_MAGIC = b"SGK1"
SGC_MAGIC = b"SGC1"
NONCE_LEN = 12


def unwrap_private_key(blob: bytes, passphrase: str) -> bytes:
    """Reverse KeyVault.wrap: passphrase + .sgk blob -> serialized private keyset."""
    if blob[:4] != SGK_MAGIC:
        raise ValueError("Not a SnoopGuard key file (bad magic)")
    off = 4
    (iterations,) = struct.unpack_from(">i", blob, off); off += 4
    salt_len = blob[off]; off += 1
    salt = blob[off:off + salt_len]; off += salt_len
    nonce = blob[off:off + NONCE_LEN]; off += NONCE_LEN
    ciphertext = blob[off:]
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, iterations, dklen=32)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Wrong passphrase or corrupt key file")


def decrypt_capture(private_keyset: bytes, src_path: str, out_path: str) -> None:
    """Reverse FileCrypto.encrypt for one .sgc file."""
    priv_handle = proto_keyset_format.parse(private_keyset, secret_key_access.TOKEN)
    hybrid_dec = priv_handle.primitive(hybrid.HybridDecrypt)

    with open(src_path, "rb") as f:
        magic = f.read(4)
        if magic != SGC_MAGIC:
            raise ValueError(f"{src_path}: not a SnoopGuard capture (bad magic)")
        (sealed_len,) = struct.unpack(">i", f.read(4))
        if not (1 <= sealed_len <= 10_000):
            raise ValueError(f"{src_path}: corrupt header")
        sealed_key = f.read(sealed_len)
        stream_keyset = hybrid_dec.decrypt(sealed_key, AD)
        stream_handle = proto_keyset_format.parse(stream_keyset, secret_key_access.TOKEN)
        saead = stream_handle.primitive(streaming_aead.StreamingAead)
        # The rest of the file is the StreamingAead ciphertext.
        with saead.new_decrypting_stream(f, AD) as ds, open(out_path, "wb") as out:
            while True:
                chunk = ds.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)


def sniff_extension(path: str) -> str:
    """Add a file extension by magic bytes when the recovered name has none."""
    if os.path.splitext(path)[1]:
        return path
    with open(path, "rb") as f:
        head = f.read(16)
    if head[:3] == b"\xff\xd8\xff":
        return path + ".jpg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return path + ".png"
    if head[4:8] == b"ftyp":
        return path + ".mp4"
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Decrypt SnoopGuard .sgc files.")
    parser.add_argument("--key", required=True, help="Exported wrapped private key (.sgk)")
    parser.add_argument("--out-dir", help="Directory for decrypted output (default: next to each input)")
    parser.add_argument("files", nargs="+", help="One or more .sgc files")
    args = parser.parse_args(argv)

    hybrid.register()
    streaming_aead.register()

    with open(args.key, "rb") as f:
        key_blob = f.read()
    passphrase = os.environ.get("SNOOPGUARD_PASSPHRASE") or getpass.getpass("Passphrase: ")
    private_keyset = unwrap_private_key(key_blob, passphrase)

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)

    failures = 0
    for src in args.files:
        base = os.path.basename(src)
        if base.endswith(".sgc"):
            base = base[:-4]
        dest_dir = args.out_dir or os.path.dirname(os.path.abspath(src))
        out_path = os.path.join(dest_dir, base)
        try:
            decrypt_capture(private_keyset, src, out_path)
            out_path = sniff_extension(out_path)
            print(f"ok:  {src} -> {out_path}")
        except Exception as e:
            failures += 1
            print(f"ERR: {src}: {e}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
