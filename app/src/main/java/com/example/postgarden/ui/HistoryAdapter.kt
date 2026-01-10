package com.example.postgarden.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.example.postgarden.R
import com.example.postgarden.data.CachedReport

class HistoryAdapter(
    private val onItemClick: (CachedReport) -> Unit
) : RecyclerView.Adapter<HistoryAdapter.HistoryViewHolder>() {

    private var items: List<CachedReport> = emptyList()

    fun submitList(newItems: List<CachedReport>) {
        items = newItems
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): HistoryViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_history, parent, false)
        return HistoryViewHolder(view)
    }

    override fun onBindViewHolder(holder: HistoryViewHolder, position: Int) {
        val item = items[position]
        holder.bind(item)
    }

    override fun getItemCount(): Int = items.size

    inner class HistoryViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvTitle: TextView = itemView.findViewById(R.id.tvHistoryTitle)

        fun bind(item: CachedReport) {
            tvTitle.text = "${item.type.uppercase()} - ${item.version}"
            
            itemView.setOnClickListener {
                onItemClick(item)
            }
        }
    }
}
