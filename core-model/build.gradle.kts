plugins {
    alias(libs.plugins.kotlin.jvm)
    jacoco
}

kotlin { jvmToolchain(17) }
jacoco { toolVersion = libs.versions.jacoco.get() }

dependencies {
    testImplementation(libs.junit)
}
