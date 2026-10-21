import groovy.json.JsonOutput
import org.gradle.api.artifacts.component.ModuleComponentIdentifier
import org.gradle.api.artifacts.result.UnresolvedDependencyResult

plugins {
    `kotlin-dsl`
}

kotlin { jvmToolchain(17) }

dependencies {
    implementation(libs.android.gradle.plugin)
    testImplementation(libs.junit)
    testImplementation(gradleTestKit())
    constraints {
        implementation(libs.tooling.bcprov) { version { strictly(libs.versions.toolingBc.get()) } }
        implementation(libs.tooling.bcutil) { version { strictly(libs.versions.toolingBc.get()) } }
        implementation(libs.tooling.bcpkix) { version { strictly(libs.versions.toolingBc.get()) } }
        implementation(libs.tooling.jose4j) { version { strictly(libs.versions.toolingJose4j.get()) } }
        implementation(libs.tooling.jdom2) { version { strictly(libs.versions.toolingJdom2.get()) } }
    }
}

gradlePlugin {
    plugins {
        register("dependencyPolicy") {
            id = "moneymate.dependency-policy"
            implementationClass = "com.app.moneymate.buildlogic.DependencyPolicyPlugin"
        }
        register("appVersion") {
            id = "moneymate.app-version"
            implementationClass = "com.app.moneymate.buildlogic.AppBuildPlugin"
        }
    }
}

tasks.register("exportBuildDependencies") {
    val output = layout.buildDirectory.file("reports/security/build-logic.cdx.json")
    outputs.file(output)
    outputs.upToDateWhen { false }
    doLast {
        val scopes =
            configurations.filter { it.isCanBeResolved } + buildscript.configurations.filter { it.isCanBeResolved }
        val results = scopes.map { it.incoming.resolutionResult }
        check(results.all { result -> result.allDependencies.none { it is UnresolvedDependencyResult } }) {
            "Unresolved build-logic dependency"
        }
        val tooling =
            listOf(
                libs.tooling.bcprov,
                libs.tooling.bcutil,
                libs.tooling.bcpkix,
                libs.tooling.jose4j,
                libs.tooling.jdom2,
            ).map { it.get() }
                .associate { "${it.module.group}:${it.module.name}" to it.versionConstraint.requiredVersion }
        val allComponents = results.flatMap { it.allComponents }
        val modules = allComponents.filter { it.id is ModuleComponentIdentifier }.mapNotNull { it.moduleVersion }
        modules.forEach {
            tooling["${it.group}:${it.name}"]?.let { expected ->
                check(it.version == expected) { "Unexpected build-logic tooling: $it; expected $expected" }
            }
        }
        check(tooling.keys.all { gav -> modules.any { "${it.group}:${it.name}" == gav } }) {
            "Missing tooling component"
        }
        val components =
            allComponents
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
        output.get().asFile.apply {
            parentFile.mkdirs()
            writeText(
                JsonOutput.toJson(
                    mapOf(
                        "bomFormat" to "CycloneDX",
                        "specVersion" to "1.5",
                        "version" to 1,
                        "components" to components,
                    ),
                ),
            )
        }
    }
}
