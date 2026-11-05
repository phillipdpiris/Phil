package io.github.phillipdpiris.snoopguard

import android.app.Notification
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import io.github.phillipdpiris.snoopguard.crypto.FileCrypto
import io.github.phillipdpiris.snoopguard.crypto.KeyManager
import java.io.File
import java.util.concurrent.Executors

// BackupManager is in the same package; no import needed.

/**
 * Foreground, camera-type service. While armed it listens for the screen turning
 * on (ACTION_SCREEN_ON) and for unlock (ACTION_USER_PRESENT) and captures a
 * front-camera selfie on each, unless in log-only (silent) mode.
 *
 * Each selfie is encrypted to the public key before it touches persistent
 * storage: the camera writes a transient JPEG to the cache, the face check runs
 * on it, and it is encrypted to a `.sgc` file and the plaintext deleted. The
 * service never holds anything that could decrypt a capture.
 *
 * It is a [LifecycleService] so CameraX can bind to its lifecycle.
 */
class WatchService : LifecycleService() {

    private lateinit var store: CaptureStore
    private lateinit var armState: ArmState
    private lateinit var keyManager: KeyManager
    private var capturer: SelfieCapturer? = null
    private var faceGate: FaceGate? = null
    private var publicKeyset: ByteArray? = null
    private val ioExecutor = Executors.newSingleThreadExecutor()

    private val screenReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                Intent.ACTION_USER_PRESENT -> onTrigger("unlock")
                Intent.ACTION_SCREEN_ON -> onTrigger("screen_on")
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        store = CaptureStore(this)
        armState = ArmState(this)
        keyManager = KeyManager(this)
        registerReceiver(
            screenReceiver,
            IntentFilter().apply {
                addAction(Intent.ACTION_SCREEN_ON)
                addAction(Intent.ACTION_USER_PRESENT)
            },
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        startForegroundSafely()
        // Idempotent: a START_STICKY redelivery must not bind the camera twice.
        if (!armState.silent && capturer == null) {
            if (keyManager.isSetup()) {
                publicKeyset = keyManager.publicKeyset()
                faceGate = FaceGate()
                capturer = SelfieCapturer(this, this).also { it.start() }
            } else {
                // Armed (e.g. from the Quick Settings tile) before a key exists:
                // we can log unlocks but must not capture, since there is no key
                // to encrypt to. The user finishes setup by opening the app.
                store.appendEvent("armed_without_key\tcapture_disabled")
            }
        }
        return START_STICKY
    }

    private fun onTrigger(reason: String) {
        if (!armState.armed) return
        store.appendEvent("trigger\t$reason")
        if (armState.silent) return

        val cap = capturer
        val pub = publicKeyset
        if (cap == null || pub == null) {
            store.appendEvent("capture_skipped_no_key\t$reason")
            return
        }

        val ts = System.currentTimeMillis()
        val tmp = store.newTempJpeg(ts)
        cap.capture(tmp) { ok ->
            if (!ok) {
                store.appendEvent("capture_failed\t$reason")
                tmp.delete()
                return@capture
            }
            // Keep only frames that actually contain a face, then encrypt.
            faceGate?.hasFace(this, tmp) { face ->
                if (!face) {
                    tmp.delete()
                    store.appendEvent("capture_discarded_no_face\t$reason")
                } else {
                    encryptAndStore(tmp, ts, reason, pub)
                }
            } ?: encryptAndStore(tmp, ts, reason, pub)
        }
    }

    /** Encrypts the transient JPEG to a `.sgc` file off the main thread, then deletes it. */
    private fun encryptAndStore(tmp: File, ts: Long, reason: String, pub: ByteArray) {
        ioExecutor.execute {
            val target = store.newCaptureFile(ts)
            try {
                tmp.inputStream().use { input ->
                    target.outputStream().use { out ->
                        FileCrypto.encrypt(pub, input, out)
                    }
                }
                store.appendEvent("capture_saved\t${target.name}")
                // Push the new encrypted capture off-device promptly, so a
                // snooper who deletes it on the phone doesn't erase the evidence.
                val backup = BackupManager(applicationContext)
                if (backup.isConfigured()) {
                    try {
                        backup.exportAll()
                    } catch (t: Throwable) {
                        store.appendEvent("backup_failed\t${t.message}")
                    }
                }
            } catch (t: Throwable) {
                target.delete()
                store.appendEvent("capture_encrypt_failed\t${t.message}")
                Log.w("SnoopGuard", "encrypt failed: ${t.message}")
            } finally {
                tmp.delete()
            }
        }
    }

    private fun startForegroundSafely() {
        val notification: Notification = NotificationCompat.Builder(this, SnoopGuardApp.CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_shield)
            .setContentTitle(getString(R.string.notif_title))
            .setContentText(getString(R.string.notif_text))
            .setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA)
        } else {
            startForeground(NOTIF_ID, notification)
        }
    }

    override fun onDestroy() {
        try {
            unregisterReceiver(screenReceiver)
        } catch (t: Throwable) {
            Log.w("SnoopGuard", "receiver already gone: ${t.message}")
        }
        capturer?.stop()
        faceGate?.close()
        ioExecutor.shutdown()
        super.onDestroy()
    }

    override fun onBind(intent: Intent): IBinder? {
        super.onBind(intent)
        return null
    }

    companion object {
        private const val NOTIF_ID = 1001

        fun start(context: Context) {
            val intent = Intent(context, WatchService::class.java)
            context.startForegroundService(intent)
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, WatchService::class.java))
        }
    }
}
