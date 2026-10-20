plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.app.moneymate.privacy"
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
    testImplementation(libs.junit)
}
