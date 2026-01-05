package com.example.postgarden.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.example.postgarden.R
import java.io.File

class HistoryAdapter(
    private val onItemClick: (File) -> Unit
) : RecyclerView.Adapter<HistoryAdapter.HistoryViewHolder>() {

    private var files: List<File> = emptyList()

    fun submitList(newFiles: List<File>) {
        files = newFiles
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): HistoryViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_history, parent, false)
        return HistoryViewHolder(view)
    }

    override fun onBindViewHolder(holder: HistoryViewHolder, position: Int) {
        val file = files[position]
        holder.bind(file)
    }

    override fun getItemCount(): Int = files.size

    inner class HistoryViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvTitle: TextView = itemView.findViewById(R.id.tvHistoryTitle)

        fun bind(file: File) {
            // file name format: history_20260105_100000_morning.json
            val name = file.name
            val parts = name.split("_")
            if (parts.size >= 4) {
                // simple parsing
                val date = parts[1]
                val time = parts[2]
                val type = parts[3].removeSuffix(".json")
                tvTitle.text = "$date $time - $type"
            } else {
                tvTitle.text = name
            }

            itemView.setOnClickListener {
                onItemClick(file)
            }
        }
    }
}
