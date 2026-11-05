package io.github.phillipdpiris.snoopguard

import android.content.Context
import android.util.Log
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.io.File

/**
 * Grabs a single still from the front camera using CameraX, bound to the
 * [WatchService] lifecycle. Headless: no preview surface is attached.
 */
class SelfieCapturer(
    private val context: Context,
    private val lifecycleOwner: LifecycleOwner,
) {
    private var imageCapture: ImageCapture? = null
    private var provider: ProcessCameraProvider? = null

    fun start(onReady: () -> Unit = {}) {
        val future = ProcessCameraProvider.getInstance(context)
        future.addListener({
            try {
                val cameraProvider = future.get()
                provider = cameraProvider
                val capture = ImageCapture.Builder()
                    .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                    .build()
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    lifecycleOwner,
                    CameraSelector.DEFAULT_FRONT_CAMERA,
                    capture,
                )
                imageCapture = capture
                onReady()
            } catch (t: Throwable) {
                // Camera access may be revoked via the Quick Settings toggle; surface it.
                Log.w(TAG, "Camera bind failed (toggle off or in use?): ${t.message}")
            }
        }, ContextCompat.getMainExecutor(context))
    }

    /** Takes one picture into [target]. [onResult] reports success/failure. */
    fun capture(target: File, onResult: (Boolean) -> Unit) {
        val capture = imageCapture ?: run { onResult(false); return }
        val options = ImageCapture.OutputFileOptions.Builder(target).build()
        capture.takePicture(
            options,
            ContextCompat.getMainExecutor(context),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(output: ImageCapture.OutputFileResults) = onResult(true)
                override fun onError(exc: ImageCaptureException) {
                    Log.w(TAG, "capture failed: ${exc.message}")
                    onResult(false)
                }
            },
        )
    }

    fun stop() {
        provider?.unbindAll()
        imageCapture = null
    }

    companion object {
        private const val TAG = "SnoopGuard"
    }
}
