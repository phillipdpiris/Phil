package io.github.phillipdpiris.snoopguard

import android.content.Context
import java.io.File

/**
 * Holds imported media, encrypted as `.sgc`, separate from captures. Filenames
 * are opaque (timestamp only) so the vault does not leak original names; the
 * file type is recovered by magic-byte sniffing at decrypt time.
 */
class ImportStore(context: Context) {

    private val dir = File(context.filesDir, "imports").apply { mkdirs() }

    fun newImportFile(timestampMs: Long, index: Int): File =
        File(dir, "import_${timestampMs}_$index.sgc")

    fun listImports(): List<File> =
        dir.listFiles { f -> f.extension == "sgc" }
            ?.sortedByDescending { it.lastModified() }
            ?: emptyList()
}
