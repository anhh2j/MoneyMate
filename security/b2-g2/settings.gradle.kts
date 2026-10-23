pluginManagement {
    includeBuild("../../build-logic")
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

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

rootProject.name = "MoneyMate-B2-G2-Test-Only"
