package io.github.phillipdpiris.snoopguardviewer

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Base64
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.documentfile.provider.DocumentFile
import androidx.recyclerview.widget.LinearLayoutManager
import io.github.phillipdpiris.snoopguardviewer.crypto.FileCrypto
import io.github.phillipdpiris.snoopguardviewer.crypto.KeyVault
import io.github.phillipdpiris.snoopguardviewer.databinding.ActivityMainBinding
import java.io.File
import java.util.concurrent.Executors

/**
 * Companion viewer (Viewer 3). A standalone second-device app: load the exported
 * wrapped key (.sgk), enter the passphrase, point it at the synced vault folder,
 * and browse/open the encrypted .sgc files. The private key is unwrapped in
 * memory only and never written to this device.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    private var wrappedKey: ByteArray? = null
    private var treeUri: Uri? = null
    private var privateKeyset: ByteArray? = null

    private val loadKey = registerForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri == null) return@registerForActivityResult
        val bytes = try {
            contentResolver.openInputStream(uri)?.use { it.readBytes() }
        } catch (t: Throwable) {
            null
        }
        if (bytes == null) {
            toast(getString(R.string.key_load_failed))
        } else {
            wrappedKey = bytes
            prefs().edit().putString(KEY_WRAPPED, Base64.encodeToString(bytes, Base64.NO_WRAP)).apply()
            renderState()
        }
    }

    private val chooseFolder = registerForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        if (uri == null) return@registerForActivityResult
        try {
            contentResolver.takePersistableUriPermission(
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION,
            )
        } catch (_: SecurityException) {
        }
        treeUri = uri
        prefs().edit().putString(KEY_TREE, uri.toString()).apply()
        renderState()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.entriesList.layoutManager = LinearLayoutManager(this)

        // Restore remembered key + folder (the wrapped key is useless without the passphrase).
        prefs().getString(KEY_WRAPPED, null)?.let { wrappedKey = Base64.decode(it, Base64.NO_WRAP) }
        prefs().getString(KEY_TREE, null)?.let { treeUri = Uri.parse(it) }

        binding.loadKeyButton.setOnClickListener { loadKey.launch(arrayOf("*/*")) }
        binding.chooseFolderButton.setOnClickListener { chooseFolder.launch(null) }
        binding.unlockButton.setOnClickListener { unlock() }

        renderState()
    }

    private fun unlock() {
        val key = wrappedKey ?: run { toast(getString(R.string.need_key)); return }
        val tree = treeUri ?: run { toast(getString(R.string.need_folder)); return }
        val pass = binding.passphrase.text?.toString().orEmpty().toCharArray()
        if (pass.isEmpty()) return

        binding.unlockButton.isEnabled = false
        io.execute {
            val keyset = try {
                KeyVault.unwrap(key, pass)
            } catch (e: KeyVault.BadPassphraseException) {
                null
            } finally {
                pass.fill('\u0000')
            }
            val entries = if (keyset != null) listEntries(tree) else emptyList()
            main.post {
                binding.unlockButton.isEnabled = true
                if (keyset == null) {
                    toast(getString(R.string.wrong_passphrase))
                } else {
                    privateKeyset = keyset
                    binding.passphrase.text?.clear()
                    showEntries(entries)
                }
            }
        }
    }

    private fun listEntries(tree: Uri): List<DocumentFile> {
        val root = DocumentFile.fromTreeUri(this, tree) ?: return emptyList()
        return root.listFiles()
            .filter { it.isFile && (it.name?.endsWith(".sgc") == true) }
            .sortedByDescending { it.lastModified() }
    }

    private fun showEntries(entries: List<DocumentFile>) {
        binding.status.text = if (entries.isEmpty()) {
            getString(R.string.vault_empty)
        } else {
            getString(R.string.unlocked_hint)
        }
        binding.entriesList.adapter = VaultAdapter(entries) { openEntry(it) }
    }

    private fun openEntry(doc: DocumentFile) {
        val keyset = privateKeyset ?: return
        val name = doc.name ?: "item"
        io.execute {
            val out = try {
                val dir = File(cacheDir, "open").apply { mkdirs() }
                val tmp = File(dir, name.removeSuffix(".sgc"))
                contentResolver.openInputStream(doc.uri)?.use { input ->
                    tmp.outputStream().use { o -> FileCrypto.decrypt(keyset, input, o) }
                } ?: return@execute
                addExtension(tmp)
            } catch (t: Throwable) {
                null
            }
            main.post {
                if (out == null) toast(getString(R.string.open_failed)) else viewExternally(out)
            }
        }
    }

    private fun viewExternally(file: File) {
        val uri = FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, mimeFor(file))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        try {
            startActivity(intent)
        } catch (t: Throwable) {
            toast(getString(R.string.open_failed))
        }
    }

    private fun addExtension(file: File): File {
        val head = ByteArray(12)
        val n = file.inputStream().use { it.read(head) }
        val ext = when {
            n >= 3 && head[0] == 0xFF.toByte() && head[1] == 0xD8.toByte() && head[2] == 0xFF.toByte() -> "jpg"
            n >= 8 && head[0] == 0x89.toByte() && head[1] == 0x50.toByte() -> "png"
            n >= 8 && head[4] == 'f'.code.toByte() && head[5] == 't'.code.toByte() &&
                head[6] == 'y'.code.toByte() && head[7] == 'p'.code.toByte() -> "mp4"
            else -> return file
        }
        val renamed = File(file.parentFile, "${file.name}.$ext")
        return if (file.renameTo(renamed)) renamed else file
    }

    private fun mimeFor(file: File): String = when (file.extension.lowercase()) {
        "jpg", "jpeg" -> "image/jpeg"
        "png" -> "image/png"
        "mp4" -> "video/mp4"
        else -> "application/octet-stream"
    }

    private fun renderState() {
        val haveKey = wrappedKey != null
        val haveFolder = treeUri != null
        binding.keyStatus.setText(if (haveKey) R.string.key_loaded else R.string.key_none)
        binding.folderStatus.setText(if (haveFolder) R.string.folder_set else R.string.folder_none)
        binding.unlockButton.isEnabled = haveKey && haveFolder
    }

    private fun prefs() = getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_LONG).show()

    override fun onDestroy() {
        super.onDestroy()
        privateKeyset?.fill(0)
        privateKeyset = null
        File(cacheDir, "open").listFiles()?.forEach { it.delete() }
        io.shutdown()
    }

    companion object {
        private const val PREFS = "viewer"
        private const val KEY_WRAPPED = "wrapped_key"
        private const val KEY_TREE = "tree_uri"
    }
}
