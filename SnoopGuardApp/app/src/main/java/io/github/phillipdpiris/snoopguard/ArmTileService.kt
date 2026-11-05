package io.github.phillipdpiris.snoopguard

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService

/**
 * Quick Settings tile to arm/disarm. Tapping the tile runs with the panel open,
 * which counts as a foreground start, so the camera service is permitted to bind
 * the camera (Android 14+ background-start restriction).
 */
class ArmTileService : TileService() {

    private val armState by lazy { ArmState(this) }

    override fun onStartListening() {
        super.onStartListening()
        refresh()
    }

    override fun onClick() {
        super.onClick()
        if (armState.armed) {
            armState.armed = false
            WatchService.stop(this)
        } else {
            armState.armed = true
            WatchService.start(this)
        }
        refresh()
    }

    private fun refresh() {
        val tile = qsTile ?: return
        tile.state = if (armState.armed) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        tile.label = getString(
            if (armState.armed) R.string.status_armed else R.string.status_disarmed,
        )
        tile.updateTile()
    }
}
