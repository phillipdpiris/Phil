package io.github.phillipdpiris.snoopguard

import android.content.Context
import android.net.Uri
import android.util.Log
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.io.File

/**
 * On-device face check. Used to discard frames that contain no face (phone woke
 * in a pocket, pointed at a ceiling, camera toggled off → black frame).
 *
 * This is NOT face *recognition*. Teaching it to skip the owner's own face
 * (so the app can stay armed all the time) needs an embedding model such as
 * MobileFaceNet via TFLite, and is listed as a follow-up in the README.
 */
class FaceGate {

    private val detector = FaceDetection.getClient(
        FaceDetectorOptions.Builder()
            .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
            .build(),
    )

    /** Calls [onResult] with true if at least one face is present in [jpeg]. */
    fun hasFace(context: Context, jpeg: File, onResult: (Boolean) -> Unit) {
        val image = try {
            InputImage.fromFilePath(context, Uri.fromFile(jpeg))
        } catch (t: Throwable) {
            Log.w("SnoopGuard", "face input failed: ${t.message}")
            onResult(false)
            return
        }
        detector.process(image)
            .addOnSuccessListener { faces -> onResult(faces.isNotEmpty()) }
            .addOnFailureListener { onResult(false) }
    }

    fun close() = detector.close()
}
