package io.github.phillipdpiris.snoopguard

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import io.github.phillipdpiris.snoopguard.crypto.KeyManager
import io.github.phillipdpiris.snoopguard.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var armState: ArmState
    private lateinit var store: CaptureStore
    private lateinit var keyManager: KeyManager
    private val adapter = CapturesAdapter(emptyList())

    private val setupLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        if (result.resultCode == RESULT_OK) requestAndArm()
    }

    private val requestPerms = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        val cameraGranted = result[Manifest.permission.CAMERA] == true
        if (cameraGranted) {
            arm()
        } else {
            Toast.makeText(this, R.string.perm_camera_needed, Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        armState = ArmState(this)
        store = CaptureStore(this)
        keyManager = KeyManager(this)

        binding.capturesList.layoutManager = LinearLayoutManager(this)
        binding.capturesList.adapter = adapter

        binding.silentSwitch.isChecked = armState.silent
        binding.silentSwitch.setOnCheckedChangeListener { _, checked ->
            armState.silent = checked
            if (armState.armed) {
                // Re-arm so the mode change takes effect.
                WatchService.stop(this)
                WatchService.start(this)
            }
        }

        binding.armButton.setOnClickListener {
            when {
                armState.armed -> disarm()
                !keyManager.isSetup() -> setupLauncher.launch(Intent(this, SetupActivity::class.java))
                else -> requestAndArm()
            }
        }
    }

    override fun onResume() {
        super.onResume()
        render()
    }

    private fun requestAndArm() {
        val needed = buildList {
            if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED
            ) add(Manifest.permission.CAMERA)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (needed.isEmpty()) arm() else requestPerms.launch(needed.toTypedArray())
    }

    private fun arm() {
        armState.armed = true
        WatchService.start(this)
        render()
    }

    private fun disarm() {
        armState.armed = false
        WatchService.stop(this)
        render()
    }

    private fun render() {
        binding.statusText.setText(
            if (armState.armed) R.string.status_armed else R.string.status_disarmed,
        )
        binding.armButton.setText(if (armState.armed) R.string.disarm else R.string.arm)
        val captures = store.listCaptures()
        adapter.submit(captures)
        binding.emptyText.visibility = if (captures.isEmpty()) android.view.View.VISIBLE else android.view.View.GONE
    }
}
