package com.app.moneymate.capture.spike

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SpikeSessionTest {
    private var now = 0L
    private val session = SpikeSession { now }
    private fun metadata() = RawNotification("test.publisher", 10, 20, false)
    private fun send() = session.receive(metadata()) { RawNotification("test.publisher", 10, 20, false, text = "synthetic") }
    private fun ready() {
        session.setAccess(SpikeSession.Access.GRANTED)
        session.setConnection(true)
        session.setForeground(true)
        session.start()
        send()
    }

    @Test
    fun lazyPayloadGate() {
        ready()
        assertNull(session.records().last().text)
        assertTrue(session.consent(setOf("test.publisher")))
        send()
        assertEquals("synthetic", session.records().last().text)
        assertFalse(session.consent(setOf("unknown.publisher")))
        assertTrue(session.records().all { it.text == null })
    }

    @Test
    fun backgroundAndRevokeClearPayload() {
        ready()
        session.consent(setOf("test.publisher"))
        send()
        val stale = session.records().last()
        session.setForeground(false)
        assertNull(stale.text)
        send()
        assertNull(session.records().last().text)
        session.setAccess(SpikeSession.Access.NOT_GRANTED)
        assertTrue(session.records().isEmpty())
        assertFalse(session.discovery)
    }

    @Test
    fun limitsAndTtl() {
        ready()
        session.consent(setOf("test.publisher"))
        repeat(101) { send() }
        assertEquals(100, session.records().size)
        assertEquals(2, session.dropped)
        now = SpikeSession.PAYLOAD_TTL
        session.tick()
        assertTrue(session.records().all { it.text == null })
        assertFalse(session.payloadEnabled)
        now = SpikeSession.DISCOVERY_TTL
        session.tick()
        assertTrue(session.records().isEmpty())
    }

    @Test
    fun byteLimitAndEpoch() {
        ready()
        session.consent(setOf("test.publisher"))
        repeat(80) {
            session.receive(metadata()) { RawNotification("test.publisher", 1, 2, false, text = "x".repeat(16_384)) }
        }
        assertTrue(session.records().sumOf { it.textBytes() } <= SpikeSession.MAX_BYTES)
        session.receive(metadata()) { session.clear(); RawNotification("test.publisher", 1, 2, false, text = "stale") }
        assertTrue(session.records().isEmpty())
    }

    @Test
    fun disconnectAndClearDoNotRestoreConsent() {
        ready()
        session.consent(setOf("test.publisher"))
        session.setConnection(false)
        session.setConnection(true)
        send()
        assertFalse(session.payloadEnabled)
        session.clear()
        assertTrue(session.records().isEmpty())
        assertFalse(session.payloadEnabled)
        assertEquals("RawNotification(payload=hidden)", RawNotification("test", 1, 2, false, text = "hidden").toString())
    }

    @Test
    fun rebindCooldownAndNewProcess() {
        session.setAccess(SpikeSession.Access.GRANTED)
        assertTrue(session.requestRebindAllowed())
        assertFalse(session.requestRebindAllowed())
        now += SpikeSession.REBIND_COOLDOWN
        assertTrue(session.requestRebindAllowed())
        session.setConnection(true)
        assertFalse(session.requestRebindAllowed())
        assertFalse(SpikeSession { now }.discovery)
        assertTrue(SpikeSession { now }.records().isEmpty())
    }
}
