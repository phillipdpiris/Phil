# SnoopGuard (prototype)

An Android anti-snoop app. Once **armed**, it takes a front-camera selfie every
time the phone is **woken or unlocked**, so the owner can see who has been using
their device. Unlike the common "intruder selfie" apps (Third Eye, Lockwatch,
CrookCatcher), which fire only on a *failed* unlock, SnoopGuard triggers on
*every* unlock while armed — catching the snooper who already knows the PIN.

> Status: early scaffold. The capture pipeline, arming, Quick Settings tile,
> boot handling and log-only mode are implemented. Off-device upload, owner
> face-skipping, and the app lock are stubbed as follow-ups (see below).

## What it is / is not

This is a **device-owner tool**: you install it on *your own* phone to find out
who is using it. It follows Google Play's stalkerware/deceptive-behaviour rules:

- the app icon is always visible — no disguises;
- while armed, a foreground-service notification is always shown;
- it only ever watches the phone it is installed on.

It is **not** covert surveillance of someone else's phone, and it deliberately
cannot be hidden.

## How it works

| Piece | File | Role |
|-------|------|------|
| Arm/disarm + history UI | `MainActivity.kt` | Requests camera/notification permission, arms, lists captures |
| Quick Settings tile | `ArmTileService.kt` | Arm/disarm from the shade (counts as a foreground start) |
| Watch service | `WatchService.kt` | Camera-type foreground service; listens for `SCREEN_ON` / `USER_PRESENT` |
| Capture | `SelfieCapturer.kt` | Headless CameraX single-shot from the front camera |
| Face gate | `FaceGate.kt` | ML Kit face detection — discards frames with no face |
| Storage | `CaptureStore.kt` | Saves JPEGs + an append-only event log in private storage |
| Boot handling | `BootReceiver.kt` | Records a reboot-while-armed and disarms (can't re-arm camera at boot) |
| State | `ArmState.kt` | Armed flag + log-only mode |

### Log-only (silent) mode

Records *when* the phone was unlocked without ever opening the camera, so there
is no camera indicator. Intended for the case where a visible green dot could
escalate a situation (e.g. a controlling partner) but the owner still wants to
know what happened.

## Known Android constraints (by design, not bugs)

- **Green dot.** Android 12+ shows a camera indicator on every capture. It
  cannot be hidden; keep bursts short and treat it as a deterrent.
- **Persistent notification.** Foreground services must show one. It can be
  quiet (`IMPORTANCE_LOW`) but not removed.
- **Arming is foreground-only.** Android 14 blocks background-started camera
  services; Android 15 blocks starting one at boot. After a reboot the app stays
  disarmed until reopened — the recorded gap is itself the signal.
- **Camera toggle.** The Quick Settings camera toggle yields black frames; the
  face gate discards these and the event log notes the miss.
- **No unlocker identity.** Android does not tell apps who unlocked. Either arm
  manually or (follow-up) teach it to skip the owner's own face.

## Follow-ups (not yet implemented)

1. **Off-device upload** of each capture (owner email / private cloud / the
   encrypted-vault idea) so a snooper holding the phone can't delete the
   evidence.
2. **App lock** (separate PIN/biometric) gating disarm and history.
3. **Owner face-skip** via an on-device embedding model (MobileFaceNet / TFLite)
   so it can stay armed all the time.
4. **Snoop report**: pair each selfie with the apps opened during the session
   using `UsageStatsManager` (needs the Usage Access special permission).
5. **Wear OS companion**: buzz the watch when the phone is unlocked while armed.

## Build

A full build needs the Android SDK, which this project pulls on first build.

```bash
cd SnoopGuardApp
./gradlew testDebugUnitTest   # pure-logic unit tests
./gradlew assembleDebug       # outputs app/build/outputs/apk/debug/app-debug.apk
```

CI builds it on every push touching `SnoopGuardApp/**`
(`.github/workflows/build-snoopguard-apk.yml`); download the APK from the run's
**Artifacts** section and `adb install app-debug.apk`.

- Package: `io.github.phillipdpiris.snoopguard`
- minSdk 26 · targetSdk 35 · Kotlin 2.2.21 · AGP 8.10.1
