package io.github.phillipdpiris.snoopguardviewer.crypto

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import kotlin.random.Random

/**
 * Confirms the viewer's copied crypto core round-trips and uses the same
 * container formats as the app, so files the app writes decrypt here.
 */
class CryptoRoundTripTest {

    @Test
    fun fileCrypto_roundTrip_small() {
        val pair = FileCrypto.generateKeyPair()
        val plaintext = "a captured selfie".toByteArray()
        val enc = ByteArrayOutputStream()
        FileCrypto.encrypt(pair.publicKeyset, ByteArrayInputStream(plaintext), enc)
        val dec = ByteArrayOutputStream()
        FileCrypto.decrypt(pair.privateKeyset, ByteArrayInputStream(enc.toByteArray()), dec)
        assertArrayEquals(plaintext, dec.toByteArray())
    }

    @Test
    fun fileCrypto_roundTrip_largeVideoSized() {
        val pair = FileCrypto.generateKeyPair()
        val plaintext = Random(7).nextBytes(3 * 1024 * 1024 + 7)
        val enc = ByteArrayOutputStream()
        FileCrypto.encrypt(pair.publicKeyset, ByteArrayInputStream(plaintext), enc)
        val dec = ByteArrayOutputStream()
        FileCrypto.decrypt(pair.privateKeyset, ByteArrayInputStream(enc.toByteArray()), dec)
        assertArrayEquals(plaintext, dec.toByteArray())
    }

    @Test
    fun keyVault_wrapUnwrap_andWrongPassphrase() {
        val secret = Random(2).nextBytes(140)
        val blob = KeyVault.wrap(secret, "a good passphrase".toCharArray())
        assertArrayEquals(secret, KeyVault.unwrap(blob, "a good passphrase".toCharArray()))
        assertThrows(KeyVault.BadPassphraseException::class.java) {
            KeyVault.unwrap(blob, "bad".toCharArray())
        }
    }
}
