package com.app.moneymate.coremodel

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test
import java.util.Properties

class ModuleSmokeTest {
    @Test
    fun moduleResourceLoadsFromRuntimeClasspath() {
        val resource = javaClass.getResourceAsStream("/moneymate/core-model.properties")
        assertNotNull("The module resource must be packaged on the runtime classpath", resource)
        val properties = Properties()
        requireNotNull(resource).use(properties::load)
        assertEquals("core-model", properties.getProperty("module"))
    }
}
