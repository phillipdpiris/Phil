package io.github.phillipdpiris.snoopguard.crypto

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Test
import kotlin.random.Random

class KeyVaultTest {

    private val secret = Random(1).nextBytes(140) // ~ a serialized private keyset

    @Test
    fun wrapThenUnwrap_recoversSecret() {
        val blob = KeyVault.wrap(secret, "correct horse battery staple".toCharArray())
        val out = KeyVault.unwrap(blob, "correct horse battery staple".toCharArray())
        assertArrayEquals(secret, out)
    }

    @Test
    fun wrongPassphrase_throws() {
        val blob = KeyVault.wrap(secret, "right-passphrase".toCharArray())
        assertThrows(KeyVault.BadPassphraseException::class.java) {
            KeyVault.unwrap(blob, "wrong-passphrase".toCharArray())
        }
    }

    @Test
    fun corruptBlob_throws() {
        val blob = KeyVault.wrap(secret, "pw".toCharArray())
        blob[blob.size - 1] = (blob[blob.size - 1] + 1).toByte() // flip a ciphertext byte
        assertThrows(KeyVault.BadPassphraseException::class.java) {
            KeyVault.unwrap(blob, "pw".toCharArray())
        }
    }

    @Test
    fun blob_startsWithMagic_andHidesSecret() {
        val blob = KeyVault.wrap(secret, "pw".toCharArray())
        assertEquals("SGK1", String(blob.copyOfRange(0, 4), Charsets.US_ASCII))
        // the plaintext secret must not appear in the wrapped blob
        assertFalse(blob.toList().windowed(secret.size).any { it == secret.toList() })
    }

    @Test
    fun eachWrap_usesFreshSaltAndNonce() {
        val a = KeyVault.wrap(secret, "pw".toCharArray())
        val b = KeyVault.wrap(secret, "pw".toCharArray())
        assertFalse("two wraps should differ (random salt+nonce)", a.contentEquals(b))
    }
}
