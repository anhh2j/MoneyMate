import org.gradle.api.artifacts.ProjectDependency

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.compose) apply false
}

val ktlint by configurations.creating
val detektCli by configurations.creating

dependencies {
    ktlint(libs.ktlint.cli)
    detektCli(libs.detekt.cli)
}

val kotlinFiles = fileTree(rootDir) {
    include("**/*.kt", "**/*.kts")
    exclude("**/build/**", "**/.gradle/**", "**/.git/**")
}

tasks.register<JavaExec>("ktlintCheck") {
    group = "verification"
    description = "Checks every Kotlin source and build script; no auto-correction."
    classpath = ktlint
    mainClass.set("com.pinterest.ktlint.Main")
    inputs.files(kotlinFiles)
    val report = layout.buildDirectory.file("reports/ktlint/checkstyle.xml")
    outputs.file(report)
    doFirst {
        report.get().asFile.parentFile.mkdirs()
        args("--reporter=plain", "--reporter=checkstyle,output=${report.get().asFile}")
        args(kotlinFiles.files.sorted().map { it.absolutePath })
    }
}

tasks.register<JavaExec>("detekt") {
    group = "verification"
    description = "Strict source analysis with zero tolerated findings and an empty baseline."
    classpath = detektCli
    mainClass.set("io.gitlab.arturbosch.detekt.cli.Main")
    inputs.files(kotlinFiles.matching { include("**/*.kt") })
    inputs.files("detekt.yml", "detekt-baseline.xml")
    val reports = layout.buildDirectory.dir("reports/detekt")
    outputs.dir(reports)
    doFirst {
        reports.get().asFile.mkdirs()
        args(
            "--input", kotlinFiles.matching { include("**/*.kt") }.files.sorted().joinToString(",") { it.absolutePath },
            "--config", file("detekt.yml").absolutePath,
            "--baseline", file("detekt-baseline.xml").absolutePath,
            "--build-upon-default-config",
            "--report", "html:${reports.get().file("detekt.html").asFile}",
            "--report", "xml:${reports.get().file("detekt.xml").asFile}",
        )
    }
}

val moduleEdges = mapOf(
    "app" to setOf("core-model", "capture", "parser", "dedup", "categorizer", "data", "privacy", "security"),
    "core-model" to emptySet(),
    "capture" to setOf("core-model"),
    "parser" to setOf("core-model"),
    "dedup" to setOf("core-model"),
    "categorizer" to setOf("core-model"),
    "data" to setOf("core-model"),
    "privacy" to emptySet(),
    "security" to emptySet(),
)

tasks.register("verifyModuleGraph") {
    group = "verification"
    description = "Checks the exact T00 module graph, including absence of cycles."
    doLast {
        check(subprojects.map { it.name }.toSet() == moduleEdges.keys) { "Unexpected module set" }
        subprojects.forEach { module ->
            val actual = module.configurations.flatMap { it.dependencies.withType<ProjectDependency>() }
                .map { it.name }.toSet()
            check(actual == moduleEdges.getValue(module.name)) {
                "${module.path}: expected ${moduleEdges[module.name]}, got $actual"
            }
        }
        println("PASS: exact T00 module graph; all edges terminate at core-model, no cycles")
    }
}
