package com.app.moneymate.capture

import org.junit.Assert.assertEquals
import org.junit.Test

class ModuleSmokeTest {
    @Test
    fun generatedModuleConfigurationLoads() {
        val config = Class.forName("com.app.moneymate.capture.BuildConfig")
        assertEquals("com.app.moneymate.capture", config.getField("LIBRARY_PACKAGE_NAME").get(null))
    }
}
