package com.app.moneymate.security

import org.junit.Assert.assertEquals
import org.junit.Test

class ModuleSmokeTest {
    @Test
    fun generatedModuleConfigurationLoads() {
        val config = Class.forName("com.app.moneymate.security.BuildConfig")
        assertEquals("com.app.moneymate.security", config.getField("LIBRARY_PACKAGE_NAME").get(null))
    }
}
