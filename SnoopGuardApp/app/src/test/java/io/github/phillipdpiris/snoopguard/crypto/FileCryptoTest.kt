package io.github.phillipdpiris.snoopguard.crypto

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertFalse
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.security.GeneralSecurityException
import kotlin.random.Random

class FileCryptoTest {

    private fun roundTrip(plaintext: ByteArray) {
        val pair = FileCrypto.generateKeyPair()

        val encrypted = ByteArrayOutputStream()
        FileCrypto.encrypt(pair.publicKeyset, ByteArrayInputStream(plaintext), encrypted)
        val blob = encrypted.toByteArray()

        // The ciphertext must not contain the plaintext verbatim.
        if (plaintext.size >= 16) {
            assertFalse("ciphertext leaks plaintext", containsSubarray(blob, plaintext.copyOfRange(0, 16)))
        }

        val decrypted = ByteArrayOutputStream()
        FileCrypto.decrypt(pair.privateKeyset, ByteArrayInputStream(blob), decrypted)
        assertArrayEquals(plaintext, decrypted.toByteArray())
    }

    @Test
    fun roundTrip_smallPayload() = roundTrip("a selfie's worth of bytes".toByteArray())

    @Test
    fun roundTrip_emptyPayload() = roundTrip(ByteArray(0))

    @Test
    fun roundTrip_largePayload_exercisesStreamingChunks() {
        // 5 MB > the 1 MB streaming segment, so this crosses chunk boundaries
        // the way a short video would.
        roundTrip(Random(42).nextBytes(5 * 1024 * 1024))
    }

    @Test
    fun wrongPrivateKey_failsToDecrypt() {
        val a = FileCrypto.generateKeyPair()
        val b = FileCrypto.generateKeyPair()
        val encrypted = ByteArrayOutputStream()
        FileCrypto.encrypt(a.publicKeyset, ByteArrayInputStream("secret".toByteArray()), encrypted)

        assertThrows(GeneralSecurityException::class.java) {
            FileCrypto.decrypt(b.privateKeyset, ByteArrayInputStream(encrypted.toByteArray()), ByteArrayOutputStream())
        }
    }

    private fun containsSubarray(haystack: ByteArray, needle: ByteArray): Boolean {
        if (needle.isEmpty() || needle.size > haystack.size) return false
        outer@ for (i in 0..haystack.size - needle.size) {
            for (j in needle.indices) {
                if (haystack[i + j] != needle[j]) continue@outer
            }
            return true
        }
        return false
    }
}
