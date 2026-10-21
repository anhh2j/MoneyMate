package com.app.moneymate.capture.spike

/** Debug RAM only. No generated toString/copy/component methods for payload. */
class RawNotification(
    val packageName: String,
    val postTime: Long,
    val receivedAt: Long,
    val groupSummary: Boolean,
    title: String? = null,
    text: String? = null,
    bigText: String? = null,
    subText: String? = null,
    val truncated: Boolean = false,
) {
    var title: String? = title
        private set
    var text: String? = text
        private set
    var bigText: String? = bigText
        private set
    var subText: String? = subText
        private set

    fun textBytes(): Int = listOf(title, text, bigText, subText).sumOf { (it?.length ?: 0) * 2 }

    fun clearPayload() {
        title = null
        text = null
        bigText = null
        subText = null
    }

    override fun toString(): String = "RawNotification(payload=hidden)"
}
