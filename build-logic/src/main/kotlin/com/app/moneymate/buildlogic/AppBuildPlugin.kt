package com.app.moneymate.buildlogic

import org.gradle.api.NamedDomainObjectContainer
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.withGroovyBuilder
import java.io.File

class AppBuildPlugin : Plugin<Project> {
    override fun apply(project: Project) {
        val version = Versioning.read(project.rootProject.file("version.properties"))
        configureVersion(project, version)
        configureRelease(project)
        registerInventory(project)
    }

    private fun registerInventory(project: Project) {
        val root = project.rootProject
        val inventories =
            root.subprojects.map { module ->
                module.tasks.register("exportModuleDependencies") {
                    doLast { Inventory.write(module) }
                }
            }
        root.tasks.register("exportDependencyInventory") {
            dependsOn(inventories)
            dependsOn(project.gradle.includedBuild("build-logic").task(":exportBuildDependencies"))
            doLast {
                Inventory.write(root)
                Inventory.combine(root)
            }
        }
    }

    private fun configureVersion(
        project: Project,
        version: AppVersion,
    ) {
        val android = project.extensions.getByName("android")
        // Keep the shared settings/project plugin JAR free of AGP type signatures.
        // The extension belongs to the Android plugin's project classloader.
        android.withGroovyBuilder {
            getProperty("defaultConfig").withGroovyBuilder {
                setProperty("versionName", version.name)
                setProperty("versionCode", version.code)
                "buildConfigField"("String", "GIT_SHA", "\"${gitSha(project.rootDir)}\"")
            }
            getProperty("buildFeatures").withGroovyBuilder { setProperty("buildConfig", true) }
        }
    }

    private fun configureRelease(project: Project) {
        val android = project.extensions.getByName("android")
        val credentials =
            listOf("KEYSTORE_BASE64", "KEYSTORE_PASSWORD", "KEY_ALIAS", "KEY_PASSWORD")
                .associateWith { project.providers.environmentVariable(it).orNull }
        val signing =
            if (credentials.values.all { !it.isNullOrEmpty() }) {
                val material =
                    project.gradle.sharedServices
                        .registerIfAbsent("moneymateSigning", SigningMaterial::class.java) {}
                        .get()
                android.withGroovyBuilder {
                    val configs = getProperty("signingConfigs") as NamedDomainObjectContainer<*>
                    configs.create("environmentRelease").apply {
                        withGroovyBuilder {
                            setProperty("storeFile", material.decode(requireNotNull(credentials["KEYSTORE_BASE64"])))
                            setProperty("storePassword", credentials["KEYSTORE_PASSWORD"])
                            setProperty("keyAlias", credentials["KEY_ALIAS"])
                            setProperty("keyPassword", credentials["KEY_PASSWORD"])
                        }
                    }
                }
            } else {
                null
            }
        android.withGroovyBuilder {
            val defaultRules = "getDefaultProguardFile"("proguard-android-optimize.txt")
            val release = (getProperty("buildTypes") as NamedDomainObjectContainer<*>).getByName("release")
            release.withGroovyBuilder {
                setProperty("minifyEnabled", true)
                setProperty("shrinkResources", true)
                "proguardFiles"(defaultRules, project.file("proguard-rules.pro"))
                setProperty("signingConfig", signing)
            }
        }
    }

    private fun gitSha(directory: File): String =
        runCatching {
            val process = ProcessBuilder("git", "rev-parse", "--short=7", "HEAD").directory(directory).start()
            val value = process.inputStream.bufferedReader().use { it.readText().trim() }
            if (process.waitFor() == 0 && value.matches(Regex("[0-9a-f]{7}"))) value else "unknown"
        }.getOrDefault("unknown")
}
