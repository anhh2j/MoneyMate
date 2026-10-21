package com.app.moneymate.capture.spike

import android.app.KeyguardManager
import android.app.Notification
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class SpikeNotificationListenerService : NotificationListenerService() {
    private val handler = Handler(Looper.getMainLooper())
    private val tick =
        object : Runnable {
            override fun run() {
                session.setAccess(SpikeNotificationAccess.read(this@SpikeNotificationListenerService))
                if (getSystemService(KeyguardManager::class.java).isKeyguardLocked) session.setForeground(false)
                session.tick()
                handler.postDelayed(this, TICK_INTERVAL_MS)
            }
        }

    override fun onListenerConnected() {
        session.setAccess(SpikeNotificationAccess.read(this))
        session.setConnection(true)
        handler.removeCallbacks(tick)
        handler.post(tick)
    }

    override fun onListenerDisconnected() {
        session.setConnection(false)
        session.setAccess(SpikeNotificationAccess.read(this))
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        session.setAccess(SpikeNotificationAccess.read(this))
        if (getSystemService(KeyguardManager::class.java).isKeyguardLocked) session.setForeground(false)
        val metadata =
            RawNotification(
                sbn.packageName,
                sbn.postTime,
                System.currentTimeMillis(),
                sbn.notification.flags and Notification.FLAG_GROUP_SUMMARY != 0,
            )
        session.receive(metadata) { SpikeNotificationSnapshotter.snapshot(metadata, sbn.notification.extras) }
    }

    override fun onDestroy() {
        handler.removeCallbacks(tick)
        session.setConnection(false)
        session.stop()
        super.onDestroy()
    }

    companion object {
        private const val TICK_INTERVAL_MS = 1000L
        val session = SpikeSession { SystemClock.elapsedRealtime() }
    }
}
