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
    private var stage = "snapshot"

    override fun onCreate(arguments: Bundle?) {
        super.onCreate(arguments)
        phase = arguments?.getString("phase")
        start()
    }

    override fun onStart() {
        val result = Bundle()
        try {
            if (phase == "cold") {
                checkCase(state { !session.discovery && !session.payloadEnabled && session.records().isEmpty() })
                result.putString("stream", "Cold process state PASS\n")
            } else {
                exerciseSnapshot()
                sendStatus(0, Bundle().apply { putString("case", "ING-01 snapshot null/malformed/limit PASS") })
                stage = "listener"
                exerciseListener()
                sendStatus(0, Bundle().apply { putString("case", "ING-02..05 listener/privacy PASS") })
                stage = "external-uid"
                exerciseIsolation()
                sendStatus(0, Bundle().apply { putString("case", "ING-03 external UID bind/start denied PASS") })
                result.putString("stream", "ING-01..05 runtime assertions PASS\n")
            }
            finish(Activity.RESULT_OK, result)
        } catch (_: AssertionError) {
            onMain {
                result.putString("access", session.access.name)
                result.putBoolean("connected", session.connected)
                result.putBoolean("foreground", session.foreground)
                result.putInt("recordCount", session.records().size)
                val keyguard = targetContext.getSystemService(android.app.KeyguardManager::class.java)
                result.putBoolean("keyguardLocked", keyguard.isKeyguardLocked)
                val manager = targetContext.getSystemService(android.app.ActivityManager::class.java)
                result.putBoolean("lowRamDevice", manager.isLowRamDevice)
            }
            result.putString("stream", "FAIL: $stage assertion; payload omitted\n")
            finish(Activity.RESULT_CANCELED, result)
        } catch (_: RuntimeException) {
            result.putString("stream", "FAIL: $stage exception; details omitted\n")
            finish(Activity.RESULT_CANCELED, result)
        }
    }

    private fun exerciseSnapshot() {
        val metadata = RawNotification("synthetic", 10, 20, false)
        val extras =
            Bundle().apply {
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
        extras.putCharSequence(Notification.EXTRA_TEXT, android.text.SpannableString("spanned"))
        checkCase(SpikeNotificationSnapshotter.snapshot(metadata, extras).text == "spanned")
    }

    private fun exerciseListener() {
        startActivitySync(
            Intent()
                .setComponent(ComponentName(targetContext, SpikeActivity::class.java))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
        )
        click("spike-rebind")
        waitFor { state { session.connected } }
        click("spike-start")
        launchProbe("post")
        waitFor { state { session.records().any { it.packageName == context.packageName } } }
        onMain { checkCase(session.records().all { it.text == null }) }
        click("spike-package-${context.packageName}")
        click("spike-consent")
        waitFor { state { session.records().any { it.text == canary() } } }
        checkCase(!containsCanary(uiAutomation.rootInActiveWindow))
        click("spike-reveal-request")
        click("spike-reveal-confirm")
        waitFor {
            val root = uiAutomation.rootInActiveWindow
            val visible = containsCanary(root)
            if (!visible && root != null) scrollForward(root)
            visible
        }
        // Copy uses the metadata-only API through the UI, not a synthetic export hook.
        click("spike-copy")
        onMain {
            val clipboard = targetContext.getSystemService(ClipboardManager::class.java)
            val text =
                clipboard.primaryClip
                    ?.getItemAt(0)
                    ?.text
                    ?.toString()
                    .orEmpty()
            checkCase(text.contains("package=") && !text.contains(canary()))
        }
        changeAccess(false)
        waitFor { state { session.access != SpikeSession.Access.GRANTED && session.records().isEmpty() } }
        changeAccess(true)
        waitFor { state { session.connected } }
        onMain { checkCase(!session.payloadEnabled) }
        click("spike-start")
        click("spike-clear")
        onMain { checkCase(session.records().isEmpty() && !session.payloadEnabled) }
        uiAutomation.executeShellCommand("input keyevent 3").close()
        SystemClock.sleep(500)
        onMain { checkCase(!session.foreground && session.records().all { it.text == null }) }
    }

    private fun changeAccess(granted: Boolean) {
        val listener = "com.app.moneymate/com.app.moneymate.capture.spike.SpikeNotificationListenerService"
        val command =
            if (android.os.Build.VERSION.SDK_INT == 26) {
                if (granted) {
                    "settings put secure enabled_notification_listeners $listener"
                } else {
                    "settings delete secure enabled_notification_listeners"
                }
            } else {
                if (granted) {
                    "cmd notification allow_listener $listener"
                } else {
                    "cmd notification disallow_listener $listener"
                }
            }
        uiAutomation.executeShellCommand(command).close()
    }

    private fun exerciseIsolation() {
        launchProbe("probe")
        waitFor {
            val command = "run-as ${context.packageName} cat shared_prefs/probe.xml"
            val descriptor = uiAutomation.executeShellCommand(command)
            val result =
                android.os.ParcelFileDescriptor
                    .AutoCloseInputStream(descriptor)
                    .bufferedReader()
                    .use { it.readText() }
            listOf("differentUid", "bindDenied", "startDenied").all { key ->
                result.contains("name=\"$key\" value=\"true\"")
            }
        }
    }

    private fun launchProbe(mode: String) {
        targetContext.startActivity(
            Intent()
                .setComponent(ComponentName(context.packageName, SpikeProbeActivity::class.java.name))
                .putExtra("mode", mode)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
        )
        SystemClock.sleep(700)
    }

    private fun click(id: String) {
        stage = id
        waitFor {
            val root = uiAutomation.rootInActiveWindow ?: return@waitFor false
            val node = find(root, id)
            if (node != null) {
                node.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.id)
                node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            } else {
                scrollForward(root)
                false
            }
        }
        waitForIdleSync()
        stage = "$id-complete"
        sendStatus(0, Bundle().apply { putString("step", stage) })
    }

    private fun find(
        node: AccessibilityNodeInfo,
        id: String,
    ): AccessibilityNodeInfo? =
        if (node.contentDescription?.toString() == id) {
            node
        } else {
            (0 until node.childCount).firstNotNullOfOrNull { index ->
                node.getChild(index)?.let { find(it, id) }
            }
        }

    private fun scrollForward(node: AccessibilityNodeInfo): Boolean {
        if (node.isScrollable && node.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)) return true
        return (0 until node.childCount).any { index -> node.getChild(index)?.let { scrollForward(it) } == true }
    }

    private fun containsCanary(node: AccessibilityNodeInfo?): Boolean =
        node != null && (
            node.text?.toString()?.contains(canary()) == true ||
                (0 until node.childCount).any { containsCanary(node.getChild(it)) }
        )

    private fun waitFor(condition: () -> Boolean) {
        val until = SystemClock.elapsedRealtime() + 20_000
        while (SystemClock.elapsedRealtime() < until) {
            if (condition()) return
            SystemClock.sleep(150)
        }
        throw AssertionError("timeout; details omitted")
    }

    private fun state(condition: () -> Boolean): Boolean {
        var result = false
        runOnMainSync { result = condition() }
        return result
    }

    private fun onMain(action: () -> Unit) {
        runOnMainSync(action)
    }

    private fun checkCase(value: Boolean) {
        if (!value) throw AssertionError("case failed; details omitted")
    }

    companion object {
        private val session get() = SpikeNotificationListenerService.session

        fun canary(): String = listOf("T01", "SYNTHETIC", "CANARY").joinToString("_")
    }
}
