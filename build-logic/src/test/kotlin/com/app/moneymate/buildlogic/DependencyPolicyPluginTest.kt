package com.app.moneymate.buildlogic

import org.gradle.testkit.runner.GradleRunner
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.util.jar.JarEntry
import java.util.jar.JarOutputStream

class DependencyPolicyPluginTest {
    @get:Rule
    val temporary = TemporaryFolder()

    private val versions =
        """
        [versions]
        toolingBc = "1.86"
        toolingJose4j = "0.9.7"
        toolingJdom2 = "2.0.6.1"
        [libraries]
        """.trimIndent()

    @Test
    fun readsExactlyFiveGavsAndAlignsBc() {
        val file = temporary.newFile("catalog.toml").apply { writeText(versions) }
        val pins = DependencyPolicyPlugin.pins(file)
        assertEquals(5, pins.size)
        assertEquals(setOf("1.86"), pins.filterKeys { it.startsWith("org.bouncycastle:") }.values.toSet())
        assertEquals("0.9.7", pins["org.bitbucket.b_c:jose4j"])
        assertEquals("2.0.6.1", pins["org.jdom:jdom2"])
    }

    @Test
    fun missingOrDuplicatePinsFailClosed() {
        val file = temporary.newFile("invalid.toml")
        file.writeText(versions.replace("toolingBc = \"1.86\"", ""))
        assertThrows(IllegalArgumentException::class.java) { DependencyPolicyPlugin.pins(file) }
        file.writeText(versions.replace("[libraries]", "toolingBc = \"1.85\"\n[libraries]"))
        assertThrows(IllegalArgumentException::class.java) { DependencyPolicyPlugin.pins(file) }
    }

    @Test
    fun pinsBuildscriptsAndLintWithoutChangingUnrelatedOrRuntimeDependencies() {
        val fixture = fixture(includeSecureJdom = true)
        val output = runner(fixture).build().output
        assertTrue(output, output.contains("PIN_:="))
        assertTrue(output, output.contains("PIN_:child="))
        for (gav in DependencyPolicyPlugin.pins(File(fixture, "gradle/libs.versions.toml"))) {
            assertEquals(
                output,
                4,
                output
                    .lineSequence()
                    .filter { it.startsWith("PIN_") || it.startsWith("LINT_") }
                    .filter { it.contains("${gav.key}:${gav.value}") }
                    .count(),
            )
        }
        assertEquals(2, output.lineSequence().count { it.startsWith("CONTROL_") && it.endsWith("2.0.6") })
        assertEquals(2, output.lineSequence().count { it.startsWith("RUNTIME_") && it.endsWith("2.0.6") })
    }

    @Test
    fun unavailableSecureArtifactFailsInsteadOfFallingBackToOldVersion() {
        val output = runner(fixture(includeSecureJdom = false)).buildAndFail().output
        assertTrue(output, output.contains("org.jdom:jdom2:2.0.6.1"))
        assertTrue(output, output.contains("Could not find"))
    }

    private fun runner(directory: File): GradleRunner =
        GradleRunner
            .create()
            .withProjectDir(directory)
            .withTestKitDir(File(directory, "test-kit"))
            .withPluginClasspath()
            .withArguments(
                "recordPolicy",
                ":child:recordPolicy",
                "--offline",
                "--no-configuration-cache",
                "--stacktrace",
            )

    private fun fixture(includeSecureJdom: Boolean): File {
        val root = temporary.newFolder()
        File(root, "gradle").mkdirs()
        File(root, "gradle/libs.versions.toml").writeText(versions)
        File(root, "settings.gradle").writeText(
            "plugins { id 'moneymate.dependency-policy' }\nrootProject.name='policy-fixture'\ninclude 'child'\n",
        )
        File(root, "gradle.properties").writeText("org.gradle.jvmargs=-Xmx256m\norg.gradle.workers.max=2\n")
        val pins = DependencyPolicyPlugin.pins(File(root, "gradle/libs.versions.toml"))
        val previous =
            pins.mapValues {
                if (it.key.startsWith("org.bouncycastle:")) {
                    "1.80.2"
                } else if (it.key.endsWith("jose4j")) {
                    "0.9.5"
                } else {
                    "2.0.6"
                }
            }
        for ((gav, version) in previous + mapOf("org.jdom:unrelated" to "2.0.6")) publish(root, gav, version)
        for ((gav, version) in pins) if (includeSecureJdom || gav != "org.jdom:jdom2") publish(root, gav, version)
        val dependencies =
            (previous + mapOf("org.jdom:unrelated" to "2.0.6"))
                .map { (gav, version) ->
                    "<dependency><groupId>${gav.substringBefore(':')}</groupId>" +
                        "<artifactId>${gav.substringAfter(':')}</artifactId><version>$version</version></dependency>"
                }.joinToString("")
        publish(root, "fixture:tool", "1.0", dependencies)
        val script =
            """
            buildscript {
                repositories { maven { url = uri('${File(root, "repo").toURI()}') } }
                dependencies { classpath 'fixture:tool:1.0' }
            }
            repositories { maven { url = uri('${File(root, "repo").toURI()}') } }
            configurations { probeRuntime; androidLintTool }
            dependencies { probeRuntime 'org.jdom:jdom2:2.0.6'; androidLintTool 'fixture:tool:1.0' }
            tasks.register('recordPolicy') {
                doLast {
                    def selected = buildscript.configurations.classpath.incoming.resolutionResult
                    .allComponents.collect { it.moduleVersion }.findAll { it != null }
                    println('PIN_' + project.path + '=' + selected.collect { it.toString() }.sort().join('|'))
                    def lint = configurations.androidLintTool.incoming.resolutionResult
                    .allComponents.collect { it.moduleVersion }.findAll { it != null }
                    println('LINT_' + project.path + '=' + lint.collect { it.toString() }.sort().join('|'))
                    println('CONTROL_' + project.path + '=' + selected.find { it.name == 'unrelated' }.version)
                    def runtime = configurations.probeRuntime.incoming.resolutionResult
                    .allComponents.find { it.moduleVersion?.name == 'jdom2' }.moduleVersion.version
                println('RUNTIME_' + project.path + '=' + runtime)
                }
            }
            """.trimIndent()
        File(root, "build.gradle").writeText(script)
        File(root, "child").mkdirs()
        File(root, "child/build.gradle").writeText(script)
        return root
    }

    private fun publish(
        root: File,
        gav: String,
        version: String,
        dependencies: String = "",
    ) {
        val group = gav.substringBefore(':')
        val name = gav.substringAfter(':')
        val directory = File(root, "repo/${group.replace('.', '/')}/$name/$version").apply { mkdirs() }
        File(directory, "$name-$version.pom").writeText(
            "<project><modelVersion>4.0.0</modelVersion><groupId>$group</groupId>" +
                "<artifactId>$name</artifactId><version>$version</version>" +
                "<dependencies>$dependencies</dependencies></project>",
        )
        JarOutputStream(File(directory, "$name-$version.jar").outputStream()).use {
            it.putNextEntry(JarEntry("fixture.txt"))
            it.write("local policy fixture".toByteArray())
            it.closeEntry()
        }
    }
}
