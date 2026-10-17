package com.app.moneymate.privacy

import org.junit.Assert.assertEquals
import org.junit.Test

class ModuleSmokeTest {
    @Test
    fun generatedModuleConfigurationLoads() {
        val config = Class.forName("com.app.moneymate.privacy.BuildConfig")
        assertEquals("com.app.moneymate.privacy", config.getField("LIBRARY_PACKAGE_NAME").get(null))
    }
}
