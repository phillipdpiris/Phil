package io.github.phillipdpiris.snoopguard

import android.graphics.BitmapFactory
import android.text.format.DateFormat
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import java.io.File

class CapturesAdapter(private var items: List<File>) :
    RecyclerView.Adapter<CapturesAdapter.VH>() {

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
        // Downsample thumbnails so the list does not load full-res JPEGs.
        val opts = BitmapFactory.Options().apply { inSampleSize = 8 }
        holder.thumb.setImageBitmap(BitmapFactory.decodeFile(file.absolutePath, opts))
        val when_ = DateFormat.format("MMM d, h:mm:ss a", file.lastModified())
        holder.caption.text = when_
    }

    override fun getItemCount(): Int = items.size
}
