package io.github.phillipdpiris.snoopguard

import android.content.Context
import java.io.File

/**
 * Stores captures and the unlock log in the app's private internal storage.
 *
 * Captures are written as encrypted `.sgc` files (see
 * [io.github.phillipdpiris.snoopguard.crypto.FileCrypto]); the plaintext JPEG
 * exists only transiently in [tmpDir] while the camera writes it and the face
 * check runs, and is deleted immediately after encryption.
 *
 * NOTE (threat model): a snooper holding the unlocked phone could open this app
 * and delete these files, or uninstall the app. Because the files are encrypted
 * to a public key, they can't read them — but they could still delete them. The
 * off-device backup (follow-up) copies each `.sgc` out so deletion here is not
 * the last word.
 */
class CaptureStore(context: Context) {

    private val dir = File(context.filesDir, "captures").apply { mkdirs() }
    private val tmpDir = File(context.cacheDir, "cap_tmp").apply { mkdirs() }
    private val logFile = File(context.filesDir, "events.log")

    /** Transient plaintext target the camera writes to, before encryption. */
    fun newTempJpeg(timestampMs: Long): File = File(tmpDir, "tmp_$timestampMs.jpg")

    /** Encrypted capture target. */
    fun newCaptureFile(timestampMs: Long): File = File(dir, "capture_$timestampMs.sgc")

    /** Encrypted captures, newest first. */
    fun listCaptures(): List<File> =
        dir.listFiles { f -> f.extension == "sgc" }
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
