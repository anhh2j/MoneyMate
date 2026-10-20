package com.app.moneymate.parser

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test
import java.util.Properties

class ModuleSmokeTest {
    @Test
    fun moduleResourceLoadsFromRuntimeClasspath() {
        val resource = javaClass.getResourceAsStream("/moneymate/parser.properties")
        assertNotNull("The module resource must be packaged on the runtime classpath", resource)
        val properties = Properties()
        requireNotNull(resource).use(properties::load)
        assertEquals("parser", properties.getProperty("module"))
        assertNotNull(javaClass.getResource("/moneymate/core-model.properties"))
    }
}
