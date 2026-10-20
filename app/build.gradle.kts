plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    id("moneymate.app-version")
}

android {
    namespace = "com.app.moneymate"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.app.moneymate"
        minSdk = 26
        targetSdk = 37
    }
    buildFeatures { compose = true }
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
    implementation(project(":core-model"))
    implementation(project(":capture"))
    implementation(project(":parser"))
    implementation(project(":dedup"))
    implementation(project(":categorizer"))
    implementation(project(":data"))
    implementation(project(":privacy"))
    implementation(project(":security"))

    implementation(libs.activity.compose)
    implementation(libs.compose.foundation)
    implementation(libs.compose.ui)
    testImplementation(libs.junit)
}
