package io.github.phillipdpiris.snoopguard

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * A reboot while armed is itself worth noting: it is one way to stop the watch.
 *
 * Android 15 forbids starting a camera-type foreground service from
 * BOOT_COMPLETED, so we deliberately do NOT re-arm here. Instead we record the
 * reboot and clear the armed flag; the user re-arms by opening the app. The
 * recorded gap is the signal.
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val armState = ArmState(context)
        if (armState.armed) {
            CaptureStore(context).appendEvent("reboot_while_armed\twatch_stopped_until_reopened")
            armState.armed = false
        }
    }
}
