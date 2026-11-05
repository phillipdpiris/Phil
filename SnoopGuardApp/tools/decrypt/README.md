# SnoopGuard laptop decryptor (Viewer 2)

Decrypt SnoopGuard captures and imports (`.sgc`) on your computer — the strongest
of the three viewers, because the private key never touches the watched phone.

You need two things:
1. the **exported key file** (`snoopguard-private-key.sgk`) you saved during setup, and
2. your **passphrase**.

## Install

```bash
cd SnoopGuardApp/tools/decrypt
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## Use

```bash
# decrypt a few files next to themselves
python snoopguard_decrypt.py --key snoopguard-private-key.sgk capture_173...sgc

# decrypt a whole folder into ./decrypted
python snoopguard_decrypt.py --key key.sgk --out-dir ./decrypted /path/to/captures/*.sgc
```

You'll be prompted for the passphrase (or set `SNOOPGUARD_PASSPHRASE` in the
environment). Each output is written with the `.sgc` suffix removed; if the name
has no extension, the tool sniffs the magic bytes and appends `.jpg`, `.png`, or
`.mp4`.

## How it stays consistent with the app

The app (Kotlin/Tink-Java) and this tool (Python/Tink-Python) implement the same
two container formats, documented at the top of `snoopguard_decrypt.py`:

- **`.sgk`** — the private key wrapped with PBKDF2-HMAC-SHA256 + AES-256-GCM.
- **`.sgc`** — an HPKE-sealed per-file key followed by a `StreamingAead` payload.

Tink keeps its wire formats compatible across languages, so a `.sgc` written by
the Android app decrypts here and vice versa.

## Self-test

`selftest.py` writes both formats the way the app does and decrypts them back,
including a payload larger than the 1 MB streaming segment (the video case) and
wrong-passphrase / wrong-key rejection:

```bash
python selftest.py
```

This checks the Python side against the documented formats. It does not by itself
prove cross-language parity with the Java app — that relies on Tink's
cross-language wire compatibility. (A later CI step could have the Android build
emit a vector for this test to consume, closing that loop.)
