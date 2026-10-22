package com.app.moneymate.security.b2

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import android.os.Debug
import android.os.SystemClock
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.lambdapioneer.argon2kt.Argon2Exception
import com.lambdapioneer.argon2kt.Argon2Kt
import com.lambdapioneer.argon2kt.Argon2Mode
import com.lambdapioneer.argon2kt.Argon2Version
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.security.MessageDigest

/** Isolated B2 experiment. All inputs are public synthetic upstream vectors. */
@RunWith(AndroidJUnit4::class)
class Argon2CompatibilityTest {
    private val mode = Argon2Mode.ARGON2_ID

    // Upstream v1.6.0 Argon2KtTest.officialTestSuite_v13_argon2id_case3 and case1.
    @Test
    fun nativeLoadAndKnownAnswerSmall() {
        Argon2Kt.assertJniWorking()
        assertEquals(
            "9dfeb910e80bad0311fee20f9c0e2b12c17987b4cac90c2ef54d5b3021c68bfe",
            derive(256).rawHashAsHexadecimal(),
        )
        metric(JSONObject().put("case", "KAT_256_KiB").put("result", "PASS"))
    }

    @Test
    fun knownAnswerLarge() {
        assertEquals(
            "09316115d5cf24ed5a15a31a3ba326e5cf32edc24702987c02b6566f61913cf7",
            derive(65536).rawHashAsHexadecimal(),
        )
        metric(JSONObject().put("case", "KAT_65536_KiB").put("result", "PASS"))
    }

    @Test
    fun verifierAndParameterSensitivity() {
        val engine = Argon2Kt()
        val reference = derive(256)
        assertTrue(engine.verify(mode, reference.encodedOutputAsString(), "password".toByteArray()))
        assertFalse(engine.verify(mode, reference.encodedOutputAsString(), "wrong-synthetic".toByteArray()))
        val changedSalt = derive(256, salt = "diffsalt")
        val changedMemory = derive(512)
        val changedIterations = derive(256, iterations = 3)
        for (changed in listOf(changedSalt, changedMemory, changedIterations)) {
            assertFalse(MessageDigest.isEqual(reference.rawHashAsByteArray(), changed.rawHashAsByteArray()))
        }
        metric(JSONObject().put("case", "VERIFIER_AND_SENSITIVITY").put("result", "PASS"))
    }

    @Test
    fun malformedInputsRejected() {
        assertThrows(Argon2Exception::class.java) { derive(256, salt = "short") }
        assertThrows(IllegalArgumentException::class.java) { derive(0) }
        assertThrows(IllegalArgumentException::class.java) { derive(256, iterations = 0) }
        assertThrows(Argon2Exception::class.java) { Argon2Kt().verify(mode, "SYNTHETIC_INVALID_ENCODING", "password".toByteArray()) }
        metric(JSONObject().put("case", "MALFORMED_REJECTED").put("result", "PASS"))
    }

    @Test
    fun measuredLatencyAndMemorySnapshots() {
        // Test-only settings. No production parameter or latency acceptance threshold.
        for (memory in listOf(1024, 8192, 65536)) {
            derive(memory) // Warm-up, excluded from measurements.
            repeat(5) { run ->
                val before = memorySnapshot()
                val start = SystemClock.elapsedRealtimeNanos()
                val result = derive(memory)
                val elapsed = SystemClock.elapsedRealtimeNanos() - start
                assertEquals(32, result.rawHashAsByteArray().size)
                metric(
                    JSONObject()
                        .put("case", "BENCHMARK_TEST_ONLY")
                        .put("mKiB", memory)
                        .put("t", 2)
                        .put("p", 1)
                        .put("run", run)
                        .put("elapsedNs", elapsed)
                        .put("before", before)
                        .put("after", memorySnapshot())
                        .put("measurement", "PSS/native/Java snapshots; not per-call peak allocation"),
                )
            }
        }
    }

    @Test
    fun boundedMemoryPressureProbe() {
        // A bounded 16 MiB Java allocation, not proof of exhausted-memory behavior.
        val pressure = List(4) { ByteArray(4 * 1024 * 1024) { 1 } }
        assertEquals(32, derive(8192).rawHashAsByteArray().size)
        assertEquals(4, pressure.sumOf { it[0].toInt() })
        metric(
            JSONObject()
                .put("case", "BOUNDED_PRESSURE_16_MiB")
                .put("result", "PASS")
                .put("exhaustedMemory", "NOT-VERIFIED")
                .put("memory", memorySnapshot()),
        )
    }

    private fun derive(
        memory: Int,
        salt: String = "somesalt",
        iterations: Int = 2,
    ) = Argon2Kt().hash(
        mode = mode,
        password = "password".toByteArray(),
        salt = salt.toByteArray(),
        tCostInIterations = iterations,
        mCostInKibibyte = memory,
        parallelism = 1,
        hashLengthInBytes = 32,
        version = Argon2Version.V13,
    )

    private fun memorySnapshot(): JSONObject {
        val runtime = Runtime.getRuntime()
        val manager =
            InstrumentationRegistry
                .getInstrumentation()
                .context
                .getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        return JSONObject()
            .put("pssKiB", Debug.getPss())
            .put("nativeAllocatedBytes", Debug.getNativeHeapAllocatedSize())
            .put("javaUsedBytes", runtime.totalMemory() - runtime.freeMemory())
            .put("javaMaxBytes", runtime.maxMemory())
            .put("lowRamDevice", manager.isLowRamDevice)
    }

    private fun metric(value: JSONObject) {
        value
            .put("api", Build.VERSION.SDK_INT)
            .put("abis", Build.SUPPORTED_ABIS.joinToString(","))
            .put("scope", "B2_TEST_ONLY")
            .put("r8", "NOT-VERIFIED")
        Log.i("B2_METRIC", value.toString())
    }
}
