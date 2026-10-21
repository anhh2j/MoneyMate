package com.app.moneymate.spike

import android.content.Context
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.app.moneymate.R
import com.app.moneymate.capture.spike.SpikeNotificationListenerService

// Compose Unit-returning functions require uppercase names. Keep both lint systems explicit.
@Suppress("FunctionNaming", "ktlint:standard:function-naming")
@Composable
private fun Control(
    label: String,
    id: String,
    action: () -> Unit,
) {
    BasicText(label, Modifier.padding(12.dp).semantics { contentDescription = id }.clickable(onClick = action))
}

// Single debug screen; raw never enters saved state. Uppercase follows Compose naming.
@Suppress("LongMethod", "FunctionNaming", "ktlint:standard:function-naming")
@Composable
fun SpikeScreen(
    context: Context,
    settings: () -> Boolean,
    rebind: () -> Unit,
) {
    val session = SpikeNotificationListenerService.session
    var revision by remember { mutableIntStateOf(0) }
    DisposableEffect(session) {
        val observer = {
            revision++
            Unit
        }
        session.observe(observer)
        onDispose { session.unobserve(observer) }
    }
    // Keep no raw payload in Compose state; clear mutates even previously rendered records.
    val epoch = session.epoch
    var chosen by remember(epoch) { mutableStateOf<String?>(null) }
    var consent by remember(epoch) { mutableStateOf(false) }
    var reveal by remember(epoch) { mutableStateOf(false) }
    var revealPrompt by remember(epoch) { mutableStateOf(false) }
    var settingsMissing by remember { mutableStateOf(false) }
    Column(Modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
        BasicText(stringResource(R.string.spike_warning))
        BasicText(
            "Access=${session.access}; Connected=${session.connected}; " +
                "Discovery=${session.discovery}; Payload=${session.payloadEnabled}",
        )
        BasicText("Received=${session.received}; Dropped=${session.dropped}; Revision=$revision")
        Control(stringResource(R.string.spike_start), "spike-start", session::start)
        Control(stringResource(R.string.spike_stop), "spike-stop", session::stop)
        Control(stringResource(R.string.spike_clear), "spike-clear", session::clear)
        Control(stringResource(R.string.spike_settings), "spike-settings") { settingsMissing = !settings() }
        if (settingsMissing) BasicText(stringResource(R.string.spike_settings_missing))
        Control(stringResource(R.string.spike_rebind), "spike-rebind", rebind)
        session.packages().forEach { pkg ->
            Control("Package: $pkg", "spike-package-$pkg") {
                if (session.payloadEnabled) {
                    session.consent(emptySet())
                } else {
                    chosen = pkg
                    consent = true
                }
            }
        }
        if (consent && chosen != null) {
            BasicText(stringResource(R.string.spike_consent))
            Control(stringResource(R.string.spike_enable), "spike-consent") { session.consent(setOfNotNull(chosen)) }
        }
        if (session.payloadEnabled) {
            Control(stringResource(R.string.spike_hidden), "spike-reveal-request") { revealPrompt = true }
            if (revealPrompt) {
                BasicText(stringResource(R.string.spike_reveal_warning))
                Control(stringResource(R.string.spike_reveal), "spike-reveal-confirm") { reveal = true }
            }
        }
        session.records().filter { chosen == null || chosen == it.packageName }.forEach { record ->
            BasicText("${record.packageName}; ${record.postTime}; truncated=${record.truncated}")
            Control(stringResource(R.string.spike_copy), "spike-copy") {
                SpikeClipboard.copyMetadata(
                    context,
                    record.packageName,
                    record.postTime,
                    record.receivedAt,
                    record.groupSummary,
                )
            }
            if (reveal && session.payloadEnabled) {
                BasicText(
                    "title: ${record.title.orEmpty()}\ntext: ${record.text.orEmpty()}\n" +
                        "bigText: ${record.bigText.orEmpty()}\nsubText: ${record.subText.orEmpty()}",
                )
            } else {
                BasicText(stringResource(R.string.spike_hidden))
            }
        }
    }
}
