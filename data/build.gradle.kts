plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.app.moneymate.data"
    compileSdk = 37
    defaultConfig { minSdk = 26 }
    buildFeatures { buildConfig = true }
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
    testImplementation(libs.junit)
}
