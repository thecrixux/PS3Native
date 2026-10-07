package net.rpcs3.ui.hud

import android.content.Context
import android.net.Uri
import android.os.Build
import android.system.Os
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import net.rpcs3.R
import net.rpcs3.RPCS3
import net.rpcs3.ui.components.SettingsHint
import net.rpcs3.ui.components.SettingsSection
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import org.json.JSONObject

// Keep the capture alive when the drawer is closed. Bound native storage to 60,000 frames.
object BenchmarkCapture {
    var recording by mutableStateOf(false)
        private set
    var busy by mutableStateOf(false)
        private set
    var latest by mutableStateOf<File?>(null)
        private set
    var status by mutableStateOf("")
        private set
    private var metadata = JSONObject()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    fun start(context: Context) {
        if (busy || recording) return
        runCatching {
            val titleId = RPCS3.instance.getTitleId()
            val details = JSONObject()
                .put("title_id", titleId)
                .put("started_unix_ms", System.currentTimeMillis())
                .put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
                .put("android_sdk", Build.VERSION.SDK_INT)
                .put("tu_debug", Os.getenv("TU_DEBUG").orEmpty())
                .put("runtime_at_start", JSONObject(RPCS3.instance.benchmarkContext()))
                .put("hud_enabled", HudPrefs.isEnabled(HudPrefs.of(context)))
                .put("measurement", "RSX flip intervals; excludes loading state and emulator pauses; excludes generated frames")
            if (!RPCS3.instance.benchmarkStart()) {
                status = context.getString(R.string.benchmark_not_running)
                return
            }
            metadata = details
            recording = true
            status = context.getString(R.string.benchmark_recording)
        }.onFailure { status = context.getString(R.string.benchmark_error, it.message.orEmpty()) }
    }

    fun finish(context: Context) {
        if (!recording || busy) return
        val app = context.applicationContext
        val details = metadata
        recording = false
        busy = true
        scope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val report = JSONObject(RPCS3.instance.benchmarkStop())
                    val frames = report.getJSONArray("frames")
                    report.remove("frames")
                    report.put("metadata", details)
                    val output = File(app.cacheDir, "benchmark-latest.zip")
                    val temporary = File(app.cacheDir, "benchmark-pending.zip")
                    ZipOutputStream(temporary.outputStream().buffered()).use { zip ->
                        zip.putNextEntry(ZipEntry("summary.json"))
                        zip.write(report.toString(2).toByteArray(Charsets.UTF_8))
                        zip.closeEntry()
                        zip.putNextEntry(ZipEntry("frames.csv"))
                        val writer = zip.writer(Charsets.UTF_8).buffered()
                        writer.write("frame,frame_time_ms,elapsed_ms\n")
                        var elapsed = 0.0
                        for (index in 0 until frames.length()) {
                            val ms = frames.getDouble(index)
                            elapsed += ms
                            writer.write("${index + 1},$ms,$elapsed\n")
                        }
                        writer.flush()
                        zip.closeEntry()
                    }
                    check(temporary.renameTo(output)) { "Cannot save benchmark archive" }
                    output to report
                }
            }.onSuccess { (file, report) ->
                latest = file
                status = app.getString(
                    R.string.benchmark_result,
                    report.getInt("frame_count"), report.getDouble("fps"), report.getDouble("p99_ms")
                )
                if (report.optBoolean("limit_reached")) {
                    status += " " + app.getString(R.string.benchmark_limit)
                }
            }.onFailure { status = app.getString(R.string.benchmark_error, it.message.orEmpty()) }
            busy = false
        }
    }

    fun save(context: Context, uri: Uri) {
        val source = latest ?: return
        if (busy || recording) return
        val app = context.applicationContext
        busy = true
        scope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val output = app.contentResolver.openOutputStream(uri, "wt")
                        ?: error("Cannot open destination")
                    output.use { stream -> source.inputStream().use { it.copyTo(stream) } }
                }
            }.onSuccess { status = app.getString(R.string.benchmark_saved) }
                .onFailure { status = app.getString(R.string.benchmark_error, it.message.orEmpty()) }
            busy = false
        }
    }
}

@Composable
fun BenchmarkPanel() {
    val context = LocalContext.current
    val exporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/zip")) { uri ->
        if (uri != null) BenchmarkCapture.save(context, uri)
    }
    SettingsSection(title = stringResource(R.string.benchmark_title)) {
        SettingsHint(text = stringResource(R.string.benchmark_hint))
        TextButton(
            enabled = !BenchmarkCapture.busy,
            onClick = {
                if (BenchmarkCapture.recording) BenchmarkCapture.finish(context)
                else BenchmarkCapture.start(context)
            }
        ) {
            Text(stringResource(if (BenchmarkCapture.recording) R.string.benchmark_stop else R.string.benchmark_start))
        }
        TextButton(
            enabled = BenchmarkCapture.latest != null && !BenchmarkCapture.busy && !BenchmarkCapture.recording,
            onClick = { exporter.launch("PS3Native-benchmark-${System.currentTimeMillis()}.zip") }
        ) { Text(stringResource(R.string.benchmark_export)) }
        if (BenchmarkCapture.busy) Text(stringResource(R.string.benchmark_busy))
        if (BenchmarkCapture.status.isNotEmpty()) SettingsHint(text = BenchmarkCapture.status)
    }
}
