package com.example.postgarden.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.postgarden.data.PolishedNewsItem

import com.example.postgarden.data.ApiClient // Import ApiClient
import com.example.postgarden.R // Import the R class

class NewsAdapter : ListAdapter<PolishedNewsItem, NewsAdapter.NewsViewHolder>(NewsDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): NewsViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_news, parent, false)
        return NewsViewHolder(view)
    }

    override fun onBindViewHolder(holder: NewsViewHolder, position: Int) {
        val item = getItem(position)
        holder.bind(item)
    }

    class NewsViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val rankView: TextView = itemView.findViewById(R.id.tv_rank)
        private val titleView: TextView = itemView.findViewById(R.id.tv_title)
        private val contentView: TextView = itemView.findViewById(R.id.tv_content)
        private val sourceView: TextView = itemView.findViewById(R.id.tv_source)
        private val imageView: ImageView = itemView.findViewById(R.id.iv_news_image)

        fun bind(item: PolishedNewsItem) {
            rankView.text = "${item.rank}."
            titleView.text = item.title
            contentView.text = item.content
            sourceView.text = "Source: ${item.source_platform}"
            
            // Only load image if URL is valid
            if (item.image.isNotEmpty()) {
                val imageUrl = if (item.image.startsWith("http")) {
                    item.image
                } else {
                    "${ApiClient.BASE_URL}/${item.image}" // Use ApiClient.BASE_URL
                }
                Glide.with(itemView.context)
                    .load(imageUrl)
                    .centerCrop()
                    .placeholder(android.R.drawable.ic_menu_gallery) // Placeholder while loading
                    .error(android.R.drawable.ic_delete) // Error placeholder
                    .into(imageView)
            } else {
                // You can set a placeholder image here if you have one
                imageView.setImageResource(android.R.drawable.ic_menu_gallery)
            }
        }
    }
}

class NewsDiffCallback : DiffUtil.ItemCallback<PolishedNewsItem>() {
    override fun areItemsTheSame(oldItem: PolishedNewsItem, newItem: PolishedNewsItem): Boolean {
        return oldItem.rank == newItem.rank && oldItem.source_url == newItem.source_url
    }

    override fun areContentsTheSame(oldItem: PolishedNewsItem, newItem: PolishedNewsItem): Boolean {
        return oldItem == newItem
    }
}
