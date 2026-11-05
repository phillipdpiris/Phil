package io.github.phillipdpiris.snoopguardviewer.crypto

import java.nio.ByteBuffer
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Byte-for-byte copy of the SnoopGuard app's KeyVault, so this viewer unwraps
 * the exact same ".sgk" blob the app exports.
 *
 * Container: "SGK1" | int32 iterations | uint8 saltLen | salt | 12B nonce |
 * AES-256-GCM(private keyset), key = PBKDF2-HMAC-SHA256(passphrase, salt, iters).
 */
object KeyVault {

    private const val MAGIC = "SGK1"
    private const val ITERATIONS = 210_000
    private const val SALT_LEN = 16
    private const val NONCE_LEN = 12
    private const val TAG_BITS = 128
    private const val KEY_BITS = 256

    class BadPassphraseException : Exception("Wrong passphrase or corrupt key blob")

    fun wrap(privateKeyset: ByteArray, passphrase: CharArray): ByteArray {
        val rng = SecureRandom()
        val salt = ByteArray(SALT_LEN).also { rng.nextBytes(it) }
        val nonce = ByteArray(NONCE_LEN).also { rng.nextBytes(it) }
        val key = deriveKey(passphrase, salt, ITERATIONS)

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(TAG_BITS, nonce))
        val ciphertext = cipher.doFinal(privateKeyset)

        val magic = MAGIC.toByteArray(Charsets.US_ASCII)
        return ByteBuffer.allocate(magic.size + 4 + 1 + salt.size + nonce.size + ciphertext.size)
            .put(magic)
            .putInt(ITERATIONS)
            .put(salt.size.toByte())
            .put(salt)
            .put(nonce)
            .put(ciphertext)
            .array()
    }

    /** @throws BadPassphraseException if the passphrase is wrong or the blob is corrupt. */
    fun unwrap(blob: ByteArray, passphrase: CharArray): ByteArray {
        try {
            val buf = ByteBuffer.wrap(blob)
            val magic = ByteArray(MAGIC.length).also { buf.get(it) }
            require(String(magic, Charsets.US_ASCII) == MAGIC) { "bad magic" }
            val iterations = buf.getInt()
            val saltLen = buf.get().toInt()
            require(saltLen in 1..64) { "bad salt length" }
            val salt = ByteArray(saltLen).also { buf.get(it) }
            val nonce = ByteArray(NONCE_LEN).also { buf.get(it) }
            val ciphertext = ByteArray(buf.remaining()).also { buf.get(it) }

            val key = deriveKey(passphrase, salt, iterations)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(TAG_BITS, nonce))
            return cipher.doFinal(ciphertext)
        } catch (e: Exception) {
            throw BadPassphraseException()
        }
    }

    private fun deriveKey(passphrase: CharArray, salt: ByteArray, iterations: Int): SecretKeySpec {
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val spec = PBEKeySpec(passphrase, salt, iterations, KEY_BITS)
        try {
            return SecretKeySpec(factory.generateSecret(spec).encoded, "AES")
        } finally {
            spec.clearPassword()
        }
    }
}
