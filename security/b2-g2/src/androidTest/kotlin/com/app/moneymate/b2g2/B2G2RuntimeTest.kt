package com.app.moneymate.b2g2

import android.app.ActivityManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.Build
import android.os.Debug
import android.os.Process
import android.os.SystemClock
import android.system.Os
import android.system.OsConstants
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Public upstream vectors, synthetic inputs only; provider lives in the target APK. */
@RunWith(AndroidJUnit4::class)
class B2G2RuntimeTest {
    private val publicInput = "password".toByteArray()
    private val publicSalt = "somesalt".toByteArray()

    @Test
    fun nativeLoadAndPublishedKnownAnswers() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("com.app.moneymate.b2g2", context.packageName)
        assertEquals(0, context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE)
        assertEquals("x86_64", Build.SUPPORTED_ABIS.first())
        assertTrue(Process.is64Bit())
        B2KdfProbe.nativeLoad()
        assertEquals(
            "9dfeb910e80bad0311fee20f9c0e2b12c17987b4cac90c2ef54d5b3021c68bfe",
            derive(256),
        )
        metric(JSONObject().put("case", "KAT_256_KiB").put("result", "PASS"))
        assertEquals(
            "09316115d5cf24ed5a15a31a3ba326e5cf32edc24702987c02b6566f61913cf7",
            derive(65536),
        )
        metric(JSONObject().put("case", "KAT_65536_KiB").put("result", "PASS"))
    }

    @Test
    fun verifierAndSensitivityThroughTarget() {
        val reference = derive(256)
        val encoded = B2KdfProbe.encode(publicInput, publicSalt)
        assertTrue(B2KdfProbe.verify(encoded, publicInput))
        assertFalse(B2KdfProbe.verify(encoded, "wrong-synthetic".toByteArray()))
        assertFalse(reference == derive(512))
        assertFalse(reference == B2KdfProbe.derive(publicInput, "diffsalt".toByteArray(), 256, 2))
        assertFalse(reference == B2KdfProbe.derive(publicInput, publicSalt, 256, 3))
        metric(JSONObject().put("case", "VERIFIER_AND_SENSITIVITY").put("result", "PASS"))
    }

    @Test
    fun malformedInputsRejectedByExactExceptionTypeInTarget() {
        for (case in listOf("SHORT_SALT", "ZERO_MEMORY", "ZERO_ITERATIONS", "BAD_ENCODING")) {
            assertTrue(case, B2KdfProbe.rejects(case, publicInput, publicSalt))
        }
        metric(JSONObject().put("case", "MALFORMED_REJECTED").put("result", "PASS"))
    }

    @Test
    fun measuredProfilesThroughTarget() {
        for (memory in listOf(1024, 8192, 65536)) {
            derive(memory)
            repeat(5) { run ->
                val before = memorySnapshot()
                val start = SystemClock.elapsedRealtimeNanos()
                val result = derive(memory)
                val elapsed = SystemClock.elapsedRealtimeNanos() - start
                assertEquals(64, result.length)
                metric(
                    JSONObject()
                        .put("case", "BENCHMARK_TEST_ONLY")
                        .put("mKiB", memory)
                        .put("t", 2)
                        .put("p", 1)
                        .put("run", run)
                        .put("elapsedNs", elapsed)
                        .put("before", before)
                        .put("after", memorySnapshot()),
                )
            }
        }
    }

    @Test
    fun boundedPressureThroughTarget() {
        val pressure = List(4) { ByteArray(4 * 1024 * 1024) { 1 } }
        assertEquals(64, derive(8192).length)
        assertEquals(4, pressure.sumOf { it[0].toInt() })
        metric(
            JSONObject()
                .put("case", "BOUNDED_PRESSURE_16_MiB")
                .put("result", "PASS")
                .put("nativeOom", "NOT-VERIFIED")
                .put("memory", memorySnapshot()),
        )
    }

    private fun derive(memory: Int): String = B2KdfProbe.derive(publicInput, publicSalt, memory, 2)

    private fun memorySnapshot(): JSONObject {
        val runtime = Runtime.getRuntime()
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val manager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val information = ActivityManager.MemoryInfo()
        manager.getMemoryInfo(information)
        return JSONObject()
            .put("pssKiB", Debug.getPss())
            .put("nativeAllocatedBytes", Debug.getNativeHeapAllocatedSize())
            .put("javaUsedBytes", runtime.totalMemory() - runtime.freeMemory())
            .put("javaMaxBytes", runtime.maxMemory())
            .put("memoryClassMiB", manager.memoryClass)
            .put("totalMemBytes", information.totalMem)
            .put("availableMemBytes", information.availMem)
            .put("lowRamDevice", manager.isLowRamDevice)
            .put("measurement", "Before/after snapshots, not peak per-call allocation")
    }

    private fun metric(value: JSONObject) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        value
            .put("scope", "B2_G2_TEST_ONLY")
            .put("api", Build.VERSION.SDK_INT)
            .put("abis", Build.SUPPORTED_ABIS.joinToString(","))
            .put("process64Bit", Process.is64Bit())
            .put("pageSize", Os.sysconf(OsConstants._SC_PAGESIZE))
            .put("targetPackage", context.packageName)
            .put("targetSourceDir", context.applicationInfo.sourceDir)
        Log.i("B2_G2_METRIC", value.toString())
    }
}
