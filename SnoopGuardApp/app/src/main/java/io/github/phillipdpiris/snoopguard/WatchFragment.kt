package io.github.phillipdpiris.snoopguard

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import io.github.phillipdpiris.snoopguard.crypto.KeyManager
import io.github.phillipdpiris.snoopguard.databinding.FragmentWatchBinding

/** Arm/disarm, log-only toggle, and the (locked) capture list. */
class WatchFragment : Fragment() {

    private var _binding: FragmentWatchBinding? = null
    private val binding get() = _binding!!

    private lateinit var armState: ArmState
    private lateinit var store: CaptureStore
    private lateinit var keyManager: KeyManager
    private val adapter = CapturesAdapter(emptyList())

    private val requestPerms = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        if (result[Manifest.permission.CAMERA] == true) {
            arm()
        } else {
            toast(getString(R.string.perm_camera_needed))
        }
    }

    private val setupLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) requestAndArm()
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        _binding = FragmentWatchBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        armState = ArmState(requireContext())
        store = CaptureStore(requireContext())
        keyManager = KeyManager(requireContext())

        binding.capturesList.layoutManager = LinearLayoutManager(requireContext())
        binding.capturesList.adapter = adapter

        binding.silentSwitch.isChecked = armState.silent
        binding.silentSwitch.setOnCheckedChangeListener { _, checked ->
            armState.silent = checked
            if (armState.armed) {
                WatchService.stop(requireContext())
                WatchService.start(requireContext())
            }
        }

        binding.armButton.setOnClickListener {
            when {
                armState.armed -> disarm()
                !keyManager.isSetup() -> setupLauncher.launch(Intent(requireContext(), SetupActivity::class.java))
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
            if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED
            ) add(Manifest.permission.CAMERA)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (needed.isEmpty()) arm() else requestPerms.launch(needed.toTypedArray())
    }

    private fun arm() {
        armState.armed = true
        WatchService.start(requireContext())
        render()
    }

    private fun disarm() {
        armState.armed = false
        WatchService.stop(requireContext())
        render()
    }

    private fun render() {
        val b = _binding ?: return
        b.statusText.setText(if (armState.armed) R.string.status_armed else R.string.status_disarmed)
        b.armButton.setText(if (armState.armed) R.string.disarm else R.string.arm)
        val captures = store.listCaptures()
        adapter.submit(captures)
        b.emptyText.visibility = if (captures.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun toast(message: String) =
        Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show()

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
