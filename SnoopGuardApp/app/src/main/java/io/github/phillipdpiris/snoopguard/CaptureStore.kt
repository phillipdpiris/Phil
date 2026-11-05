package io.github.phillipdpiris.snoopguard

import android.content.Context
import java.io.File

/**
 * Stores captures and the unlock log in the app's private internal storage.
 *
 * NOTE (threat model): a snooper holding the unlocked phone could open this app
 * and delete these files, or uninstall the app. A real deployment should push each
 * capture off-device immediately (the owner's email or private cloud) and gate
 * disarm/history behind a separate app lock. Those are deliberately left as
 * follow-ups; see README.
 */
class CaptureStore(context: Context) {

    private val dir = File(context.filesDir, "captures").apply { mkdirs() }
    private val logFile = File(context.filesDir, "events.log")

    fun newCaptureFile(timestampMs: Long): File = File(dir, "capture_$timestampMs.jpg")

    /** Captures, newest first. */
    fun listCaptures(): List<File> =
        dir.listFiles { f -> f.extension == "jpg" }
            ?.sortedByDescending { it.lastModified() }
            ?: emptyList()

    fun appendEvent(line: String) {
        logFile.appendText(formatLogLine(line) + "\n")
    }

    fun readLog(): String = if (logFile.exists()) logFile.readText() else ""

    companion object {
        /** Prefixes each entry with a sortable epoch-millis stamp. Pure for testing. */
        fun formatLogLine(line: String, nowMs: Long = System.currentTimeMillis()): String =
            "$nowMs\t$line"
    }
}
