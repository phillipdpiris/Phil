package io.github.phillipdpiris.snoopguard

import android.text.format.DateFormat
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import java.io.File

/**
 * Lists encrypted items (captures or imports). It never decodes the files —
 * they are ciphertext — so it shows a lock, the time, and an optional label.
 * An optional click handler lets the Vault tab open (decrypt) an item.
 */
class CapturesAdapter(
    private var items: List<File>,
    private val labelResId: Int = R.string.capture_locked,
    private val onClick: ((File) -> Unit)? = null,
) : RecyclerView.Adapter<CapturesAdapter.VH>() {

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val thumb: ImageView = view.findViewById(R.id.thumb)
        val caption: TextView = view.findViewById(R.id.caption)
    }

    fun submit(newItems: List<File>) {
        items = newItems
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_capture, parent, false)
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val file = items[position]
        holder.thumb.setImageResource(R.drawable.ic_lock)
        val when_ = DateFormat.format("MMM d, h:mm:ss a", file.lastModified())
        val label = holder.itemView.context.getString(labelResId)
        holder.caption.text = "$label  •  $when_"
        onClick?.let { handler ->
            holder.itemView.setOnClickListener { handler(file) }
        }
    }

    override fun getItemCount(): Int = items.size
}
