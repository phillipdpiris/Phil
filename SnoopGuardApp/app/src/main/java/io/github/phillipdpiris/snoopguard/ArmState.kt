package io.github.phillipdpiris.snoopguard

import android.content.Context

/**
 * Persists whether the watch is armed and which mode it runs in.
 *
 * Arming is deliberately a foreground, user-initiated action: since Android 14 a
 * service started from the background may not open the camera, so the app can only
 * begin watching while the user has it in the foreground (the activity or the
 * Quick Settings tile).
 */
class ArmState(context: Context) {

    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var armed: Boolean
        get() = prefs.getBoolean(KEY_ARMED, false)
        set(value) = prefs.edit().putBoolean(KEY_ARMED, value).apply()

    /** Log-only: record unlock events but never open the camera (no green dot). */
    var silent: Boolean
        get() = prefs.getBoolean(KEY_SILENT, false)
        set(value) = prefs.edit().putBoolean(KEY_SILENT, value).apply()

    companion object {
        private const val PREFS = "snoopguard_state"
        private const val KEY_ARMED = "armed"
        private const val KEY_SILENT = "silent"
    }
}
