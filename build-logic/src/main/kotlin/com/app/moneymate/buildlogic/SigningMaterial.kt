package com.app.moneymate.buildlogic

import org.gradle.api.services.BuildService
import org.gradle.api.services.BuildServiceParameters
import java.io.File
import java.nio.file.Files
import java.util.Base64

abstract class SigningMaterial :
    BuildService<BuildServiceParameters.None>,
    AutoCloseable {
    private val directory = Files.createTempDirectory("moneymate-signing-").toFile()

    fun decode(value: String): File =
        File(directory, "temporary-signing.jks").apply {
            writeBytes(Base64.getDecoder().decode(value))
        }

    override fun close() {
        check(directory.deleteRecursively()) { "Could not remove temporary signing material" }
    }
}
