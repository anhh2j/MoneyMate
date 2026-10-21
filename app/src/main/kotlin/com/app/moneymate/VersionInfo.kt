package com.app.moneymate

object VersionInfo {
    val name: String get() = BuildConfig.VERSION_NAME
    val gitSha: String get() = BuildConfig.GIT_SHA
}
