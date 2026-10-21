package com.app.moneymate.spike

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context

/** Deliberately accepts no RawNotification, CharSequence payload, or arbitrary export text. */
object SpikeClipboard {
    fun copyMetadata(context: Context, packageName: String, postTime: Long, receivedAt: Long, summary: Boolean) {
        require(packageName.matches(Regex("[A-Za-z0-9_.]+")))
        val metadata = "package=$packageName;postTime=$postTime;receivedAt=$receivedAt;summary=$summary"
        context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("metadata", metadata))
    }
}
