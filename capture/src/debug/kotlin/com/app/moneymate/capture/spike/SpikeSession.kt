package com.app.moneymate.capture.spike

/** Pure reducer; all callers serialize on the Android main thread. */
class SpikeSession(private val clock: () -> Long) {
    enum class Access { UNKNOWN, NOT_GRANTED, GRANTED }

    var access = Access.UNKNOWN
        private set
    var connected = false
        private set
    var foreground = false
        private set
    var discovery = false
        private set
    var epoch = 0L
        private set
    var dropped = 0L
        private set
    var received = 0L
        private set
    var payloadEnabled = false
        private set
    private var startedAt = 0L
    private var payloadAt = 0L
    private var rebindAt: Long? = null
    private val buffer = ArrayDeque<RawNotification>()
    private val selected = mutableSetOf<String>()
    private val observers = mutableSetOf<() -> Unit>()

    fun records(): List<RawNotification> = buffer.toList()

    fun packages(): Set<String> = buffer.map { it.packageName }.toSet()

    fun observe(observer: () -> Unit) { observers.add(observer) }

    fun unobserve(observer: () -> Unit) { observers.remove(observer) }

    private fun changed() { observers.toList().forEach { it() } }

    fun start() {
        stop()
        discovery = true
        startedAt = clock()
        changed()
    }

    fun stop() {
        clear()
        discovery = false
        changed()
    }

    fun clear() {
        clearPayload()
        buffer.clear()
        dropped = 0
        received = 0
        changed()
    }

    private fun clearPayload() {
        epoch++
        buffer.forEach { it.clearPayload() }
        selected.clear()
        payloadEnabled = false
    }

    fun setForeground(value: Boolean) {
        foreground = value
        if (!value) clearPayload()
        changed()
    }

    fun setConnection(value: Boolean) {
        connected = value
        if (!value) clearPayload()
        changed()
    }

    fun setAccess(value: Access) {
        if (access == value) return
        access = value
        if (value != Access.GRANTED) stop()
        changed()
    }

    /** Called only by an explicit confirmation in the foreground UI. */
    fun consent(packages: Set<String>): Boolean {
        clearPayload()
        val valid = packages.isNotEmpty() && packages().containsAll(packages)
        payloadEnabled = discovery && foreground && connected && access == Access.GRANTED && valid
        if (payloadEnabled) {
            selected.addAll(packages)
            payloadAt = clock()
        }
        changed()
        return payloadEnabled
    }

    fun tick() {
        if (discovery && clock() - startedAt >= DISCOVERY_TTL) {
            stop()
        } else if (payloadEnabled && clock() - payloadAt >= PAYLOAD_TTL) {
            clearPayload()
            changed()
        }
    }

    fun permitsPayload(packageName: String): Boolean {
        tick()
        return discovery && foreground && connected && access == Access.GRANTED &&
            payloadEnabled && packageName in selected
    }

    /** Lazy factory must not touch notification extras until permitsPayload succeeds. */
    fun receive(metadata: RawNotification, payload: () -> RawNotification) {
        tick()
        if (!discovery || !connected || access != Access.GRANTED) return
        val token = epoch
        val record = if (permitsPayload(metadata.packageName)) payload() else metadata
        if (token != epoch) {
            record.clearPayload()
            return
        }
        if (received < Long.MAX_VALUE) received++
        buffer.addLast(record)
        while (buffer.size > MAX_EVENTS || buffer.sumOf { it.textBytes() } > MAX_BYTES) {
            buffer.removeFirst().clearPayload()
            if (dropped < Long.MAX_VALUE) dropped++
        }
        changed()
    }

    fun requestRebindAllowed(): Boolean {
        val now = clock()
        val previous = rebindAt
        val allowed = access == Access.GRANTED && !connected && (previous == null || now - previous >= REBIND_COOLDOWN)
        if (allowed) rebindAt = now
        return allowed
    }

    companion object {
        const val MAX_EVENTS = 100
        const val MAX_BYTES = 1024 * 1024
        const val PAYLOAD_TTL = 5 * 60 * 1000L
        const val DISCOVERY_TTL = 2 * 60 * 60 * 1000L
        const val REBIND_COOLDOWN = 30 * 1000L
    }
}
