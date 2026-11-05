package io.github.phillipdpiris.snoopguard

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pure-logic tests that don't need an Android device. */
class CaptureStoreTest {

    @Test
    fun logLine_isTabSeparated_withLeadingTimestamp() {
        val line = CaptureStore.formatLogLine("trigger\tunlock", nowMs = 1_700_000_000_000L)
        assertEquals("1700000000000\ttrigger\tunlock", line)
    }

    @Test
    fun logLine_usesMonotonicStamp_forOrdering() {
        val a = CaptureStore.formatLogLine("a", nowMs = 100L)
        val b = CaptureStore.formatLogLine("b", nowMs = 200L)
        val earlier = a.substringBefore('\t').toLong()
        val later = b.substringBefore('\t').toLong()
        assertTrue(earlier < later)
    }
}
