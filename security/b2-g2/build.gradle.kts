import groovy.json.JsonOutput
import org.gradle.api.artifacts.component.ModuleComponentIdentifier
import org.gradle.api.artifacts.result.ResolvedDependencyResult
import org.gradle.api.artifacts.result.UnresolvedDependencyResult
import java.security.MessageDigest

plugins {
    alias(libs.plugins.android.application)
    // Request the baseline KGP without applying a JVM plugin to this Android harness.
    alias(libs.plugins.kotlin.jvm) apply false
}

android {
    namespace = "com.app.moneymate.b2g2"
    compileSdk = 37
    defaultConfig {
        applicationId = "com.app.moneymate.b2g2"
        minSdk = 26
        targetSdk = 37
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    testBuildType = "release"
    buildTypes {
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            isDebuggable = false
            signingConfig = signingConfigs.getByName("debug")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    lint {
        warningsAsErrors = true
        abortOnError = true
    }
}

kotlin { jvmToolchain(17) }

dependencies {
    implementation(libs.b2.argon2kt)
    implementation(libs.b2.tracing)
    androidTestImplementation(libs.b2.runner)
    androidTestImplementation(libs.b2.junit)
    androidTestCompileOnly(libs.b2.errorprone.annotations)
}

tasks.register("exportB2G2Toolchain") {
    doLast {
        val scopes =
            listOf(
                "buildscript:classpath" to buildscript.configurations.getByName("classpath"),
                "module:kotlinCompilerClasspath" to configurations.getByName("kotlinCompilerClasspath"),
                "module:kotlinBuildToolsApiClasspath" to configurations.getByName("kotlinBuildToolsApiClasspath"),
            )
        val graphs =
            scopes.map { (scope, configuration) ->
                val result = configuration.incoming.resolutionResult
                check(result.allDependencies.none { it is UnresolvedDependencyResult }) { "Unresolved toolchain: $scope" }
                mapOf(
                    "scope" to scope,
                    "components" to
                        result.allComponents.filter { it.id is ModuleComponentIdentifier }.mapNotNull { it.moduleVersion }.map {
                            mapOf("group" to it.group, "name" to it.name, "version" to it.version)
                        },
                    "selectionReasons" to
                        result.allComponents.map {
                            mapOf(
                                "id" to it.id.displayName,
                                "reasons" to it.selectionReason.descriptions.map { reason -> reason.description },
                            )
                        },
                    "edges" to
                        result.allDependencies.filterIsInstance<ResolvedDependencyResult>().map {
                            mapOf(
                                "from" to it.from.id.displayName,
                                "requested" to it.requested.displayName,
                                "selected" to it.selected.id.displayName,
                            )
                        },
                )
            }
        val directory =
            layout.buildDirectory
                .dir("reports/b2-g2")
                .get()
                .asFile
        directory.mkdirs()
        // Persist selection evidence even if subsequent artifact verification fails.
        directory.resolve("toolchain-graph.json").writeText(JsonOutput.toJson(mapOf("graphs" to graphs)))
        val artifacts =
            scopes.flatMap { (scope, configuration) ->
                configuration.incoming.artifacts.artifacts.map {
                    mapOf(
                        "scope" to scope,
                        "component" to it.id.componentIdentifier.displayName,
                        "artifact" to it.id.displayName,
                        "file" to it.file.name,
                        "sha256" to
                            MessageDigest.getInstance("SHA-256").digest(it.file.readBytes()).joinToString("") { byte ->
                                "%02x".format(byte)
                            },
                    )
                }
            }
        directory.resolve("toolchain-artifacts.json").writeText(JsonOutput.toJson(artifacts))
    }
}

tasks.register("exportB2G2Inventory") {
    doLast {
        val scopes =
            configurations.filter { it.isCanBeResolved } +
                buildscript.configurations.filter { it.isCanBeResolved }
        val graphs = scopes.map { it.name to it.incoming.resolutionResult }
        check(graphs.all { (_, result) -> result.allDependencies.none { it is UnresolvedDependencyResult } })
        val components =
            graphs
                .flatMap { (_, result) -> result.allComponents }
                .filter { it.id is ModuleComponentIdentifier }
                .mapNotNull { it.moduleVersion }
                .distinctBy { "${it.group}:${it.name}:${it.version}" }
                .map {
                    mapOf(
                        "type" to "library",
                        "group" to it.group,
                        "name" to it.name,
                        "version" to it.version,
                        "purl" to "pkg:maven/${it.group}/${it.name}@${it.version}",
                    )
                }
        val report =
            layout.buildDirectory
                .file("reports/b2-g2/dependencies.cdx.json")
                .get()
                .asFile
        report.parentFile.mkdirs()
        report.writeText(
            JsonOutput.toJson(
                mapOf("bomFormat" to "CycloneDX", "specVersion" to "1.5", "version" to 1, "components" to components),
            ),
        )
    }
}
