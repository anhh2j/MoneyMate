package com.app.moneymate.spike

import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Process

/** Lives in the test APK's own UID, never inside the target instrumentation process. */
class SpikeProbeActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if ("probe".equals(intent.getStringExtra("mode"))) {
            probe()
            finish()
        } else {
            publish()
        }
    }

    private fun publish() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel("synthetic", "Synthetic", NotificationManager.IMPORTANCE_DEFAULT),
        )
        var index = 0
        while (index < 3) {
            val id = index + 1
            val delay = 2000L + index * 2000L
            Handler(Looper.getMainLooper()).postDelayed(
                object : Runnable {
                    override fun run() {
                        val content =
                            StringBuilder()
                                .append("T01")
                                .append('_')
                                .append("SYNTHETIC")
                                .append('_')
                                .append("CANARY")
                        // Passing the Java result directly avoids a Kotlin Intrinsics null-check.
                        manager.notify(
                            id,
                            Notification
                                .Builder(this@SpikeProbeActivity, "synthetic")
                                .setSmallIcon(android.R.drawable.ic_dialog_info)
                                .setContentTitle("Synthetic title")
                                .setContentText(content)
                                .setSubText("Synthetic subtext")
                                .setStyle(Notification.BigTextStyle().bigText("Synthetic expanded"))
                                .build(),
                        )
                        if (id == 1) this@SpikeProbeActivity.finish()
                    }
                },
                delay,
            )
            index++
        }
    }

    private fun probe() {
        val component =
            ComponentName(
                "com.app.moneymate",
                "com.app.moneymate.capture.spike.SpikeNotificationListenerService",
            )
        var bindDenied = false
        var startDenied = false
        val connection =
            object : ServiceConnection {
                override fun onServiceConnected(
                    name: ComponentName?,
                    service: IBinder?,
                ) = Unit

                override fun onServiceDisconnected(name: ComponentName?) = Unit
            }
        try {
            val bound = bindService(Intent().setComponent(component), connection, Context.BIND_AUTO_CREATE)
            bindDenied = !bound
            if (bound) unbindService(connection)
        } catch (_: SecurityException) {
            bindDenied = true
        }
        try {
            startService(Intent().setComponent(component))
        } catch (_: SecurityException) {
            startDenied = true
        }
        val targetUid = packageManager.getApplicationInfo("com.app.moneymate", 0).uid
        getSharedPreferences("probe", MODE_PRIVATE)
            .edit()
            .putBoolean("bindDenied", bindDenied)
            .putBoolean("startDenied", startDenied)
            .putInt("probeUid", Process.myUid())
            .putInt("targetUid", targetUid)
            .putBoolean("differentUid", targetUid != Process.myUid())
            .commit()
    }
}
