plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.app.moneymate.security"
    compileSdk = 37
    defaultConfig {
        minSdk = 26
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
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
    androidTestImplementation(libs.b2.argon2kt)
    androidTestImplementation(libs.b2.runner)
    androidTestImplementation(libs.b2.junit)
}
