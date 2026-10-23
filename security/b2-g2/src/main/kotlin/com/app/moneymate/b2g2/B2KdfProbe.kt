package com.app.moneymate.b2g2

import com.lambdapioneer.argon2kt.Argon2Exception
import com.lambdapioneer.argon2kt.Argon2Kt
import com.lambdapioneer.argon2kt.Argon2Mode
import com.lambdapioneer.argon2kt.Argon2Version

/** Target APK facade for the isolated experiment. No MoneyMate production caller. */
object B2KdfProbe {
    private const val SMALL_VECTOR_MEMORY_KIB = 256

    @JvmStatic
    fun nativeLoad() = Argon2Kt.assertJniWorking()

    @JvmStatic
    fun derive(
        input: ByteArray,
        salt: ByteArray,
        memory: Int,
        iterations: Int,
    ): String = hash(input, salt, memory, iterations).rawHashAsHexadecimal()

    @JvmStatic
    fun encode(
        input: ByteArray,
        salt: ByteArray,
    ): String = hash(input, salt, SMALL_VECTOR_MEMORY_KIB, 2).encodedOutputAsString()

    @JvmStatic
    fun verify(
        encoded: String,
        input: ByteArray,
    ): Boolean = Argon2Kt().verify(Argon2Mode.ARGON2_ID, encoded, input)

    @JvmStatic
    fun rejects(
        case: String,
        input: ByteArray,
        salt: ByteArray,
    ): Boolean =
        try {
            when (case) {
                "SHORT_SALT" -> hash(input, ByteArray(2), SMALL_VECTOR_MEMORY_KIB, 2)
                "ZERO_MEMORY" -> hash(input, salt, 0, 2)
                "ZERO_ITERATIONS" -> hash(input, salt, SMALL_VECTOR_MEMORY_KIB, 0)
                "BAD_ENCODING" -> verify("SYNTHETIC_INVALID_ENCODING", input)
                else -> error("Unknown synthetic test case")
            }
            false
        } catch (error: Argon2Exception) {
            if (case !in listOf("SHORT_SALT", "BAD_ENCODING")) throw error
            true
        } catch (error: IllegalArgumentException) {
            if (case !in listOf("ZERO_MEMORY", "ZERO_ITERATIONS")) throw error
            true
        }

    private fun hash(
        input: ByteArray,
        salt: ByteArray,
        memory: Int,
        iterations: Int,
    ) = Argon2Kt().hash(
        mode = Argon2Mode.ARGON2_ID,
        password = input,
        salt = salt,
        tCostInIterations = iterations,
        mCostInKibibyte = memory,
        parallelism = 1,
        hashLengthInBytes = 32,
        version = Argon2Version.V13,
    )
}

/** The inspector must prove this unreachable class was removed by R8. */
internal class B2G2UnreachableCanary {
    val marker = "B2_G2_CANARY_MUST_BE_REMOVED"
}
