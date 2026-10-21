package com.app.moneymate.capture.spike

import android.app.NotificationManager
import android.content.ComponentName
import android.content.Context
import android.os.Build
import android.provider.Settings

object SpikeNotificationAccess {
    fun component(context: Context): ComponentName = ComponentName(context, SpikeNotificationListenerService::class.java)

    fun read(context: Context): SpikeSession.Access =
        try {
            val granted =
                if (Build.VERSION.SDK_INT >= 27) {
                    context.getSystemService(NotificationManager::class.java).isNotificationListenerAccessGranted(component(context))
                } else {
                    val setting = Settings.Secure.getString(context.contentResolver, "enabled_notification_listeners")
                    setting?.split(':')?.mapNotNull { ComponentName.unflattenFromString(it) }?.contains(component(context)) == true
                }
            if (granted) SpikeSession.Access.GRANTED else SpikeSession.Access.NOT_GRANTED
        } catch (_: SecurityException) {
            SpikeSession.Access.UNKNOWN
        }
}
