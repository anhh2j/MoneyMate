package com.app.moneymate.buildlogic

import org.gradle.api.Action
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.artifacts.Configuration
import org.gradle.api.initialization.Settings
import java.io.File

class DependencyPolicyPlugin : Plugin<Settings> {
    override fun apply(settings: Settings) {
        val pins = pins(settings.settingsDir.resolve("gradle/libs.versions.toml"))
        settings.gradle.beforeProject(
            object : Action<Project> {
                override fun execute(project: Project) {
                    project.buildscript.configurations.configureEach { pinTooling(pins) }
                    project.configurations.configureEach {
                        if (name == "androidLintTool") pinTooling(pins)
                    }
                }
            },
        )
    }

    private fun Configuration.pinTooling(pins: Map<String, String>) {
        resolutionStrategy.eachDependency {
            pins["${requested.group}:${requested.name}"]?.let {
                useVersion(it)
                because("T00b B approved experiment: exact tooling GAV security pin")
            }
        }
    }

    companion object {
        fun loadedClasses(
            project: Project,
            pins: Map<String, String>,
        ): List<Map<String, String>> {
            val androidApp = project.plugins.findPlugin("com.android.application")
            val android = androidApp ?: project.plugins.findPlugin("com.android.library")
            if (project != project.rootProject && android == null) return emptyList()
            val anchors =
                mapOf(
                    "org.bouncycastle:bcprov-jdk18on" to "org.bouncycastle.jce.provider.BouncyCastleProvider",
                    "org.bouncycastle:bcutil-jdk18on" to "org.bouncycastle.asn1.cms.ContentInfo",
                    "org.bouncycastle:bcpkix-jdk18on" to "org.bouncycastle.operator.ContentSigner",
                    "org.bitbucket.b_c:jose4j" to "org.jose4j.jwe.JsonWebEncryption",
                    "org.jdom:jdom2" to "org.jdom2.Document",
                )
            val loaders =
                mapOf(
                    "agp" to (android?.javaClass?.classLoader ?: project.buildscript.classLoader),
                    "project-script" to project.buildscript.classLoader,
                )
            return loaders.flatMap { (context, loader) ->
                anchors.map { (gav, name) ->
                    val type = Class.forName(name, false, loader)
                    val source = type.protectionDomain.codeSource.location
                    val jar = File(source.toURI()).name
                    val expected = "${gav.substringAfter(':')}-${pins.getValue(gav)}.jar"
                    check(jar == expected || jar == "instrumented-$expected") {
                        "Loaded tooling mismatch in ${project.path}:$context: $gav from $source; expected $expected"
                    }
                    mapOf(
                        "context" to context,
                        "gav" to gav,
                        "class" to name,
                        "expectedVersion" to pins.getValue(gav),
                        "source" to source.toString(),
                    )
                }
            }
        }

        fun pins(catalog: File): Map<String, String> {
            val versions = catalog.readText().substringBefore("[libraries]")

            fun version(key: String): String {
                val values = Regex("(?m)^$key\\s*=\\s*\"([0-9]+(?:\\.[0-9]+)+)\"\\s*$").findAll(versions).toList()
                require(values.size == 1) { "Missing or duplicate tooling pin: $key" }
                return values.single().groupValues[1]
            }
            val bc = version("toolingBc")
            return mapOf(
                "org.bouncycastle:bcprov-jdk18on" to bc,
                "org.bouncycastle:bcutil-jdk18on" to bc,
                "org.bouncycastle:bcpkix-jdk18on" to bc,
                "org.bitbucket.b_c:jose4j" to version("toolingJose4j"),
                "org.jdom:jdom2" to version("toolingJdom2"),
            )
        }
    }
}
