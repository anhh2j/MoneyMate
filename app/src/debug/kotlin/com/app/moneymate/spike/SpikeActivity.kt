package com.app.moneymate.spike

import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import com.app.moneymate.capture.spike.SpikeNotificationAccess
import com.app.moneymate.capture.spike.SpikeNotificationListenerService

class SpikeActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    SpikeNotificationListenerService.session.stop()
                    finish()
                }
            },
        )
        // Ignore all incoming extras/URI. No external intent can start a session or consent.
        setContent { SpikeScreen(this, ::openSettings, ::rebind) }
    }

    override fun onResume() {
        super.onResume()
        SpikeNotificationListenerService.session.setAccess(SpikeNotificationAccess.read(this))
        SpikeNotificationListenerService.session.setForeground(true)
    }

    override fun onPause() {
        SpikeNotificationListenerService.session.setForeground(false)
        super.onPause()
    }

    private fun openSettings(): Boolean =
        try {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            true
        } catch (_: ActivityNotFoundException) {
            false
        }

    private fun rebind() {
        val session = SpikeNotificationListenerService.session
        session.setAccess(SpikeNotificationAccess.read(this))
        if (session.requestRebindAllowed()) {
            NotificationListenerService.requestRebind(SpikeNotificationAccess.component(this))
        }
    }
}
