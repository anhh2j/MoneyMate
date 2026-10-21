package com.app.moneymate.buildlogic

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files

class VersioningTest {
    @Test
    fun officialExamples() {
        mapOf(
            "0.1.0-alpha.1" to 10001,
            "0.1.0" to 10099,
            "0.3.0-beta.2" to 30032,
            "0.3.1" to 30199,
            "1.0.0-rc.1" to 1000061,
            "1.0.0" to 1000099,
            "1.0.1" to 1000199,
            "1.1.0-alpha.1" to 1010001,
        ).forEach { (name, code) -> assertEquals(name, code, Versioning.parse(name).code) }
    }

    @Test
    fun stageAndPatchOrdering() {
        val names =
            listOf(
                "0.1.0-alpha.1",
                "0.1.0-alpha.29",
                "0.1.0-beta.1",
                "0.1.0-beta.29",
                "0.1.0-rc.1",
                "0.1.0-rc.29",
                "0.1.0",
                "0.1.1-alpha.1",
            )
        names.map { Versioning.parse(it).code }.zipWithNext().forEach { (first, second) -> assertTrue(first < second) }
    }

    @Test
    fun metadataDoesNotChangeAndroidVersion() {
        assertEquals(Versioning.parse("1.2.3-rc.4"), Versioning.parse("1.2.3-rc.4+20261019.sha-7"))
    }

    @Test
    fun rejectsInvalidAndUnsupportedVersions() {
        listOf(
            "",
            "v1.0.0",
            "01.0.0",
            "1.00.0",
            "1.0.01",
            "1.0",
            "1.0.0-dev",
            "1.0.0-alpha.0",
            "1.0.0-alpha.01",
            "1.0.0+",
            "1.0.0+bad..meta",
            " 1.0.0",
            "1.0.0\n",
        ).forEach {
            assertThrows(it, IllegalArgumentException::class.java) { Versioning.parse(it) }
        }
    }

    @Test
    fun rejectsOutOfRangeAndOverflow() {
        listOf(
            "0.100.0",
            "0.0.100",
            "0.1.0-alpha.30",
            "0.1.0-beta.30",
            "0.1.0-rc.30",
            "999999999999999999999.0.0",
            "2148.0.0",
        ).forEach {
            assertThrows(it, IllegalArgumentException::class.java) { Versioning.parse(it) }
        }
        assertEquals(999999, Versioning.parse("0.99.99").code)
    }

    @Test
    fun propertiesMustHaveOneSource() {
        val file = Files.createTempFile("moneymate-version-test-", ".properties").toFile()
        try {
            file.writeText("VERSION_NAME=0.1.0-alpha.1\n")
            assertEquals(10001, Versioning.read(file).code)
            file.writeText("VERSION_NAME=0.1.0\nVERSION_NAME=0.2.0\n")
            assertThrows(IllegalArgumentException::class.java) { Versioning.read(file) }
        } finally {
            check(file.delete())
        }
    }
}
