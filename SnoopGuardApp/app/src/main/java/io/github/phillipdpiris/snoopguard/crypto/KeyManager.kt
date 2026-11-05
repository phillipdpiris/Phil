package io.github.phillipdpiris.snoopguard.crypto

import android.content.Context
import java.io.File

/**
 * Stores the key material on the device:
 *
 * - `public.keyset`  — the public key, in the clear. Used to encrypt captures
 *   and imports. Holding it grants no ability to decrypt anything.
 * - `private.sgk`    — the private key, wrapped by the passphrase (see
 *   [KeyVault]). Useless to anyone who doesn't know the passphrase, so a snooper
 *   who seizes the unlocked phone and copies this file still can't read captures.
 *
 * The passphrase itself is never stored.
 */
class KeyManager(context: Context) {

    private val dir = File(context.filesDir, "keys").apply { mkdirs() }
    private val publicFile = File(dir, "public.keyset")
    private val privateFile = File(dir, "private.sgk")

    fun isSetup(): Boolean = publicFile.exists() && privateFile.exists()

    /**
     * Generates a new key pair, stores the public keyset and the
     * passphrase-wrapped private keyset, and returns the wrapped private blob so
     * the caller can offer to export it (back it up off the phone).
     */
    fun setup(passphrase: CharArray): ByteArray {
        val pair = FileCrypto.generateKeyPair()
        publicFile.writeBytes(pair.publicKeyset)
        val wrapped = KeyVault.wrap(pair.privateKeyset, passphrase)
        privateFile.writeBytes(wrapped)
        return wrapped
    }

    /** Public keyset bytes for encrypting. Throws if not set up. */
    fun publicKeyset(): ByteArray = publicFile.readBytes()

    /** The wrapped private blob, for re-export. */
    fun wrappedPrivate(): ByteArray = privateFile.readBytes()

    /**
     * Unwraps the private keyset for viewing. The returned bytes are sensitive;
     * the caller should use them transiently and not persist them.
     *
     * @throws KeyVault.BadPassphraseException on a wrong passphrase.
     */
    fun loadPrivateKeyset(passphrase: CharArray): ByteArray =
        KeyVault.unwrap(privateFile.readBytes(), passphrase)
}
