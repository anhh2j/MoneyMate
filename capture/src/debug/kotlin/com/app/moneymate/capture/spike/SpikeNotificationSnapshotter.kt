package com.app.moneymate.capture.spike

import android.app.Notification
import android.os.BadParcelableException
import android.os.Bundle

object SpikeNotificationSnapshotter {
    private const val MAX_UNITS = 16_384

    fun snapshot(
        metadata: RawNotification,
        extras: Bundle?,
    ): RawNotification {
        var remaining = MAX_UNITS
        var truncated = false

        fun read(key: String): String? {
            val value =
                try {
                    // Avoid typed getter framework warnings for malformed extras.
                    @Suppress("DEPRECATION")
                    val candidate = extras?.get(key)
                    candidate as? CharSequence
                } catch (_: BadParcelableException) {
                    null
                } catch (_: ClassCastException) {
                    null
                }
            if (value == null) return null
            var end = minOf(value.length, remaining)
            if (end in 1 until value.length && Character.isHighSurrogate(value[end - 1])) end--
            truncated = truncated || end < value.length
            remaining -= end
            return value.subSequence(0, end).toString()
        }
        val title = read(Notification.EXTRA_TITLE)
        val text = read(Notification.EXTRA_TEXT)
        val bigText = read(Notification.EXTRA_BIG_TEXT)
        val subText = read(Notification.EXTRA_SUB_TEXT)
        return RawNotification(
            metadata.packageName,
            metadata.postTime,
            metadata.receivedAt,
            metadata.groupSummary,
            title,
            text,
            bigText,
            subText,
            truncated,
        )
    }
}
