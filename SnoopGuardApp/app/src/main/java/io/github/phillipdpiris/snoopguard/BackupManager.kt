package io.github.phillipdpiris.snoopguard

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.documentfile.provider.DocumentFile

/**
 * Copies the encrypted `.sgc` files (captures + imports) into a folder the user
 * picks through the Storage Access Framework. Point it at a folder that a cloud
 * app syncs (Drive, Dropbox, …) and the backup rides that sync off the device.
 *
 * Because the files are already encrypted to the public key, the destination —
 * and anyone who can read it — only ever sees ciphertext. That is the whole
 * point: a breach of the backup location (the Tea-breach scenario) leaks
 * nothing.
 *
 * This is the v1 off-device path. A WorkManager-backed retry queue and a direct
 * Google Drive API uploader (write-only credential, needs the user's OAuth
 * client ID) are documented follow-ups in the README.
 */
class BackupManager(private val context: Context) {

    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var treeUri: Uri?
        get() = prefs.getString(KEY_TREE, null)?.let(Uri::parse)
        private set(value) = prefs.edit().putString(KEY_TREE, value?.toString()).apply()

    fun isConfigured(): Boolean = treeUri != null

    /** Persist the folder the user picked, keeping access across reboots. */
    fun persistTree(uri: Uri) {
        val flags = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        try {
            context.contentResolver.takePersistableUriPermission(uri, flags)
        } catch (_: SecurityException) {
            // Some providers don't grant persistable permission; the URI may
            // still work for this session.
        }
        treeUri = uri
    }

    /**
     * Copies any `.sgc` not already present (by name) in the backup folder.
     * Safe to call repeatedly; returns how many new files were copied.
     * Call off the main thread.
     */
    fun exportAll(): Int {
        val tree = treeUri ?: return 0
        val root = DocumentFile.fromTreeUri(context, tree) ?: return 0
        if (!root.canWrite()) return 0

        val files = CaptureStore(context).listCaptures() + ImportStore(context).listImports()
        var copied = 0
        for (f in files) {
            if (root.findFile(f.name) != null) continue
            val doc = root.createFile("application/octet-stream", f.name) ?: continue
            try {
                context.contentResolver.openOutputStream(doc.uri)?.use { out ->
                    f.inputStream().use { it.copyTo(out) }
                } ?: run { doc.delete() }
                copied++
            } catch (t: Throwable) {
                doc.delete()
            }
        }
        return copied
    }

    companion object {
        private const val PREFS = "snoopguard_backup"
        private const val KEY_TREE = "tree_uri"
    }
}
