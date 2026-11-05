package io.github.phillipdpiris.snoopguard

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import io.github.phillipdpiris.snoopguard.databinding.ActivityMainBinding

/**
 * Host for the three tabs: Watch (arm/disarm + captures), Import (encrypt your
 * own media), and Vault (passphrase-gated viewer).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.bottomNav.setOnItemSelectedListener { item ->
            val fragment: Fragment = when (item.itemId) {
                R.id.nav_watch -> WatchFragment()
                R.id.nav_import -> ImportFragment()
                R.id.nav_vault -> VaultFragment()
                else -> return@setOnItemSelectedListener false
            }
            supportFragmentManager.beginTransaction()
                .replace(R.id.container, fragment)
                .commit()
            true
        }

        if (savedInstanceState == null) {
            binding.bottomNav.selectedItemId = R.id.nav_watch
        }
    }
}
