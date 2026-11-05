package io.github.phillipdpiris.snoopguardviewer.crypto

import com.google.crypto.tink.InsecureSecretKeyAccess
import com.google.crypto.tink.KeyTemplates
import com.google.crypto.tink.KeysetHandle
import com.google.crypto.tink.TinkProtoKeysetFormat
import com.google.crypto.tink.HybridDecrypt
import com.google.crypto.tink.HybridEncrypt
import com.google.crypto.tink.StreamingAead
import com.google.crypto.tink.config.TinkConfig
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.InputStream
import java.io.OutputStream

/**
 * Byte-for-byte copy of the SnoopGuard app's FileCrypto, so this viewer reads
 * the exact same ".sgc" container. (Kept duplicated rather than shared via a
 * module to keep the two apps independent; a shared crypto module is a later
 * refactor — see README.)
 *
 * Container: "SGC1" | int32 sealedKeyLen | HPKE-sealed per-file StreamingAead
 * keyset | StreamingAead(AES256_GCM_HKDF_1MB) ciphertext.
 */
object FileCrypto {

    private const val MAGIC = "SGC1"
    private val AD = "snoopguard-v1".toByteArray(Charsets.US_ASCII)
    private const val HYBRID_TEMPLATE = "DHKEM_X25519_HKDF_SHA256_HKDF_SHA256_AES_256_GCM"
    private const val STREAM_TEMPLATE = "AES256_GCM_HKDF_1MB"

    @Volatile
    private var registered = false

    fun ensureRegistered() {
        if (!registered) {
            synchronized(this) {
                if (!registered) {
                    TinkConfig.register()
                    registered = true
                }
            }
        }
    }

    data class KeyPair(val publicKeyset: ByteArray, val privateKeyset: ByteArray)

    fun generateKeyPair(): KeyPair {
        ensureRegistered()
        val priv = KeysetHandle.generateNew(KeyTemplates.get(HYBRID_TEMPLATE))
        val pub = priv.publicKeysetHandle
        return KeyPair(
            publicKeyset = TinkProtoKeysetFormat.serializeKeysetWithoutSecret(pub),
            privateKeyset = TinkProtoKeysetFormat.serializeKeyset(priv, InsecureSecretKeyAccess.get()),
        )
    }

    fun encrypt(publicKeyset: ByteArray, input: InputStream, output: OutputStream) {
        ensureRegistered()
        val pubHandle = TinkProtoKeysetFormat.parseKeysetWithoutSecret(publicKeyset)
        val hybrid = pubHandle.getPrimitive(HybridEncrypt::class.java)

        val streamHandle = KeysetHandle.generateNew(KeyTemplates.get(STREAM_TEMPLATE))
        val streamKeyset = TinkProtoKeysetFormat.serializeKeyset(streamHandle, InsecureSecretKeyAccess.get())
        val sealedKey = hybrid.encrypt(streamKeyset, AD)

        val header = DataOutputStream(output)
        header.writeBytes(MAGIC)
        header.writeInt(sealedKey.size)
        header.write(sealedKey)
        header.flush()

        val streaming = streamHandle.getPrimitive(StreamingAead::class.java)
        streaming.newEncryptingStream(output, AD).use { enc ->
            input.copyTo(enc)
        }
    }

    fun decrypt(privateKeyset: ByteArray, input: InputStream, output: OutputStream) {
        ensureRegistered()
        val privHandle = TinkProtoKeysetFormat.parseKeyset(privateKeyset, InsecureSecretKeyAccess.get())
        val hybrid = privHandle.getPrimitive(HybridDecrypt::class.java)

        val header = DataInputStream(input)
        val magic = ByteArray(MAGIC.length)
        header.readFully(magic)
        require(String(magic, Charsets.US_ASCII) == MAGIC) { "Not a SnoopGuard capture file" }
        val sealedLen = header.readInt()
        require(sealedLen in 1..10_000) { "Corrupt header" }
        val sealedKey = ByteArray(sealedLen)
        header.readFully(sealedKey)

        val streamKeyset = hybrid.decrypt(sealedKey, AD)
        val streamHandle = TinkProtoKeysetFormat.parseKeyset(streamKeyset, InsecureSecretKeyAccess.get())
        val streaming = streamHandle.getPrimitive(StreamingAead::class.java)
        streaming.newDecryptingStream(input, AD).use { dec ->
            dec.copyTo(output)
        }
    }
}
