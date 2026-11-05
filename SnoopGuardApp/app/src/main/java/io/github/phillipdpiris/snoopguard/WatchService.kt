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

/**
 * Foreground, camera-type service. While armed it listens for the screen turning
 * on (ACTION_SCREEN_ON) and for unlock (ACTION_USER_PRESENT) and captures a
 * front-camera selfie on each, unless in log-only (silent) mode.
 *
 * It is a [LifecycleService] so CameraX can bind to its lifecycle.
 */
class WatchService : LifecycleService() {

    private lateinit var store: CaptureStore
    private lateinit var armState: ArmState
    private var capturer: SelfieCapturer? = null
    private var faceGate: FaceGate? = null

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
            faceGate = FaceGate()
            capturer = SelfieCapturer(this, this).also { it.start() }
        }
        return START_STICKY
    }

    private fun onTrigger(reason: String) {
        if (!armState.armed) return
        store.appendEvent("trigger\t$reason")
        if (armState.silent) return

        val cap = capturer ?: return
        val target = store.newCaptureFile(System.currentTimeMillis())
        cap.capture(target) { ok ->
            if (!ok) {
                store.appendEvent("capture_failed\t$reason")
                return@capture
            }
            // Keep only frames that actually contain a face.
            faceGate?.hasFace(this, target) { face ->
                if (face) {
                    store.appendEvent("capture_saved\t${target.name}")
                } else {
                    target.delete()
                    store.appendEvent("capture_discarded_no_face\t$reason")
                }
            } ?: store.appendEvent("capture_saved\t${target.name}")
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
