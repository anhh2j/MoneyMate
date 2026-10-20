pluginManagement {
    includeBuild("build-logic")
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

// The settings policy uses only Gradle APIs. AGP stays in app/build-logic runtimes,
// not the settings parent classloader, where its plugin version would be unknown.
buildscript {
    configurations.classpath {
        exclude(group = "com.android.tools.build", module = "gradle")
    }
}

plugins { id("moneymate.dependency-policy") }

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "MoneyMate"
include(":app", ":core-model", ":capture", ":parser", ":dedup", ":categorizer", ":data", ":privacy", ":security")
