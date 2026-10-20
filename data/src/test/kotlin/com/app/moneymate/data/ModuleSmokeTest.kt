package com.app.moneymate.data

import org.junit.Assert.assertEquals
import org.junit.Test

class ModuleSmokeTest {
    @Test
    fun generatedModuleConfigurationLoads() {
        val config = Class.forName("com.app.moneymate.data.BuildConfig")
        assertEquals("com.app.moneymate.data", config.getField("LIBRARY_PACKAGE_NAME").get(null))
    }
}
