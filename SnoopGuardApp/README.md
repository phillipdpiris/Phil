# SnoopGuard (prototype)

An Android anti-snoop app with an encrypted media vault. Two jobs, one key:

1. **Watch** — once armed, it takes a front-camera selfie every time the phone
   is woken or unlocked (not just on a *failed* unlock, which is all the common
   "intruder selfie" apps catch), so you can see who has been using your phone.
2. **Vault** — it encrypts those captures, and any photos or videos you import,
   to a key the phone can write but cannot read, and can back them up off-device
   as ciphertext.

Everything is encrypted to a public key the device holds; only your passphrase
(which is never stored) can unlock the private half to view them.

> Status: working prototype, built and CI-verified (the app compiles and the
> debug APK builds; the crypto core has JVM unit tests and the laptop decryptor
> has a self-test). It has not yet been hand-tested on a physical device.

## Why it's different

- Catches the snooper who **already knows your PIN** (partner, roommate, coworker),
  which failed-unlock apps miss entirely.
- **Privacy-first**: captures are encrypted the instant they leave the camera.
  The watching service holds only the public key, so a seized, unlocked phone —
  even fully imaged — yields only ciphertext. A breach of the backup location
  leaks nothing (the lesson of the 2025 Tea breach).
- Follows Google Play's anti-stalkerware rules: visible icon, always-on
  foreground notification, watches only its own device. No disguises.

## The three tabs

| Tab | What it does |
|-----|--------------|
| **Watch** | Arm/disarm, log-only (no-camera) mode, and the (locked) capture list. |
| **Import** | Pick photos/videos; they're encrypted into the vault. Also holds the off-device backup controls. |
| **Vault** | Enter your passphrase to decrypt and open captures/imports on this device. |

## Encryption design

The keystone is `crypto/FileCrypto` + `crypto/KeyVault` (pure JVM, unit-tested):

- **Per-file streaming hybrid.** A fresh data key is generated per file, the
  payload is encrypted with Tink `StreamingAead` (1 MB segments, constant
  memory), and the data key is sealed to the **public key** with HPKE. So
  encryption needs no secret on the device, and it works the same for a selfie,
  a photo, or a **multi-gigabyte video**.
- **Passphrase-wrapped private key.** The private key is wrapped with
  PBKDF2-HMAC-SHA256 + AES-256-GCM under your passphrase (`KeyVault`), using
  only standard JCE algorithms so other tools can reproduce it. The wrapped key
  is exported at setup for off-phone backup; the passphrase is never stored.

Container formats (`.sgc` captures/imports, `.sgk` wrapped key) are documented
at the top of `tools/decrypt/snoopguard_decrypt.py`.

### Does it work on video?

Yes. The streaming design means an MP4 encrypts and decrypts exactly like a
JPEG; the crypto never holds the whole file in memory. The decryptor self-test
round-trips a payload larger than the streaming segment to prove it. Capturing a
short *clip* on unlock (instead of a still) is a UI follow-up; encrypting and
backing up video through the Import tab works today.

## Viewing your encrypted media (three ways)

1. **In-app Vault tab.** Passphrase → private key unwrapped in memory (wiped on
   leave) → tap an item to decrypt it to a cleared cache dir and open it in the
   system viewer (images and video). Convenient; protected by the passphrase a
   snooper doesn't know.
2. **Laptop decryptor** (`tools/decrypt/`). A Python CLI that decrypts `.sgc`
   files with the exported `.sgk` key + passphrase, so the private key never
   touches the phone. Strongest option. Has its own README and self-test.
3. **Companion viewer app** (follow-up, see below). A second-device app with a
   gallery UI, reusing the same crypto core.

## Off-device backup

The Import tab's backup section copies encrypted `.sgc` files into a folder you
pick via the Storage Access Framework. Point it at a folder a cloud app syncs
(Drive, Dropbox, …) and the ciphertext rides that sync off the device. Captures
auto-export right after they're encrypted, so deleting one on the phone doesn't
erase the evidence.

## Known Android constraints (by design, not bugs)

- **Green dot.** Android 12+ shows a camera indicator on every capture. It
  can't be hidden; keep bursts short, treat it as a deterrent.
- **Persistent notification.** Foreground services must show one. It can be
  quiet but not removed.
- **Arming is foreground-only.** Android 14 blocks background-started camera
  services; Android 15 blocks starting one at boot. After a reboot the app stays
  disarmed until reopened — the recorded gap is the signal.
- **Camera toggle.** The Quick Settings camera toggle yields black frames; the
  face gate discards these and the event log notes the miss.
- **No unlocker identity.** Android does not tell apps who unlocked. Either arm
  manually or (follow-up) teach it to skip the owner's own face.

## Follow-ups (not yet implemented)

1. **Direct Google Drive upload** with a write-only, public-key-encrypted path
   (needs the user's OAuth client ID; can't be CI-tested). The SAF export is the
   dependency-free stand-in.
2. **WorkManager retry queue** so backups survive no-signal and process death.
3. **Companion viewer app** (Viewer 3): a standalone second-device app that
   holds the private key, reads from the cloud folder, and shows a gallery.
   Reuses `crypto/` verbatim; mostly UI + a cloud read.
4. **App lock** (separate PIN/biometric) gating disarm and the vault list.
5. **Owner face-skip** via an on-device embedding model (MobileFaceNet/TFLite)
   so it can stay armed all the time.
6. **Snoop report**: pair each selfie with the apps opened during the session
   (`UsageStatsManager`).
7. **Video capture on unlock** (short clip instead of a still).
8. **Cross-language crypto vector in CI**: have the Android build emit a `.sgc`
   for `tools/decrypt/selftest.py` to decrypt, proving Java↔Python parity.

## Build

```bash
cd SnoopGuardApp
./gradlew testDebugUnitTest   # crypto-core JVM unit tests
./gradlew assembleDebug       # app/build/outputs/apk/debug/app-debug.apk
```

CI (`.github/workflows/build-snoopguard-apk.yml`) runs the tests and builds the
APK on every push touching `SnoopGuardApp/**`; download it from the run's
**Artifacts** section and `adb install app-debug.apk`.

- Package: `io.github.phillipdpiris.snoopguard`
- minSdk 26 · targetSdk 35 · Kotlin 2.2.21 · AGP 8.10.1 · Tink 1.18.0
