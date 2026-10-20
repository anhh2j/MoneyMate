package com.app.moneymate.buildlogic

import java.io.File
import java.util.Properties

data class AppVersion(
    val name: String,
    val code: Int,
)

object Versioning {
    private const val PATCH_GROUP = 3
    private const val STAGE_GROUP = 4
    private const val SEQUENCE_GROUP = 5
    private const val MAJOR_FACTOR = 1_000_000L
    private const val MINOR_FACTOR = 10_000L
    private const val PATCH_FACTOR = 100L
    private const val COMPONENT_LIMIT = 99L
    private const val PRE_LIMIT = 29L
    private const val BETA_OFFSET = 30L
    private const val RC_OFFSET = 60L
    private const val STABLE_OFFSET = 99L
    private val pattern =
        Regex(
            "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)" +
                "(?:-(alpha|beta|rc)\\.([1-9][0-9]*))?" +
                "(?:\\+[0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*)?$",
        )

    fun read(file: File): AppVersion {
        val text = file.readText()
        require(text.lineSequence().count { it.trim().startsWith("VERSION_NAME=") } == 1) {
            "version.properties must contain exactly one VERSION_NAME assignment"
        }
        val properties = Properties().apply { text.reader().use { load(it) } }
        require(properties.keys == setOf("VERSION_NAME")) { "Unexpected version.properties keys" }
        return parse(properties.getProperty("VERSION_NAME"))
    }

    fun parse(value: String): AppVersion {
        val match = requireNotNull(pattern.matchEntire(value)) { "Invalid or unsupported SemVer: $value" }
        val major = match.groupValues[1].toLongOrNull()
        val minor = match.groupValues[2].toLongOrNull()
        val patch = match.groupValues[PATCH_GROUP].toLongOrNull()
        require(major != null && major <= Int.MAX_VALUE / MAJOR_FACTOR) { "MAJOR/versionCode overflow" }
        require(minor != null && minor <= COMPONENT_LIMIT) { "MINOR must be in 0..99" }
        require(patch != null && patch <= COMPONENT_LIMIT) { "PATCH must be in 0..99" }
        val rank = prereleaseRank(match.groupValues[STAGE_GROUP], match.groupValues[SEQUENCE_GROUP])
        val code = major * MAJOR_FACTOR + minor * MINOR_FACTOR + patch * PATCH_FACTOR + rank
        require(code <= Int.MAX_VALUE) { "versionCode exceeds Android integer range" }
        return AppVersion(value.substringBefore('+'), code.toInt())
    }

    private fun prereleaseRank(
        stage: String,
        sequence: String,
    ): Long {
        if (stage.isEmpty()) return STABLE_OFFSET
        val number = sequence.toLongOrNull()
        require(number != null && number in 1..PRE_LIMIT) { "Pre-release sequence must be in 1..29" }
        val offset =
            when (stage) {
                "alpha" -> 0L
                "beta" -> BETA_OFFSET
                else -> RC_OFFSET
            }
        return offset + number
    }
}
