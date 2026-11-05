package io.github.phillipdpiris.snoopguard

import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import io.github.phillipdpiris.snoopguard.crypto.FileCrypto
import io.github.phillipdpiris.snoopguard.crypto.KeyManager
import java.util.concurrent.Executors

/**
 * Pick photos or videos and encrypt them into the vault with the same public
 * key as captures. The plaintext is streamed straight from the picker URI into
 * the encryptor, so this app never writes the originals in the clear.
 */
class ImportFragment : Fragment() {

    private var _binding: io.github.phillipdpiris.snoopguard.databinding.FragmentImportBinding? = null
    private val binding get() = _binding!!

    private lateinit var keyManager: KeyManager
    private lateinit var importStore: ImportStore
    private lateinit var backupManager: BackupManager
    private val adapter = CapturesAdapter(emptyList(), R.string.import_locked)
    private val ioExecutor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    private val pickMedia = registerForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(20),
    ) { uris -> if (uris.isNotEmpty()) encryptAll(uris) }

    private val chooseBackup = registerForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        if (uri != null) {
            backupManager.persistTree(uri)
            renderBackupStatus()
            toast(getString(R.string.backup_folder_set))
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        _binding = io.github.phillipdpiris.snoopguard.databinding.FragmentImportBinding
            .inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        keyManager = KeyManager(requireContext())
        importStore = ImportStore(requireContext())
        backupManager = BackupManager(requireContext().applicationContext)

        binding.importsList.layoutManager = LinearLayoutManager(requireContext())
        binding.importsList.adapter = adapter

        binding.pickButton.setOnClickListener {
            if (!keyManager.isSetup()) {
                toast(getString(R.string.import_need_key))
            } else {
                pickMedia.launch(
                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageAndVideo),
                )
            }
        }

        binding.chooseBackupButton.setOnClickListener { chooseBackup.launch(null) }
        binding.backupNowButton.setOnClickListener { backupNow() }
        renderBackupStatus()
    }

    private fun backupNow() {
        if (!backupManager.isConfigured()) {
            toast(getString(R.string.backup_not_configured))
            return
        }
        ioExecutor.execute {
            val n = try {
                backupManager.exportAll()
            } catch (t: Throwable) {
                -1
            }
            main.post {
                if (!isAdded) return@post
                toast(if (n >= 0) getString(R.string.backup_done, n) else getString(R.string.vault_open_failed))
            }
        }
    }

    private fun renderBackupStatus() {
        val b = _binding ?: return
        b.backupStatus.setText(if (backupManager.isConfigured()) R.string.backup_folder_set else R.string.backup_none)
    }

    override fun onResume() {
        super.onResume()
        render()
    }

    private fun encryptAll(uris: List<Uri>) {
        val pub = keyManager.publicKeyset()
        val resolver = requireContext().contentResolver
        val ts = System.currentTimeMillis()
        setStatus(getString(R.string.importing, uris.size))
        ioExecutor.execute {
            var ok = 0
            uris.forEachIndexed { i, uri ->
                val target = importStore.newImportFile(ts, i)
                try {
                    resolver.openInputStream(uri)?.use { input ->
                        target.outputStream().use { out -> FileCrypto.encrypt(pub, input, out) }
                    } ?: return@forEachIndexed
                    ok++
                } catch (t: Throwable) {
                    target.delete()
                }
            }
            // Push the new encrypted files off-device if a backup folder is set.
            if (backupManager.isConfigured()) {
                try {
                    backupManager.exportAll()
                } catch (_: Throwable) {
                }
            }
            main.post {
                if (!isAdded || _binding == null) return@post
                setStatus(getString(R.string.imported_done, ok))
                render()
            }
        }
    }

    private fun render() {
        val b = _binding ?: return
        val items = importStore.listImports()
        adapter.submit(items)
        b.emptyText.visibility = if (items.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun setStatus(text: String) {
        val b = _binding ?: return
        b.importStatus.visibility = View.VISIBLE
        b.importStatus.text = text
    }

    private fun toast(message: String) =
        Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show()

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    override fun onDestroy() {
        super.onDestroy()
        ioExecutor.shutdown()
    }
}
