plugins {
    alias(libs.plugins.kotlin.jvm)
    jacoco
}

kotlin { jvmToolchain(17) }
jacoco { toolVersion = libs.versions.jacoco.get() }

dependencies {
    implementation(project(":core-model"))
    testImplementation(libs.junit)
}

// T00 scaffolding has no production classes. T04 enables this gate with real code.
val hasProductionCode = providers.gradleProperty("enableProductionCoverage").map(String::toBoolean).orElse(false)

tasks.jacocoTestReport {
    dependsOn(tasks.test)
    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}

tasks.jacocoTestCoverageVerification {
    dependsOn(tasks.test)
    violationRules {
        rule {
            limit {
                counter = "LINE"
                minimum = "0.85".toBigDecimal()
            }
        }
    }
    onlyIf { hasProductionCode.get() }
}

tasks.test { finalizedBy(tasks.jacocoTestReport) }
tasks.check {
    dependsOn(tasks.jacocoTestCoverageVerification)
}
