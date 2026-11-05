package io.github.phillipdpiris.snoopguardviewer

import android.text.format.DateFormat
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.documentfile.provider.DocumentFile
import androidx.recyclerview.widget.RecyclerView

/** Lists encrypted entries from the vault folder. Never decodes ciphertext. */
class VaultAdapter(
    private val items: List<DocumentFile>,
    private val onClick: (DocumentFile) -> Unit,
) : RecyclerView.Adapter<VaultAdapter.VH>() {

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val caption: TextView = view.findViewById(R.id.caption)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_entry, parent, false)
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val doc = items[position]
        val time = DateFormat.format("MMM d, h:mm:ss a", doc.lastModified())
        holder.caption.text = holder.itemView.context.getString(R.string.entry_item) + "  •  " + time
        holder.itemView.setOnClickListener { onClick(doc) }
    }

    override fun getItemCount(): Int = items.size
}
