package io.github.phillipdpiris.snoopguard

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import io.github.phillipdpiris.snoopguard.crypto.FileCrypto
import io.github.phillipdpiris.snoopguard.crypto.KeyManager
import io.github.phillipdpiris.snoopguard.crypto.KeyVault
import io.github.phillipdpiris.snoopguard.databinding.FragmentVaultBinding
import java.io.File
import java.util.concurrent.Executors

/**
 * Viewer 1: the in-app review tab. Enter the passphrase, which unwraps the
 * private key in memory (never stored); tapping an item decrypts it to a cache
 * file and opens it in the system viewer, which handles both images and video.
 *
 * Note: decrypting on the watched phone is the convenient option, protected by
 * the passphrase a snooper doesn't know. The laptop decryptor keeps the private
 * key off the phone entirely for a stronger guarantee.
 */
class VaultFragment : Fragment() {

    private var _binding: FragmentVaultBinding? = null
    private val binding get() = _binding!!

    private lateinit var keyManager: KeyManager
    private lateinit var appCtx: Context
    private val ioExecutor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    /** Held only while the tab is open; wiped in onDestroyView. */
    private var privateKeyset: ByteArray? = null

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        _binding = FragmentVaultBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        keyManager = KeyManager(requireContext())
        appCtx = requireContext().applicationContext

        binding.vaultList.layoutManager = LinearLayoutManager(requireContext())

        binding.unlockButton.setOnClickListener {
            if (!keyManager.isSetup()) {
                toast(getString(R.string.vault_no_key))
                return@setOnClickListener
            }
            val pass = binding.vaultPassphrase.text?.toString().orEmpty().toCharArray()
            if (pass.isEmpty()) return@setOnClickListener
            unlock(pass)
        }
    }

    private fun unlock(pass: CharArray) {
        binding.unlockButton.isEnabled = false
        ioExecutor.execute {
            val keyset = try {
                keyManager.loadPrivateKeyset(pass)
            } catch (e: KeyVault.BadPassphraseException) {
                null
            } finally {
                pass.fill('\u0000')
            }
            main.post {
                if (!isAdded || _binding == null) return@post
                binding.unlockButton.isEnabled = true
                if (keyset == null) {
                    toast(getString(R.string.vault_wrong_passphrase))
                } else {
                    privateKeyset = keyset
                    clearDecryptCache()
                    showUnlocked()
                }
            }
        }
    }

    private fun showUnlocked() {
        binding.lockSection.visibility = View.GONE
        binding.vaultPassphrase.text?.clear()

        val items = CaptureStore(requireContext()).listCaptures() +
            ImportStore(requireContext()).listImports()
        val sorted = items.sortedByDescending { it.lastModified() }

        if (sorted.isEmpty()) {
            binding.vaultStatus.visibility = View.VISIBLE
            binding.vaultStatus.setText(R.string.vault_empty)
        } else {
            binding.vaultStatus.visibility = View.VISIBLE
            binding.vaultStatus.setText(R.string.vault_unlocked_hint)
            binding.vaultList.visibility = View.VISIBLE
            binding.vaultList.adapter = CapturesAdapter(sorted, R.string.vault_item) { openItem(it) }
        }
    }

    private fun openItem(file: File) {
        val keyset = privateKeyset ?: return
        ioExecutor.execute {
            val outFile = try {
                val dir = File(appCtx.cacheDir, "vault_open").apply { mkdirs() }
                val tmp = File(dir, file.nameWithoutExtension)
                file.inputStream().use { inp ->
                    tmp.outputStream().use { out -> FileCrypto.decrypt(keyset, inp, out) }
                }
                addExtension(tmp)
            } catch (t: Throwable) {
                null
            }
            main.post {
                if (!isAdded) return@post
                if (outFile == null) toast(getString(R.string.vault_open_failed))
                else viewExternally(outFile)
            }
        }
    }

    private fun viewExternally(file: File) {
        val uri = FileProvider.getUriForFile(appCtx, "${appCtx.packageName}.fileprovider", file)
        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, mimeFor(file))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        try {
            startActivity(intent)
        } catch (t: Throwable) {
            toast(getString(R.string.vault_open_failed))
        }
    }

    /** Renames the decrypted temp file to carry an extension sniffed from its bytes. */
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

    private fun clearDecryptCache() {
        File(appCtx.cacheDir, "vault_open").listFiles()?.forEach { it.delete() }
    }

    private fun toast(message: String) =
        Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show()

    override fun onDestroyView() {
        super.onDestroyView()
        privateKeyset?.fill(0)
        privateKeyset = null
        clearDecryptCache()
        _binding = null
    }

    override fun onDestroy() {
        super.onDestroy()
        ioExecutor.shutdown()
    }
}
