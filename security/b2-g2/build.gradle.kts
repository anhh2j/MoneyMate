import groovy.json.JsonOutput
import org.gradle.api.artifacts.component.ModuleComponentIdentifier
import org.gradle.api.artifacts.result.UnresolvedDependencyResult

plugins {
    alias(libs.plugins.android.application)
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
    androidTestImplementation(libs.b2.runner)
    androidTestImplementation(libs.b2.junit)
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
