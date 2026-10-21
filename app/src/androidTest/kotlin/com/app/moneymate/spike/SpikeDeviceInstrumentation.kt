package com.app.moneymate.spike

import android.app.Activity
import android.app.Instrumentation
import android.app.Notification
import android.content.ClipboardManager
import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import com.app.moneymate.capture.spike.RawNotification
import com.app.moneymate.capture.spike.SpikeNotificationListenerService
import com.app.moneymate.capture.spike.SpikeNotificationSnapshotter
import com.app.moneymate.capture.spike.SpikeSession

/** No raw values in assertion messages, instrumentation status, or evidence. */
class SpikeDeviceInstrumentation : Instrumentation() {
    private var phase: String? = null

    override fun onCreate(arguments: Bundle?) {
        super.onCreate(arguments)
        phase = arguments?.getString("phase")
        start()
    }

    override fun onStart() {
        val result = Bundle()
        try {
            if (phase == "cold") {
                checkCase(!session.discovery && !session.payloadEnabled && session.records().isEmpty())
                result.putString("stream", "Cold process state PASS\n")
            } else {
                exerciseSnapshot()
                exerciseListener()
                exerciseIsolation()
                result.putString("stream", "ING-01..05 runtime assertions PASS\n")
            }
            finish(Activity.RESULT_OK, result)
        } catch (_: AssertionError) {
            result.putString("stream", "FAIL: runtime assertion; payload omitted\n")
            finish(Activity.RESULT_CANCELED, result)
        } catch (_: RuntimeException) {
            result.putString("stream", "FAIL: runtime exception; details omitted\n")
            finish(Activity.RESULT_CANCELED, result)
        }
    }

    private fun exerciseSnapshot() {
        val metadata = RawNotification("synthetic", 10, 20, false)
        val extras = Bundle().apply {
            putCharSequence(Notification.EXTRA_TITLE, "t")
            putCharSequence(Notification.EXTRA_TEXT, canary())
            putCharSequence(Notification.EXTRA_BIG_TEXT, "b")
            putCharSequence(Notification.EXTRA_SUB_TEXT, "s")
        }
        val raw = SpikeNotificationSnapshotter.snapshot(metadata, extras)
        checkCase(raw.text == canary() && raw.bigText == "b" && raw.postTime != raw.receivedAt)
        checkCase(!raw.toString().contains(canary()))
        checkCase(SpikeNotificationSnapshotter.snapshot(metadata, null).text == null)
        extras.putCharSequence(Notification.EXTRA_TEXT, "x".repeat(20_000))
        val limited = SpikeNotificationSnapshotter.snapshot(metadata, extras)
        checkCase(limited.truncated && limited.textBytes() <= 32 * 1024)
        extras.putInt(Notification.EXTRA_TEXT, 1)
        checkCase(SpikeNotificationSnapshotter.snapshot(metadata, extras).text == null)
    }

    private fun exerciseListener() {
        startActivitySync(Intent().setComponent(ComponentName(targetContext, SpikeActivity::class.java)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        waitFor { session.connected }
        click("spike-start")
        launchProbe("post")
        waitFor { session.records().any { it.packageName == context.packageName } }
        onMain { checkCase(session.records().all { it.text == null }) }
        click("spike-package-${context.packageName}")
        click("spike-consent")
        waitFor { session.records().any { it.text == canary() } }
        // Copy uses the metadata-only API through the UI, not a synthetic export hook.
        click("spike-copy")
        onMain {
            val clipboard = targetContext.getSystemService(ClipboardManager::class.java)
            val text = clipboard.primaryClip?.getItemAt(0)?.text?.toString().orEmpty()
            checkCase(text.contains("package=") && !text.contains(canary()))
        }
        val listener = "com.app.moneymate/com.app.moneymate.capture.spike.SpikeNotificationListenerService"
        uiAutomation.executeShellCommand("cmd notification disallow_listener $listener").close()
        waitFor { session.access != SpikeSession.Access.GRANTED && session.records().isEmpty() }
        uiAutomation.executeShellCommand("cmd notification allow_listener $listener").close()
        waitFor { session.connected }
        onMain { checkCase(!session.payloadEnabled) }
        click("spike-start")
        click("spike-clear")
        onMain { checkCase(session.records().isEmpty() && !session.payloadEnabled) }
        uiAutomation.executeShellCommand("input keyevent 3").close()
        SystemClock.sleep(500)
        onMain { checkCase(!session.foreground && session.records().all { it.text == null }) }
    }

    private fun exerciseIsolation() {
        launchProbe("probe")
        waitFor {
            val descriptor = uiAutomation.executeShellCommand("run-as ${context.packageName} cat shared_prefs/probe.xml")
            val result = android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor).bufferedReader().use { it.readText() }
            listOf("differentUid", "bindDenied", "startDenied").all { key ->
                result.contains("name=\"$key\" value=\"true\"")
            }
        }
    }

    private fun launchProbe(mode: String) {
        context.startActivity(Intent().setComponent(ComponentName(context.packageName, SpikeProbeActivity::class.java.name))
            .putExtra("mode", mode).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        SystemClock.sleep(700)
    }

    private fun click(id: String) {
        waitFor {
            val root = uiAutomation.rootInActiveWindow ?: return@waitFor false
            val node = find(root, id)
            if (node != null) node.performAction(AccessibilityNodeInfo.ACTION_CLICK) else false
        }
        waitForIdleSync()
    }

    private fun find(node: AccessibilityNodeInfo, id: String): AccessibilityNodeInfo? {
        if (node.contentDescription?.toString() == id) return node
        for (index in 0 until node.childCount) {
            val child = node.getChild(index) ?: continue
            val found = find(child, id)
            if (found != null) return found
        }
        return null
    }

    private fun waitFor(condition: () -> Boolean) {
        val until = SystemClock.elapsedRealtime() + 20_000
        while (SystemClock.elapsedRealtime() < until) {
            var success = false
            onMain { success = condition() }
            if (success) return
            SystemClock.sleep(150)
        }
        throw AssertionError("timeout; details omitted")
    }

    private fun onMain(action: () -> Unit) { runOnMainSync(action) }

    private fun checkCase(value: Boolean) {
        if (!value) throw AssertionError("case failed; details omitted")
    }

    companion object {
        private val session get() = SpikeNotificationListenerService.session

        fun canary(): String = listOf("T01", "SYNTHETIC", "CANARY").joinToString("_")
    }
}
