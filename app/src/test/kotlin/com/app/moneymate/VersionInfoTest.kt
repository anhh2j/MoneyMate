package com.app.moneymate

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VersionInfoTest {
    @Test
    fun exposesGeneratedBuildMetadata() {
        assertEquals(BuildConfig.VERSION_NAME, VersionInfo.name)
        assertEquals(BuildConfig.GIT_SHA, VersionInfo.gitSha)
        assertTrue(VersionInfo.name.matches(Regex("[0-9]+\\.[0-9]+\\.[0-9]+(?:-(?:alpha|beta|rc)\\.[0-9]+)?")))
        assertTrue(VersionInfo.gitSha == "unknown" || VersionInfo.gitSha.matches(Regex("[0-9a-f]{7}")))
    }
}
