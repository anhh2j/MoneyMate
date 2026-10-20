package com.app.moneymate

import org.junit.Assert.assertEquals
import org.junit.Test

class ModuleSmokeTest {
    @Test
    fun launcherActivityLoadsFromApplicationModule() {
        val activity = Class.forName("com.app.moneymate.MainActivity", false, javaClass.classLoader)
        assertEquals("androidx.activity.ComponentActivity", requireNotNull(activity.superclass).name)
    }
}
