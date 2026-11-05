package io.github.phillipdpiris.snoopguard

import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import io.github.phillipdpiris.snoopguard.crypto.KeyManager
import io.github.phillipdpiris.snoopguard.databinding.ActivitySetupBinding

/**
 * One-time key setup. Generates the key pair, stores the public key and the
 * passphrase-wrapped private key, then offers to export the wrapped private key
 * so it can be backed up off the phone (needed, with the passphrase, by the
 * laptop decryptor and the companion viewer).
 */
class SetupActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySetupBinding
    private lateinit var keyManager: KeyManager
    private var pendingWrapped: ByteArray? = null

    private val exportKey = registerForActivityResult(
        ActivityResultContracts.CreateDocument("application/octet-stream"),
    ) { uri ->
        val bytes = pendingWrapped
        if (uri != null && bytes != null) {
            try {
                contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                toast(getString(R.string.key_exported))
            } catch (t: Throwable) {
                toast(getString(R.string.key_export_failed))
            }
        }
        pendingWrapped = null
        finishOk()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySetupBinding.inflate(layoutInflater)
        setContentView(binding.root)
        keyManager = KeyManager(this)
        binding.createButton.setOnClickListener { createKey() }
    }

    private fun createKey() {
        val p1 = binding.passphrase.text?.toString().orEmpty()
        val p2 = binding.passphraseConfirm.text?.toString().orEmpty()
        if (p1.length < MIN_PASSPHRASE) {
            toast(getString(R.string.passphrase_too_short))
            return
        }
        if (p1 != p2) {
            toast(getString(R.string.passphrase_mismatch))
            return
        }
        binding.createButton.isEnabled = false
        val chars = p1.toCharArray()
        // Key generation + Tink registration off the main thread.
        Thread {
            val wrapped = try {
                keyManager.setup(chars)
            } catch (t: Throwable) {
                null
            } finally {
                chars.fill('\u0000')
            }
            runOnUiThread {
                if (wrapped == null) {
                    binding.createButton.isEnabled = true
                    toast(getString(R.string.key_create_failed))
                } else {
                    pendingWrapped = wrapped
                    exportKey.launch("snoopguard-private-key.sgk")
                }
            }
        }.start()
    }

    private fun finishOk() {
        setResult(RESULT_OK)
        finish()
    }

    private fun toast(message: String) =
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()

    companion object {
        private const val MIN_PASSPHRASE = 8
    }
}
