package io.github.phillipdpiris.snoopguard

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context

class SnoopGuardApp : Application() {

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    private fun createChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.notif_channel_name),
            // LOW keeps the required running-notice quiet, but it stays visible —
            // a foreground service notification cannot be removed.
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = getString(R.string.notif_channel_desc)
            setShowBadge(false)
        }
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    companion object {
        const val CHANNEL_ID = "snoopguard_watch"
    }
}
