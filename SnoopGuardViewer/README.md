# SnoopGuard Viewer (companion app)

Viewer 3 for [SnoopGuard](../SnoopGuardApp): a standalone app you install on a
**second device** to browse and open the encrypted captures and imports, with
the private key never touching the watched phone.

## How it works

1. **Load key file** — the `snoopguard-private-key.sgk` you exported during
   setup on the phone (copy it to this device). It's the passphrase-wrapped
   private key; useless without the passphrase, so the app remembers it.
2. **Choose vault folder** — point it (via the system folder picker) at the
   synced folder that holds the `.sgc` files, i.e. the same cloud folder the
   phone's off-device backup writes to.
3. **Unlock & list** — enter your passphrase; the private key is unwrapped in
   memory (never stored), and the `.sgc` files are listed.
4. **Tap an item** — it's decrypted to a cleared cache dir and opened in the
   system viewer (images and video alike).

## Relationship to the main app

This reuses the **exact** container formats, so files written by the phone
decrypt here:

- `crypto/FileCrypto.kt` and `crypto/KeyVault.kt` are byte-for-byte copies of
  the app's versions (same magic, associated data, templates, PBKDF2 params).

They are duplicated rather than shared through a Gradle module to keep the two
apps independent for now; factoring the crypto into a shared `:crypto` module
both apps depend on is a sensible later refactor.

## Scope / follow-ups

This is a minimal viewer scaffold. Not yet built: thumbnails/grid, in-app media
playback (it hands off to the system viewer), search, and a shared crypto
module. It has not been hand-tested on a device; CI builds it and runs the
crypto round-trip tests.

## Build

```bash
cd SnoopGuardViewer
./gradlew testDebugUnitTest
./gradlew assembleDebug   # app/build/outputs/apk/debug/app-debug.apk
```

- Package: `io.github.phillipdpiris.snoopguardviewer`
- minSdk 26 · targetSdk 35 · Kotlin 2.2.21 · AGP 8.10.1 · Tink 1.18.0
